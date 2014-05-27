#
# -*- coding: utf-8 -*-
#

import os
import sys
import logging

from importlib import import_module

from twisted.internet import reactor
from twisted.internet.protocol import ProcessProtocol

from django.conf import settings as django_settings

from dtx.core import logger
log = logger.log(__name__, enabled=django_settings.DEBUG)

class WorkerProcess(ProcessProtocol):
    def connectionMade(self):
        log.msg("Process started, pid %s" % (self.transport.pid,))
        self.pid = self.transport.pid

    def processExited(self, reason):
        log.msg("Process %s exited, status %s" % (self.pid, reason.value.exitCode,))

    def outReceived(self, data):
        print data

    def errReceived(self, data):
        print data

def start(process_name, settings=None, logfile=None, uid=None, gid=None, **kwargs):
    from dtx.core.logger.conf import logLevel, logFile
    args =  ['python', sys.argv[0], 'twistd']
    args += ['--settings', settings if (settings) else django_settings.SETTINGS_MODULE]
    args += ['--process', process_name]
    if ((logFile) or (logfile)):
        args += ['--logfile', logfile if (logfile) else logFile]
    if (logLevel):
        args += ['--loglevel', logging.getLevelName(logLevel)]
    if (uid):
        args += ['-O', 'uid={}'.format(uid)]
    if (gid):
        args += ['-O', 'gid={}'.format(gid)]
    for key in kwargs.keys():
        args += ['-O', '{}={}'.format(key, kwargs[key])]
    log.msg(u'Starting {}'.format(' '.join(args)))
    process = WorkerProcess()
    reactor.spawnProcess(process, 'python', args, os.environ, uid=uid, gid=gid)

__all__ = [
    'start',
]
