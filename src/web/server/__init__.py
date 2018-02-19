#
# -*- coding: utf-8 -*-
#

from site import *
from functools import wraps

from twisted.internet.defer import _inlineCallbacks, _DefGen_Return

from django.utils import translation

from dtx.core import logger
log = logger.log(__name__)

currentRequest = None

class saveRequest:
    def __init__(self, g):
        self.g = g
    def __enter__(self):
        global currentRequest
        #log.msg('=== RESTORING REQUEST ===')
        #log.msg(unicode(self.g.r))
        currentRequest = self.g.r
        if currentRequest:
            log.debug(u'Activating language: {}'.format(currentRequest.language))
            translation.activate(currentRequest.language)
    def __exit__(self, type, value, tb):
        global currentRequest
        #log.msg('===== SAVING REQUEST ====')
        #log.msg(unicode(currentRequest))
        self.g.r = currentRequest

class Generator:
    def __init__(self, g):
        global currentRequest
        self.g = g
        #log.msg('===== SAVING REQUEST ====')
        #log.msg(unicode(currentRequest))
        self.r = currentRequest

    def send(self, x):
        with saveRequest(self):
            return self.g.send(x)

    def throw(self, *args, **kwargs):
        with saveRequest(self):
            return self.g.throw(*args, **kwargs)

def webMethod(f):
    @wraps(f)
    def unwindGenerator(*args, **kwargs):
        try:
            gen = f(*args, **kwargs)
        except _DefGen_Return:
            raise TypeError(
                "webMethod requires %r to produce a generator; instead"
                "caught returnValue being used in a non-generator" % (f,))
        if not isinstance(gen, types.GeneratorType):
            raise TypeError(
                "webMethod requires %r to produce a generator; "
                "instead got %r" % (f, gen))
        return _inlineCallbacks(None, Generator(gen), Deferred())
        f._without_request = True
    return unwindGenerator

__all__ = [
    'webMethod',
]
