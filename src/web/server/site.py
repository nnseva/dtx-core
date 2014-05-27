#
# -*- coding: utf-8 -*-
#

import os
import re
import types
import json
import logging
import traceback
import datetime
import urllib
import urllib2
import urlparse
import yaml
import cPickle as pickle

from itertools import chain
from pprint import pprint, pformat
from importlib import import_module

from twisted.web.server import NOT_DONE_YET
from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.web.xmlrpc import XMLRPC, withRequest
from twisted.web.wsgi import WSGIResource
from twisted.web import xmlrpc

from django.conf import settings
from django.http import HttpResponse
from django.core import urlresolvers
from django.utils import translation

from dtx.core.workflow import *
from dtx.utils.snippets.sorted_collection import SortedCollection

from dtx.core import logger
log = logger.log(__name__)

##############################################################################################################################
#
##############################################################################################################################

current_requests = []

class RequestInvocationContext:

    def __init__(self, fn, request, args, kwargs):
        self.ts = datetime.datetime.now()
        self.fn = fn
        self.request = request
        self.args = args
        self.kwargs = kwargs

    @classmethod
    def create(cls, fn, request, args, kwargs):
        context = cls(fn, request, args, kwargs)
        log.msg(u'New: {}'.format(unicode(context)))
        return context

    def __unicode__(self):
        try:
            if (self.request.method == 'POST'):
                return u'{}: F: {}'.format(unicode(datetime.datetime.now() - self.ts), unicode(self.fn))
            else:
                return u'{}: F: {}; A: {}; K {}'.format(unicode(datetime.datetime.now() - self.ts), unicode(self.fn), unicode(self.args), unicode(self.kwargs))
        except:
            return u'-- Internal Error --'

    def __enter__(self):
        global current_requests
        current_requests.append(self)

    def __exit__(self, type, value, tb):
        global current_requests
        current_requests.remove(self)

    @classmethod
    def dump_all(cls, current, framing):
        global current_requests
        try:
            log.msg(framing)
            idx = 1
            for ctx in current_requests:
                log.msg(u'{} ({}) {}'.format('*' if (current == ctx) else ' ', idx, unicode(ctx)))
                idx += 1
        finally:
            log.msg(framing)

##############################################################################################################################
#
##############################################################################################################################

@inlineCallbacks
def invokeResolverMatch(request, match):
    global current_requests
    from dtx.web import server
    with log.enter() as tm:
        try:
            kwargs = match.kwargs
            content_type = request.getHeader('content-type')
            if (content_type):
                log.msg(u'Content-Type: {}'.format(content_type))
                request.content_type = content_type.split(';')
            else:
                request.content_type = []
            request.content_type_name = request.content_type[0] if (len(request.content_type) >= 1) else None
            request.content_type_args = request.content_type[1] if (len(request.content_type) >= 2) else None
            form = {}
            if (request.content_type_name == 'application/python-pickle'):
                content = request.content.read()
                form = pickle.loads(content)
            elif (request.content_type_name == 'application/x-yaml'):
                content = request.content.read()
                form = yaml.load(content)
            params = dict(chain(kwargs.iteritems(), form.iteritems()))
            accept_language = request.getHeader('accept-language')
            accept_language = accept_language if (accept_language) else 'en-US,en;q=0.8'
            from django.utils.translation.trans_real import parse_accept_lang_header
            langs = parse_accept_lang_header(accept_language)
            log.msg(u'Accept-Language: {}'.format(unicode(langs)))
            request.language = langs[0][0] if (langs) else settings.LANGUAGE_CODE
            log.msg(u'Activating language: {}'.format(request.language))
            translation.activate(request.language)
            server.currentRequest = request
            with RequestInvocationContext.create(match.func.fn, request, match.args, params) as ctx:
                RequestInvocationContext.dump_all(ctx, u'>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')
                response = yield maybeDeferred(match.func.fn, request, *match.args, **params)
                RequestInvocationContext.dump_all(ctx, u'<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')
            if (issubclass(response.__class__, HttpResponse)):
                log.msg('Response: HttpResponse')
                cls = response.__class__
                try:
                    content_type = response['content-type']
                    log.msg(u'Content-Type: {}'.format(content_type))
                    request.setHeader("Content-Type", content_type)
                except:
                    log.msg(u'Using default content type')
                for key, value in response.items():
                    request.setHeader(key, value)
                status_code = response.__dict__.get('status_code', response.__class__.status_code)
                log.msg(u'Status-Code: {}'.format(status_code))
                request.setResponseCode(status_code)
                content = response.content
                if (content):
                    request.write(content)
            elif (isinstance(response, (unicode))):
                log.msg('Response: UTF-8')
                request.write(response.encode('utf-8'))
            elif (isinstance(response, (str))):
                log.msg('Response: Binary')
                request.write(response)
            else:
                log.msg(u'Response: Unknown ({})'.format(type(response)))
                request.setHeader("Content-Type", 'application/python-pickle')
                request.write(pickle.dumps(response))
            request.finish()
        except Exception, ex:
            log.err(traceback.format_exc())
            log.msg(u'Response-Code: {}'.format(500))
            request.setResponseCode(500)
            request.write('500')
            request.finish()
    returnValue(None)

class DtxCallbackInfo:
    def __init__(self, name):
        self.name = name
        self.count = 1

    def __unicode__(self):
        return u'({}) {}'.format(self.count, self.name)

    def callback(self):
        path = name.split('.')
        return import_module('.'.join(path[:-1])).__dict__[path[-1]]

class DtxTwistedWebCallbackDecorator:

    def __init__(self, fn):
        self.fn = fn
        self.__name__ = fn.__name__
        self.__module__ = fn.__module__

    def __call__(self, request, *args, **kwargs):
        log.err(u'=== DEPRECATED ===')
        if reactor.running and request:
            from dtx.web.client.defer import deferToRemote
            return deferToRemote(request, self.fn, *args, **kwargs).get()
        else:
            from dtx.web.client.defer import remoteAddress
            uri = remoteAddress(self.fn, request, *args, **kwargs)
            log.warn(u'GET: {}'.format(uri))
            return urllib2.urlopen(uri)

    def s(self, *args, **kwargs):
        return self.fn(*args, **kwargs)

class DtxTwistedWebResource(Resource):

    def __init__(self, pattern, urlconf):
        with log.enter(obj=self) as tm:
            Resource.__init__(self)
            self.pattern = pattern
            self.urlconf = urlconf
            self.callbacks = SortedCollection(key=lambda x: x.name)
            self._search_callbacks(urlconf)
            for item in self.callbacks:
                tm.msg(item)

    def _add_callback(self, name):
        try:
            cb = self.callbacks.find(name)
            cb.count += 1
        except:
            path = name.split('.')
            mod = import_module('.'.join(path[:-1]))
            fun = mod.__dict__[path[-1]]
            if (not isinstance(fun, DtxTwistedWebCallbackDecorator)):
                log.msg('Decorating {} ({})'.format(name, fun))
                mod.__dict__[path[-1]] = DtxTwistedWebCallbackDecorator(fun)
            self.callbacks.insert(DtxCallbackInfo(name))

    def _search_callbacks(self, urlconf):
        urlpatterns = urlconf.__dict__.get('urlpatterns', [])
        for item in urlpatterns:
            if (issubclass(item.__class__, urlresolvers.RegexURLPattern)):
                callback_str = item.__dict__.get('_callback_str', None)
                if (callback_str):
                    self._add_callback(callback_str)
                else:
                    callback_str = '.'.join((item._callback.__module__, item._callback.__name__))
                    self._add_callback(callback_str)
                    item._callback = None
                    item._callback_str = callback_str
            elif (issubclass(item.__class__, urlresolvers.RegexURLResolver)):
                self._search_callbacks(item.urlconf_name)

    def render_request(self, request, method):
        with log.enter(obj=self) as tm:
            request.method = method
            request.url = urlparse.urlsplit(request.uri)
            tm.msg(u'Resolving \'{}\' at {}'.format(unicode(request.url.path), self.urlconf))
            try:
                match = urlresolvers.resolve(unicode(request.url.path), urlconf=self.urlconf)
                tm.msg(u'Matched {}'.format(match))
                request.urlconf = self.urlconf
                task.deferLater(reactor, 0, invokeResolverMatch, request, match)
                return NOT_DONE_YET
            except urlresolvers.Resolver404, ex:
                tm.err(u'Not found')
                request.setResponseCode(404)
                return '404'
            except BaseException, ex:
                tm.err(traceback.format_exc())
                request.setResponseCode(500)
                return '500'

    def render_GET(self, request):
        return self.render_request(request, 'GET')

    def render_POST(self, request):
        return self.render_request(request, 'POST')

class DtxWSGIResource(WSGIResource):

    def __init__(self, app):
        if (not os.environ.has_key("DJANGO_SETTINGS_MODULE")):
            log.msg(u'DJANGO_SETTINGS_MODULE environment variable is not defined', logLevel=logging.WARN)
        else:
            log.msg(u'DJANGO_SETTINGS_MODULE = \'{}\''.format(os.environ.get("DJANGO_SETTINGS_MODULE")))
        wsgi_path = app.split('.')
        wsgi_module = import_module('.'.join(wsgi_path[:-1]))
        wsgi_app = getattr(wsgi_module, wsgi_path[-1])
        WSGIResource.__init__(self, reactor, reactor.getThreadPool(), wsgi_app)

@withRequest
class DtxXmlRpcHandler:

    def __init__(self, fn):
        self.fn = fn

    @inlineCallbacks
    def __call__(self, request, *args, **kwargs):
        x = yield maybeDeferred(self.fn, *([request] + [v for v in args]), **kwargs)
        returnValue (x)

class DtxXmlRpcResource(XMLRPC):

    def __init__(self, urls):
        XMLRPC.__init__(self)
        self.urls = urls
        self.handlers = {}

    def lookupProcedure(self, procedurePath):
        with log.enter(obj=self, args={'procedurePath':procedurePath}) as tm:
            try:
                if (self.handlers.has_key(procedurePath)):
                    return self.handlers[procedurePath]
                else:
                    wsgi_path = procedurePath.split('.')
                    wsgi_module = import_module('.'.join(wsgi_path[:len(wsgi_path)-1]))
                    wsgi_app = getattr(wsgi_module, wsgi_path[len(wsgi_path)-1])
                    handler = DtxXmlRpcHandler(wsgi_app)
                    self.handlers[procedurePath] = handler
                    return handler
            except:
                log.msg(traceback.format_exc(), logLevel=logging.ERROR)
                raise xmlrpc.NoSuchFunction(self.NOT_FOUND, "Procedure %s not found" % procedurePath)

class DtxWebSite(Site):

    def __init__(self, uri, sites=None):
        with log.enter(obj=self) as tm:
            Site.__init__(self, None, timeout=60*60*30)
            self.uri = uri
            self.wsgi = None
            self.xmlrpc = None
            self._search_web_sites(sites)

    @classmethod
    def listen(cls, uri, sites):
        with log.enter(obj=cls) as tm:
            url = urlparse.urlparse(uri)
            factory = cls(uri, sites)
            reactor.listenTCP(url.port, factory, interface=url.hostname)
            return factory

    def buildProtocol(self, addr):
        log.msg(u'Building protocol for {}'.format(addr))
        return Site.buildProtocol(self, addr)

    def _search_web_sites(self, sites):
        with log.enter(obj=self) as tm:
            self.web_sites = []
            dtx_web_sites = sites if (sites) else getattr(settings, 'DTX_WEB_SITES', [
                (u'.*', 'wsgi'),
            ])
            for pattern, urls in dtx_web_sites:
                log.msg(u'Registering site: {}'.format((pattern, urls)))
                if (str(urls).startswith('xmlrpc:')):
                    if (not self.xmlrpc):
                        handler = import_module(str(urls)[7:])
                        log.msg(u'Creating new XMLRPC resource for {}'.format(handler))
                        self.xmlrpc = DtxXmlRpcResource(handler)
                    self.web_sites.append((re.compile(pattern), self.xmlrpc))
                elif (str(urls) == 'wsgi'):
                    if (not self.wsgi):
                        app = getattr(settings, 'WSGI_APPLICATION', None)
                        if (not app):
                            raise Exception(u'WSGI_APPLICATION is not defined')
                        log.msg(u'Creating new WSGI resource for {}'.format(app))
                        self.wsgi = DtxWSGIResource(app)
                    self.web_sites.append((re.compile(pattern), self.wsgi))
                else:
                    urlconf = import_module(urls)
                    log.msg(u'Creating new Twisted resource for {}'.format(urlconf))
                    self.web_sites.append((re.compile(pattern), DtxTwistedWebResource(pattern, urlconf)))

    def getResourceFor(self, request):
        with log.enter(obj=self, args={'uri': request.uri}) as tm:
            uri = unicode(urlparse.urljoin(unicode(request.URLPath()), request.uri))
            for pattern, resource in self.web_sites:
                if (pattern.match(uri)):
                    return resource
            return None

##############################################################################################################################
#
##############################################################################################################################

