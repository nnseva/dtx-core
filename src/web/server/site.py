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
from twisted.python.failure import Failure

from django.conf import settings
from django.http import HttpResponse
from django.core import urlresolvers
from django.utils import translation

try:
    from django.urls.resolvers import RegexURLPattern,RegexURLResolver
except ImportError:
    from django.core.urlresolvers import RegexURLPattern,RegexURLResolver

from dtx.core.workflow import *
from dtx.utils.snippets.sorted_collection import SortedCollection

from django.core.handlers.base import BaseHandler

from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.middleware.common import CommonMiddleware

from dtx.core import logger
log = logger.log(__name__)

##############################################################################################################################
#
##############################################################################################################################

def parse_accept_header(accept):
    """Parse the Accept header *accept*, returning a list with pairs of
    (media_type, q_value), ordered by q values.
    """
    result = []
    for media_range in accept.split(","):
        parts = media_range.split(";")
        media_type = parts.pop(0)
        media_params = []
        q = 1.0
        for part in parts:
            (key, value) = part.lstrip().split("=", 1)
            if key == "q":
                q = float(value)
            else:
                media_params.append((key, value))
        result.append((media_type, tuple(media_params), q))
    result.sort(lambda x, y: -cmp(x[2], y[2]))
    return result
    
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
        log.debug(u'New: {}'.format(unicode(context)))
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
            log.debug(framing)
            idx = 1
            for ctx in current_requests:
                log.debug(u'{} ({}) {}'.format('*' if (current == ctx) else ' ', idx, unicode(ctx)))
                idx += 1
        finally:
            log.debug(framing)

##############################################################################################################################
#
##############################################################################################################################

@inlineCallbacks
def invokeResolverMatch(request, match):
    global current_requests
    from dtx.web import server
    with log.enter() as tm:
        base_handler = BaseHandler()
        try:
            base_handler.load_middleware()
            # META
            request.META = {}
            request.META['REQUEST_METHOD'] = request.method
            # Cookies
            request.COOKIES = {}
            request.COOKIES['sessionid'] = request.getCookie('sessionid')
            # Arguments
            request.GET = request.args
            # Accept
            accept = request.getHeader('accept')
            if (accept):
                log.debug(u'Accept: {}'.format(accept))
                request.accept = parse_accept_header(accept)
                request.META['HTTP_ACCEPT'] = accept
            # Args
            content_type = request.getHeader('content-type')
            if (content_type):
                log.debug(u'Content-Type: {}'.format(content_type))
                request.META['CONTENT_TYPE'] = content_type
                request.content_type = content_type.split(';')
            else:
                request.content_type = []
            request.content_type_name = request.content_type[0] if (len(request.content_type) >= 1) else None
            request.content_type_args = request.content_type[1] if (len(request.content_type) >= 2) else None
            form = {}
            # TODO: Make decoders registry
            if (request.content_type_name == 'application/python-pickle'):
                content = request.content.read()
                form = pickle.loads(content)
            elif (request.content_type_name == 'application/json'):
                content = request.content.read()
                form = json.loads(content)
            elif (request.content_type_name == 'application/x-yaml'):
                content = request.content.read()
                form = yaml.load(content)
            request.POST = form
            request.REQUEST = dict(chain(request.GET.iteritems(), request.POST.iteritems()))
            # Parameters
            kwargs = match.kwargs
            params = dict(chain(kwargs.iteritems(), form.iteritems()))
            # Language
            accept_language = request.getHeader('accept-language')
            accept_language = accept_language if (accept_language) else 'en-US,en;q=0.8'
            request.META['HTTP_ACCEPT_LANGUAGE'] = accept_language
            from django.utils.translation.trans_real import parse_accept_lang_header
            langs = parse_accept_lang_header(accept_language)
            log.debug(u'Accept-Language: {}'.format(unicode(langs)))
            request.language = langs[0][0] if (langs) else settings.LANGUAGE_CODE
            log.debug(u'Activating language: {}'.format(request.language))
            translation.activate(request.language)
            # Middleware
            for middleware_method in base_handler._request_middleware:
                try:
                    response = middleware_method(request)
                except:
                    pass
            # Invoke
            server.currentRequest = request
            with RequestInvocationContext.create(match.func, request, match.args, params) as ctx:
                #RequestInvocationContext.dump_all(ctx, u'>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')
                try:
                    response = yield maybeDeferred(match.func, request, *match.args, **params)
                except Exception:
                    Failure().printTraceback()
                    raise
                #RequestInvocationContext.dump_all(ctx, u'<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')
            if (issubclass(response.__class__, HttpResponse)):
                log.debug('Response: HttpResponse')
                cls = response.__class__
                try:
                    content_type = response['content-type']
                    log.debug(u'Content-Type: {}'.format(content_type))
                    request.setHeader("Content-Type", content_type)
                except:
                    log.debug(u'Using default content type')
                for key, value in response.items():
                    request.setHeader(key, value)
                status_code = response.__dict__.get('status_code', response.__class__.status_code)
                log.debug(u'Status-Code: {}'.format(status_code))
                request.setResponseCode(status_code)
                content = response.content
                if (content):
                    request.write(content)
            elif (isinstance(response, (unicode))):
                log.debug('Response: UTF-8')
                request.write(response.encode('utf-8'))
            elif (isinstance(response, (str))):
                log.debug('Response: Binary')
                request.write(response)
            else:
                log.debug(u'Response: Unknown ({})'.format(type(response)))
                request.setHeader("Content-Type", 'application/python-pickle')
                request.write(pickle.dumps(response))
            request.finish()
        except Exception, ex:
            log.err(traceback.format_exc())
            log.debug(u'Response-Code: {}'.format(500))
            request.setResponseCode(500)
            request.write('500')
            request.finish()
    returnValue(None)

class DtxCallbackInfo:
    def __init__(self, name, callback):
        self.name = name
        self._callback = callback
        self.count = 1

    def __unicode__(self):
        return u'({}) {}'.format(self.count, self.name)

    def callback(self):
        if not self._callback:
            path = name.split('.')
            self._callback = import_module('.'.join(path[:-1])).__dict__[path[-1]]
        return self._callback

class DtxTwistedWebResource(Resource):

    def __init__(self, pattern, urlconf):
        with log.enter(obj=self) as tm:
            Resource.__init__(self)
            self.pattern = pattern
            self.urlconf = urlconf

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

    def render_PUT(self, request):
        return self.render_request(request, 'PUT')

    def render_HEAD(self, request):
        return self.render_request(request, 'HEAD')

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
                log.err(traceback.format_exc())
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
        log.debug(u'Building protocol for {}'.format(addr))
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

