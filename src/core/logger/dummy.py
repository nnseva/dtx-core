#
# -*- coding: utf-8 -*-
#

import datetime

import base

class Block(base.Block):
    
    def __enter__(self):
        return self
    
    def __exit__(self, type, value, tb):
        pass

    def time(self):
        return datetime.timedelta(0)

    def reportResult(self, value):
    	pass
    
class Logger(base.Logger):

    def __init__(self):
    	pass
    
    def enter(self, name=None, obj=None, args={}, parent=None, enabled=True, verbose=True):
    	return Block()
    
    def msg(self, message, logLevel=None):
        pass

    def fatal(self, message, logLevel=None):
        pass

    def error(self, message, logLevel=None):
        pass

    def warn(self, message, logLevel=None):
        pass

    def debug(self, message, logLevel=None):
        pass
