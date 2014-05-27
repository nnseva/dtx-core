#
# -*- coding: utf-8 -*-
#

import logging
import traceback

from twisted.internet.task import deferLater
from twisted.internet.defer import inlineCallbacks, returnValue, Deferred

from twisted.internet import reactor, protocol
from twisted.protocols.memcache import MemCacheProtocol, DEFAULT_PORT

from django.conf import settings

from dtx.utils.snippets.sorted_collection import SortedCollection

from dtx.core import logger
log = logger.log(__name__)

##############################################################################################################################
#
##############################################################################################################################

connections = []
connection_index = 0

stored_keys = {}

def nextConnection():
    global connection_index
    if (not connections):
        return None
    if (connection_index > len(connections) - 1):
        connection_index = 0
    conn = connections[connection_index]
    connection_index += 1
    return conn    

def getConnection(key):
    global stored_keys
    if (stored_keys.has_key(key)):
        return stored_keys[key]
    else:
        return None

def setConnection(key, conn):
    global stored_keys
    stored_keys[key] = conn
    conn.keys[key] = conn

def deleteKey(key):
    global stored_keys
    conn = getConnection()
    if (conn):
        stored_keys.pop(key)
        conn.keys.pop(key)

##############################################################################################################################
#
##############################################################################################################################
   
class CacheProtocol(MemCacheProtocol):   
    def __init__(self):
        MemCacheProtocol.__init__(self)
        self.keys = {}
    
    @classmethod
    def connect(cls, host='localhost', port=DEFAULT_PORT):
        with log.enter(obj=cls) as tm:
            d = protocol.ClientCreator(reactor, cls).connectTCP(host, port)
            d.addCallback(onCacheConnected)
        
    def connectionLost(self, reason):
        with log.enter(obj=self) as tm:
            while self.keys:
                deleteKey(self.keys[0])

def onCacheConnected(proto):
    global connections
    connections.append(proto)

@inlineCallbacks
def set(key, val, flags=0, expireTime=0):
    with log.enter(args={'key': key}) as tm:
        conn = nextConnection()
        if (conn):
            stored = yield conn.set(key, val, flags, expireTime)
            if (stored):
                setConnection(key, conn)
            returnValue(stored)
        else:
            returnValue(False)

@inlineCallbacks
def get(key, withIdentifier=False):
    with log.enter(args={'key': key}) as tm:
        conn = getConnection(key)
        if (conn):
            flags, value = yield conn.get(key, withIdentifier)
            returnValue((flags, value))
        else:
            returnValue((0, None))

@inlineCallbacks
def delete(key):
    global stored_keys
    with log.enter(args={'key': key}) as tm:
        conn = getConnection(key)
        if (conn):
            deleted = yield conn.delete(key)
            if (deleted):
                deleteKey(key)
            returnValue(deleted)
        else:
            returnValue((0, None))

##############################################################################################################################
#
##############################################################################################################################

if __name__ == '__main__':
    pass
