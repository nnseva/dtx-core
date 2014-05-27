#
# -*- coding: utf-8 -*-
#

from twisted.internet import \
    defer, task, reactor, threads
from twisted.internet.defer import \
    inlineCallbacks, returnValue, Deferred, DeferredList, \
    maybeDeferred, gatherResults, _DefGen_Return
from twisted.internet.task import \
    deferLater
from twisted.internet.threads import \
    deferToThread

#from dtx.web.client.defer import \
#    deferToRemote, iterateRemote

__all__ = [
    '_DefGen_Return',
    'defer',
    'task',
    'reactor',
    'threads',
    'inlineCallbacks',
    'returnValue',
    'Deferred',
    'DeferredList',
    'gatherResults',
    'maybeDeferred',
    'deferLater',
    'deferToThread',
    #'deferToRemote',
    #'iterateRemote',
]
