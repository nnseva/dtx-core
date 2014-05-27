#
# -*- coding: utf-8 -*-
#

import uuid
import json
import urllib
import logging
import random
import traceback

from autobahn.websocket import connectWS
from twisted.internet import reactor
from twisted.internet.protocol import ReconnectingClientFactory
from autobahn.wamp import WampClientFactory, \
                          WampClientProtocol

from twisted.internet.task import deferLater
from twisted.internet.defer import inlineCallbacks, returnValue, Deferred

from twisted.internet import task
from twisted.internet import reactor

from dtx.utils.snippets.sorted_collection import SortedCollection

from dtx.core import logger
log = logger.log(__name__)

##############################################################################################################################
#
##############################################################################################################################

class EvalControlBlock:
    
    def __init__(self, id, df):
        self.id = id
        self.df = df

##############################################################################################################################
#
##############################################################################################################################

class ClientFactory(WampClientFactory, ReconnectingClientFactory):
    
    def startedConnecting(self, connector):
        log.msg(u'Started to connect')

    def buildProtocol(self, addr):
        log.msg(u'Connected from {}'.format(addr))
        self.resetDelay()
        return WampClientFactory.buildProtocol(self, addr)

    def clientConnectionLost(self, connector, reason):
        with log.enter(obj=self) as tm:
            log.err(u'Connection lost, {}'.format(reason))
            ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        with log.enter(obj=self) as tm:
            log.err(u'Connection failed, {}'.format(reason))
            ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

##############################################################################################################################
#
##############################################################################################################################

class ClientProtocol(WampClientProtocol):

    def __init__(self):
        #WampClientProtocol.__init__(self)
        self.evalSessions = SortedCollection(key=lambda x:x.id)

    @classmethod
    def connect(cls, uri, debug=False):
        global client_factory
        client_factory = ClientFactory(uri)
        client_factory.uri = uri
        client_factory.protocol = cls
        connectWS(client_factory)
        return client_factory
        
    def done(self, *args):
        self.sendClose()
        reactor.stop()
    
    def onConnected(self):
        pass
    
    def onSessionOpen(self):
        log.msg(u"Connected")
        self.onConnected()       

    @inlineCallbacks
    def eval(self, algo, data):
        df = Deferred()
        df.callback(None)

    @inlineCallbacks
    def execjs(self, command, broadcast=False):
        with log.enter(obj=self) as tm:
            uri = yaa_api + 'session#execjs'
            log.msg('Calling {} {}'.format(uri, {'exec': command}))
            yield self.call(uri, {'exec': command}, broadcast)        
        
    @inlineCallbacks
    def evaljs(self, js, params, role=0, timeout=None):
        with log.enter(obj=self) as tm:
           try:
                uri = yaa_api + 'session#evaljs'
                log.msg(u'Calling {} {}'.format(uri, {'js': js, 'params': type(params), 'timeout': timeout if (timeout) else 0}))
                id = yield self.call(uri, js, params, role, timeout if (timeout) else 0)
                df = Deferred()
                self.evalSessions.insert(EvalControlBlock(id, df))
                yield df         
           except Exception, exc:
                log.msg(traceback.format_exc(), level=logging.ERROR)
                raise
        
    def reloadjs(self, command, broadcast=False):
        self.publish(yaa_api + 'call', {'javascript': {'exec': 'window.location = "/yaa/"'}})
        
##############################################################################################################################
#
##############################################################################################################################

if __name__ == '__main__':
    pass
