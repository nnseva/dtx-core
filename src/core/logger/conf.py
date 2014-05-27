#
# -*- coding: utf-8 -*-
#

import sys
import logging

from twisted.python.logfile import DailyLogFile
from twisted.python import log

logLevel = logging.ERROR
logFile = None

def configure(**options):
    global logLevel, logFile
    LEVELS = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }

    logLevel = LEVELS[options.get('loglevel', 'info').lower()]
    logging.basicConfig(level=logLevel)

    logFile = options.get('logfile', None)
    if logFile:
        log.startLogging(DailyLogFile.fromFullPath(logFile))
    else:
        log.startLogging(sys.stdout)


    #observer = log.PythonLoggingObserver()
    #observer.start()

__all__ = ['configure']
