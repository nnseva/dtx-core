#
# -*- coding: utf-8 -*-
#

import uuid
import json
import urllib
import logging
import random
import traceback
import datetime
import urlparse
import inspect, types

from importlib import import_module

from autobahn.twisted.websocket import listenWS, \
                                       connectWS

from autobahn.wamp1.protocol import WampServerFactory, \
                                    WampServerProtocol, \
                                    WampClientFactory, \
                                    WampClientProtocol, \
                                    exportRpc

from twisted.internet.task import deferLater
from twisted.internet.defer import inlineCallbacks, returnValue, Deferred
from twisted.internet import task
from twisted.internet import reactor

from django.conf import settings

from dtx.utils.snippets.sorted_collection import SortedCollection

from dtx.core import logger
log = logger.log(__name__)

##############################################################################################################################
#
##############################################################################################################################

wamp_connections = SortedCollection(key=lambda x:x.uuid)
wamp_connection_uuid = 1

##############################################################################################################################
#
##############################################################################################################################

class ServerFactory(WampServerFactory):
   
   def __init__(self, uri, apps, debug=False):
       WampServerFactory.__init__(self, uri, debug)
       self.apps = []
       for app in apps:
           if (isinstance(app, (str))):
               mod = import_module(app)
           else:
               mod = app
           log.msg(u'Registering WAMP module {}'.format(unicode(mod)))
           self.apps.append(mod)       

class ServerProtocol(WampServerProtocol):

   api = 'http://wampeer.net/dtx/wamp/v1/'
  
   def __init__(self):
       global wamp_connection_uuid
       #WampServerProtocol.__init__(self, **kwargs)
       self.connect_ts = datetime.datetime.now()
       self.sessions = []
       self.uuid = str(wamp_connection_uuid)
       wamp_connection_uuid += 1
       
   def __unicode__(self):
       return u'<ServerProtocol: {}>'.format(self.uuid)       
   
   @classmethod
   def listen(cls, uri, apps, allowHixie76=False, debug=False):
       with log.enter(obj=cls) as tm:
           global server_factory
           url = urlparse.urlparse(uri)
           server_factory = ServerFactory(uri, apps, debug=debug)
           server_factory.protocol = cls
           server_factory.setProtocolOptions(allowHixie76=allowHixie76)            
           listenWS(server_factory)           
           server_factory.internal_client = InternalClientProtocol.connect(uri, debug)
           return server_factory                   
   
   def age(self):
       return datetime.datetime.now() - self.connect_ts
   
   @exportRpc
   def apis(self):
       apis = [ServerProtocol.api]
       for session in self.sessions:
           apis.append(session.__class__.api)
       return apis 

   @exportRpc
   def ping(self):
       return 'pong' 

   def publishYaaEvent(self, event, broadcast=False):
       global yaa_internal_client
       print u'Publish event {} at {}: {}'.format(self.call_uri, self.uuid, json.dumps(event))
       yaa_internal_client.publish(self.call_uri, event, eligible=[self.sessionid] if (not broadcast) else None)

   def onSessionOpen(self):
       global wamp_connections
       with log.enter(obj=self) as tm:
           try:
               self.debugWamp = settings.DTX_DEBUG_WAMP
               
               wamp_connections.insert(self)
               
               log.debug(u'Connected, {} connection(s) active'.format(len(wamp_connections)))               
                              
               session_rpc = ServerProtocol.api + 'session#'
               log.debug(u'Registering RPC {}'.format(session_rpc))
               self.registerForRpc(self, session_rpc)
               
               for app in self.factory.apps:
                   nm = 0
                   for k in inspect.getmembers(app, inspect.isclass):
                       if k[1].__dict__.has_key("api"):
                           session = k[1](self)
                           self.sessions.append(session)
                           session.onSessionOpen()
                           nm += 1
                   if (not nm):
                        raise Exception(u'Application {} doens\'t have any WAMP APIs'.format(unicode(app)))
                           
               log.debug(u'APIs: ' + unicode(self.apis()))
                              
           except Exception, exc:
               log.msg(traceback.format_exc(), logLevel=logging.ERROR)
               raise
 
   def onClose(self, wasClean, remoteCloseCode, remoteCloseReason):
       global wamp_connections
       with log.enter(obj=self) as tm:
           try:
               if ((not self.__dict__.has_key('connect_ts') or (not self.connect_ts))):
                   log.msg(u'onClose() on a ghost session', logLevel=logging.WARNING)
                   return

               lifetime = self.age()
               log.debug(u'Disconnected {} with reason: {}/{}. Uptime: {}. Still have {} connection(s) online'.format('cleanly' if (wasClean) else 'abnormally', remoteCloseCode, remoteCloseReason, lifetime, len(wamp_connections)))
               self.connect_ts = None
               
               while self.sessions:
                   session = self.sessions.pop()
                   session.onSessionClose()
               
               if (self in wamp_connections):
                   wamp_connections.remove(self)
               else:
                   tm.err('Connection {} not found'.format(self.uuid), logLevel=logging.ERROR)
               
               yaa_info_changed = True
           except Exception, exc:
               log.msg(traceback.format_exc(), logLevel=logging.ERROR)
               raise

##############################################################################################################################
#
##############################################################################################################################

class InternalClientProtocol(WampClientProtocol):

    @classmethod
    def connect(cls, uri, debug=False):
        client_factory = WampClientFactory(uri)
        client_factory.uri = uri
        client_factory.protocol = cls
        connectWS(client_factory)
        return client_factory
        
    def onSessionOpen(self):
        log.msg(u"Internal client connected")                
        
