#
# -*- coding: utf-8 -*-
#

import os
import six
import logging
import traceback
import urllib
import urllib2
import datetime

import yaml

from importlib import import_module
from urlparse import urlparse

import cPickle as pickle

from cStringIO import StringIO
from urlparse import urljoin

from twisted.internet import \
    defer, task, reactor, threads
from twisted.internet.defer import \
    inlineCallbacks, returnValue, Deferred, DeferredList, \
    maybeDeferred, gatherResults, _DefGen_Return
from twisted.internet.threads import \
    deferToThread
from twisted.internet.error import \
    ConnectionRefusedError, TCPTimedOutError, ConnectionLost, TimeoutError
from twisted.web._newclient import ResponseNeverReceived

from twisted.internet import task
from twisted.internet import reactor
from twisted.web.client import getPage

from twisted.internet.ssl import ClientContextFactory
from twisted.internet.protocol import Protocol
from twisted.web.client import Agent, CookieAgent, HTTPConnectionPool
from twisted.web.client import FileBodyProducer
from twisted.web.http_headers import Headers

from django.conf import settings
from django.core import urlresolvers

from dtx.utils.snippets.sorted_collection import SortedCollection

from dtx import version as dtx_version
from dtx.web.core.serializers import *

from dtx.core import logger
log = logger.log(__name__)

##############################################################################################################################
#
##############################################################################################################################

class DeferSettings:
    def __init__(self):
        from twisted import version as twisted_version
        sysname, nodename, release, version, machine = os.uname()
        self.agent = getattr(settings, 'DTX_WEB_DEFER_AGENT', 'Twisted Web Client ({}; {}) {}'.format(sysname, machine, twisted_version))
        self.connectTimeout = getattr(settings, 'DTX_WEB_DEFER_CONNECT_TIMEOUT', 30)
        self.maxAttempts = getattr(settings, 'DTX_WEB_DEFER_MAX_ATTEMPTS', 30)

deferSettings = DeferSettings()

##############################################################################################################################
#
##############################################################################################################################

class RemoteWorker:
    def __init__(self, address):
        self.address = address
        self.disabled_ts = None
        self.active_tasks_count = 0

    def __unicode__(self):
        return '<Worker: {} ({} active tasks)>'.format(unicode(self.address), self.active_tasks_count)

    def __enter__(self):
        self.active_tasks_count += 1
        return self

    def __exit__(self, type, value, tb):
        self.active_tasks_count -= 1

    def suspend(self):
        self.disabled_ts = datetime.datetime.now()

    def enabled(self):
        if (self.disabled_ts):
            if (datetime.datetime.now() - self.disabled_ts < datetime.timedelta(seconds=30)):
                return False
            else:
                self.disabled_ts = None
        return self.active_tasks_count <= 4

class RemoteConfig:
    def __init__(self, urlconf):
        self.urlconf = urlconf
        self.workers = SortedCollection(key=lambda x: x.address)
        self.index = 0

    def __unicode__(self):
        return u'{}: {}'.format(unicode(self.urlconf), len(self.workers))

    def addWorker(self, address):
        try:
            self.workers.find(address)
        except:
            log.msg(u'Registering {} for {}'.format(address, self.urlconf))
            self.workers.insert(RemoteWorker(address))

    def delWorker(self, address):
        try:
            worker = self.workers.find(address)
            log.msg(u'Unregistering {} for {}'.format(address, self.urlconf))
            self.workers.remove(worker)
        except:
            pass
        return len(self.workers)

    def nextWorker(self):
        with log.enter(obj=self) as tm:
            if (not self.workers):
                log.err(u'No registered workers for {}'.format(self.urlconf))
                return None
            start_index = self.index
            while (42):
                if (self.index > len(self.workers) - 1):
                    self.index = 0
                worker = self.workers[self.index]
                self.index += 1
                if (worker.enabled()):
                    tm.msg(u'Returning {}/{}: {}'.format(self.index, len(self.workers), worker))
                    return worker
                if (start_index == self.index):
                    log.err(u'No free workers for {}'.format(self.urlconf))
                    return None

class RemoteNodes:

    def __init__(self):
        self.configs = SortedCollection(key=lambda x: x.urlconf)
        log.msg(u'Registering static web sites')
        for address, urlconf in getattr(settings, 'DTX_WEB_REMOTE_SITES', []):
            log.msg(u'Registering {} for {}'.format(address, urlconf))
            self.addWorker(address, urlconf)

    def __unicode__(self):
        return u', '.join([unicode(v) for v in self.configs])

    def addWorker(self, address, urlconf):
        conf = None
        try:
            conf = self.configs.find(urlconf)
        except:
            log.msg(u'Registering {}'.format(urlconf))
            conf = RemoteConfig(urlconf)
            self.configs.insert(conf)
        conf.addWorker(address)

    def delWorker(self, address, urlconf):
        try:
            conf = self.configs.find(urlconf)
            if not conf.delWorker(address):
                log.msg(u'Unregistering {}'.format(urlconf))
                self.configs.remove(conf)
        except:
            pass

    def nextWorker(self, urlconf):
        with log.enter(obj=self) as tm:
            try:
                conf = self.configs.find(urlconf.__name__)
                return conf.nextWorker()
            except:
                log.err(traceback.format_exc())
                for cfg in self.configs:
                    log.err(unicode(cfg))
                return None

remote_nodes = RemoteNodes()

##############################################################################################################################
#
##############################################################################################################################

def resolveAddress(name, urlconf, *args, **kwargs):
    global remote_nodes
    with log.enter(args=dict(urlconf=unicode(urlconf))) as tm:
        if urlconf:
            try:
                uri = urlresolvers.reverse(name, urlconf, args, kwargs)
                return (uri, urlconf)
            except Exception:
                return resolveAddress(name, None, args, kwargs)
        else:
            for cf in remote_nodes.configs:
                try:
                    urlconf = import_module(cf.urlconf)
                    uri = urlresolvers.reverse(name, urlconf, args, kwargs)
                    return (uri, urlconf)
                except Exception:
                    #log.msg(traceback.format_exc(), logLevel=logging.ERROR)
                    pass
            return (None, None)

def remoteAddress(fn, request, *args, **kwargs):
    global remote_nodes
    with log.enter() as tm:
        name = fn
        uri, urlconf = resolveAddress(name, request.urlconf if request else None, *args, **kwargs)
        if not uri:
            raise Exception('Cannot resolve URI for {} (args={}, kwargs={}) in {}'.format(name, args, kwargs, unicode(remote_nodes)))
        while True:
            try:
                worker = remote_nodes.nextWorker(urlconf)
                if not worker:
                    raise Exception('Cannot find an active worker for {} ({}) at {}'.format(name, uri, unicode(urlconf)))
                address = urljoin(worker.address, uri)
                return address.encode('utf-8')
            except BaseException, ex:
                log.msg(traceback.format_exc(), logLevel=logging.ERROR)
                raise

##############################################################################################################################
#
##############################################################################################################################

class WebClientContextFactory(ClientContextFactory):
    def getContext(self, hostname, port):
        return ClientContextFactory.getContext(self)

class WebBodyCollector(Protocol):
    def __init__(self, finished):
        self.finished = finished
        self.body = ''

    def dataReceived(self, bytes):
        self.body += bytes

    def connectionLost(self, reason):
        log.msg('Finished receiving body with reason {}'.format(reason.getErrorMessage()))
        self.finished.callback(None)

class WebClientAgentsPool:

    def __init__(self, persistent=True):
        self.persistent = persistent
        self.agents = SortedCollection(key=lambda x: x.url.netloc)
        self.pool = HTTPConnectionPool(reactor)
        self.pool.maxPersistentPerHost = getattr(settings, 'DTX_WEB_DEFER_MAX_PERSISTENT_PER_HOST', 8)
        self.pool.cachedConnectionTimeout = getattr(settings, 'DTX_WEB_DEFER_CONNECT_TIMEOUT', 10)

    def createAgent(self, uri):
        url = urlparse(uri)
        try:
            agent = self.agents.find(url.netloc)
            log.msg(u'Using existing agent for {}'.format(url.netloc))
            agent.url = url
            self.agents.remove(agent)
            return agent
        except:
            log.msg(u'Creating new agent for {}'.format(url.netloc))
            agent = WebClientAgent(self, url)
            return agent

    def returnAgent(self, agent):
        if (self.persistent):
            log.msg(u'Returning agent to the pool'.format(self.url.netloc))
            self.agents.insert(agent)

class WebClientAgent:

    def __init__(self, pool, url):
        global deferSettings
        self.pool = pool
        self.url = url
        #self.contextFactory = WebClientContextFactory()
        #self.agent = Agent(reactor, self.contextFactory, connectTimeout=deferSettings.connectTimeout, pool=self.pool.pool)
        self.agent = Agent(reactor, connectTimeout=deferSettings.connectTimeout, pool=self.pool.pool)

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        self.pool.returnAgent(self)

    def request(self, method, headers=None, body=None):
        return self.agent.request(method, self.url.geturl(), headers, body)

agentsPool = WebClientAgentsPool(False)

##############################################################################################################################
#
##############################################################################################################################

class MaxAttemptsReached(BaseException):
    pass

class TryLater(BaseException):
    pass

class RemoteDeferrer:
    def __init__(self, request, fn, *args, **kwargs):
        self.request = request
        self.args = args
        self.kwargs = kwargs
        self.name = fn
        self.uri, self.urlconf = resolveAddress(self.name, None, *args, **kwargs)
        #self.uri, self.urlconf = None, None
        self.method_name = 'GET'
        self.method_kwargs = None

    @inlineCallbacks
    def process(self):
        global remote_nodes, deferSettings, agentsPool
        with log.enter() as tm:
            #if not self.uri:
            #    self.uri, self.urlconf = resolveAddress(self.name, None, *self.args, **self.kwargs)
            if not self.uri:
                raise Exception('URI for {} is not resolved (args={}, kwargs={}) in {}'.format(self.name, self.args, self.kwargs, unicode(remote_nodes)))
            while True:
                worker = None
                address = None
                try:
                    worker = remote_nodes.nextWorker(self.urlconf)
                    if not worker:
                        log.warn(u'Cannot find an active worker for {} at {}'.format(self.name, unicode(self.urlconf)))
                        raise TryLater()
                    with worker:
                        address = urljoin(worker.address, self.uri).encode('utf-8')
                        with agentsPool.createAgent(address) as agent:
                            headers = Headers({
                                'Accept': ['application/python-pickle,*/*;q=0.8'],
                                'Accept-Encoding': ['gzip,deflate,sdch'],
                                'Connection': ['keep-alive'],
                                'User-Agent': [deferSettings.agent],
                                'X-Requested-With': ['dtx.web.client.defer'],
                            })
                            accept_language = None
                            try:
                                accept_language = self.request.getHeader('accept-language')
                            except:
                                pass
                            if (accept_language):
                                headers.addRawHeader('Accept-Language', accept_language)
                            else:
                                headers.addRawHeader('Accept-Language', 'en-US,en;q=0.8')
                            response = None
                            if (self.method_name == 'POST'):
                                '''
                                headers.addRawHeader('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8')
                                if (args):
                                    self.method_kwargs['args'] = args
                                pkwargs = {}
                                for k in self.method_kwargs.keys():
                                    pkwargs[k] = pickle.dumps(self.method_kwargs[k])
                                log.msg(u'POST: {}'.format(address))
                                form = urllib.urlencode(pkwargs)
                                body = FileBodyProducer(StringIO(form))
                                '''
                                headers.addRawHeader('Content-Type', 'application/python-pickle')
                                body = FileBodyProducer(StringIO(pickle.dumps(self.method_kwargs)))
                                response = yield agent.request('POST', headers, body)
                            elif (self.method_name == 'GET'):
                                log.msg(u'GET: {}'.format(address))
                                response = yield agent.request('GET', headers)
                            log.msg('Response: {} {} ({})'.format(response.version, response.code, response.phrase))
                            if (response.code == 200):
                                finished = Deferred()
                                collector = WebBodyCollector(finished)
                                response.deliverBody(collector)
                                x = yield finished
                                if response.headers.hasHeader('content-type'):
                                    content_type = response.headers.getRawHeaders('content-type', ['application/octet-stream'])[0]
                                    log.msg('Content-Type: {}'.format(content_type))
                                    format, params = parse_content_type(content_type)
                                    if (format):
                                        log.msg(u'Decoding as "{}"'.format(format))
                                        result = read_from_string(format, collector.body, **params)
                                        returnValue(result)
                                log.msg(u'Returning non-decoded content')
                                returnValue(collector.body)
                            elif (response.code >= 500) and (response.code <= 599):
                                raise TryLater()
                            else:
                                raise Exception(response.phrase)
                except _DefGen_Return:
                    raise
                except ConnectionRefusedError:
                    log.err(u'Connection refused {}'.format(address))
                    if (worker):
                        worker.suspend()
                    raise TryLater()
                except TCPTimedOutError:
                    log.err(u'TCP Timed out {}'.format(address))
                    raise TryLater()
                except TimeoutError:
                    log.err(u'Timed out {}'.format(address))
                    raise TryLater()
                except ConnectionLost:
                    log.err(u'Connection lost {}'.format(address))
                    raise TryLater()
                except ResponseNeverReceived:
                    log.err(u'Response never received {}'.format(address))
                    raise TryLater()
                except TryLater:
                    raise
                except BaseException, ex:
                    log.err(traceback.format_exc())
                    raise

    @inlineCallbacks
    def retry(self, delay):
        with log.enter() as tm:
            log.msg(u'{} second(s) have passed'.format(delay))
            x = yield self.process()
            returnValue(x)

    @inlineCallbacks
    def execute(self):
        global deferSettings
        try:
            result = yield self.process()
            returnValue(result)
        except TryLater:
            delay = 0
            for step in range(deferSettings.maxAttempts - 1):
                try:
                    log.msg(u'========= Will try again in {} second(s) =========='.format(delay))
                    result = yield task.deferLater(reactor, delay, lambda:self.retry(delay))
                    returnValue(result)
                except _DefGen_Return:
                    raise
                except TryLater:
                    if (delay < 60):
                        delay = delay * 2 if (delay) else 1
            raise MaxAttemptsReached()
        except _DefGen_Return:
            raise
        except BaseException, ex:
            raise

    def get(self, **kwargs):
        self.method_name = 'GET'
        self.method_kwargs = kwargs
        return self.execute()

    def post(self, **kwargs):
        self.method_name = 'POST'
        self.method_kwargs = kwargs
        return self.execute()

def deferToRemote(request, fn, *args, **kwargs):
    return RemoteDeferrer(request, fn, *args, **kwargs)

@inlineCallbacks
def iterateRemote(tasks_iterator, limit=16):
    with log.enter() as rt:
        results = []
        tasks = []
        idx = 0
        for task in tasks_iterator:
            tasks.append(task)
            idx += 1
            if (idx == limit):
                rt.msg('Gathering results from {} tasks'.format(len(tasks)))
                rr = yield gatherResults(tasks)
                results.extend(rr)
                idx -= len(tasks)
                tasks = []
        if (idx > 0):
            rt.msg('Gathering results from {} tasks'.format(len(tasks)))
            rr = yield gatherResults(tasks)
            results.extend(rr)
        returnValue(results)

