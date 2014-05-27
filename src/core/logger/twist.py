#
# -*- coding: utf-8 -*-
#

import math
import datetime
import logging
import traceback

from twisted.python import log as txlog

import base
import dummy

class Printer:
    @classmethod
    def format(cls, message, logLevel=logging.INFO):
        prefix = u'---'
        if (logLevel >= logging.ERROR):
            prefix = u'ERR'
        elif (logLevel >= logging.WARNING):
            prefix = u'WRN'
        if (logLevel <= logging.DEBUG):
            prefix = u'***'
        prefix += u' '
        return prefix + unicode(message)

    @classmethod
    def write(cls, message, logLevel=logging.INFO):
        if (logLevel <= logging.DEBUG):
            print message
        elif (logLevel >= logging.ERROR):
            txlog.err(message)
        else:
            txlog.msg(message, logLevel=logLevel)

    @classmethod
    def msg(cls, message, logLevel=logging.INFO):
        Printer.write(Printer.format(message, logLevel), logLevel = logLevel)

class Block(base.Block):

    def __init__(self, name=None, module=None, obj=None, args={}, parent=None, verbose=True):
        self.name = module if module else u''
        if (obj):
            if (hasattr(obj, '__class__')):
                self.name = u'.'.join((self.name, obj.__class__.__name__))
            elif (hasattr(obj, '__name__')):
                self.name = u'.'.join((self.name, obj.__name__))
        if (not name):
            stack = traceback.extract_stack(limit=3)
            file, line, func, code = stack[0]
            self.name = u'.'.join((self.name, unicode(func))) + '(' + u', '.join([key + '=' + args[key] for key in args.keys()]) + ')'
        else:
            self.name += unicode(name)
            if (args):
                self.name += '(' + u', '.join([key + '=' + args[key] for key in args.keys()]) + ')'
        self.parent = parent

        self.verbose = verbose
        self.result = None
        self.children = {}

    def __enter__(self):
        self.ts = datetime.datetime.now()
        if (self.verbose):
            Printer.write(u'==> {}'.format(self.name), logLevel=logging.DEBUG)
        return self

    def __exit__(self, type, value, tb):
        et = self.time()
        if (self.parent):
            parent = self.parent
            if (parent.children.has_key(self.name)):
                parent.children[self.name] += et
            else:
                parent.children[self.name] = et
        if (self.verbose):
            Printer.write(u'<== {}{}, time {}'.format(self.name, (u', {}'.format(self.result)) if self.result else '', et), logLevel=logging.DEBUG)
            if (len(self.children) > 0):
                ct = datetime.timedelta(0)
                for cname in self.children.keys():
                    child = self.children[cname]
                    ct += child
                    Printer.write('--- {}: {} [{}%]'.format(cname, child, '%3.2f' % ((float(child.total_seconds()) / float(et.total_seconds())) * 100.)), logLevel=logging.DEBUG)
                ctp = 100. - ((float(ct.total_seconds()) / float(et.total_seconds())) * 100.)
                cts = '%3.2f' % (ctp)
                if (cts <> '0.00'):
                    Printer.write('--- Other: {} [{}%]'.format(et - ct, cts), logLevel=logging.DEBUG)

    def msg(self, message, logLevel=logging.DEBUG):
        Printer.msg(u'/{}/ {}'.format(unicode(self.time()), message), logLevel=logLevel)

    def time(self):
        ts = datetime.datetime.now()
        return ts - self.ts

    def reportResult(self, value):
        self.result = unicode(value)

class Logger(base.Logger):
    def __init__(self, module):
        self.module = module

    def enter(self, name=None, obj=None, args={}, parent=None, enabled=True, verbose=True):
        if (not enabled):
            return dummy.Block()
        return Block(name, self.module, obj, args, parent, verbose)

    def msg(self, message, logLevel=logging.INFO):
        Printer.msg(message, logLevel=logLevel)
