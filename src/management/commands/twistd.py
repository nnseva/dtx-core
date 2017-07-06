#
# -*- coding: utf-8 -*-
#

import os
import sys
import traceback
import logging

from itertools import chain
from importlib import import_module

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.http import QueryDict

from twisted.internet import reactor

from dtx.core.logger.opts import options_list as dtx_logger_option_list
from dtx.core.logger.conf import configure as dtx_logger_configure

from dtx.process import started_process_list

from dtx.core import logger
log = logger.log(__name__)

from django import get_version
from distutils.version import LooseVersion

if (LooseVersion(get_version()) < LooseVersion('1.8')):
    from optparse import make_option
    option_list  = BaseCommand.option_list
    option_list += dtx_logger_option_list
    option_list += (
        make_option('--node',
            action='store',
            type='string',
            dest='node_name',
            default=getattr(settings, 'DTX_DEFAULT_NODE', 'dtx.nodes.default'),
            help='Node module to start',
        ),
        make_option('--process',
            action='store',
            type='string',
            dest='node_name',
            default=getattr(settings, 'DTX_DEFAULT_NODE', 'dtx.nodes.default'),
            help='Node module to start [DEPRECATED!]',
        ),
        make_option('-O', '--option',
            action='append',
            type='string',
            dest='node_opts',
            default=[],
            help='Node',
        ),
        make_option('--thread-pool-size',
            action='store',
            type='string',
            dest='thread_pool_size',
            default=getattr(settings, 'DTX_THREAD_POOL_SIZE', 16),
            help='Thread pool size',
        ),
    )
else:
    option_list = ()
    option_list += dtx_logger_option_list
    option_list += (
        dict(args=('--node',),
            kw=dict(
                action='store',
                type=str,
                dest='node_name',
                default=getattr(settings, 'DTX_DEFAULT_NODE', 'dtx.nodes.default'),
                help='Node module to start',
            )
        ),
        dict(args=('--process',),
            kw=dict(
                action='store',
                type=str,
                dest='node_name',
                default=getattr(settings, 'DTX_DEFAULT_NODE', 'dtx.nodes.default'),
                help='Node module to start [DEPRECATED!]',
            )
        ),
        dict(args=('-O', '--option'),
            kw=dict(
                action='append',
                type=str,
                dest='node_opts',
                default=[],
                help='Node',
            )
        ),
        dict(args=('--thread-pool-size',),
            kw=dict(
                action='store',
                type=str,
                dest='thread_pool_size',
                default=getattr(settings, 'DTX_THREAD_POOL_SIZE', 16),
                help='Thread pool size',
            )
        ),
    )

class Command(BaseCommand):
    can_import_settings = True

    if (LooseVersion(get_version()) < LooseVersion('1.8')):
        option_list = option_list
    else:
        @classmethod
        def add_arguments(cls,parser):
            for o in option_list:
                parser.add_argument(*o['args'],**o['kw'])

    def handle(self, *args, **options):
        try:
            dtx_logger_configure(**options)
            node_name = options.get('node_name')
            node_opts = options.get('node_opts')

            thread_pool_size = options.get('thread_pool_size')
            if (thread_pool_size):
                    reactor.suggestThreadPoolSize(thread_pool_size)

            log.msg(u'Loading {}'.format(node_name))
            node = import_module(node_name)

            opts = dict(chain.from_iterable(d.iteritems() for d in [QueryDict(v).dict() for v in node_opts]))
            log.msg(u'Starting {} with args {}, kwargs {}'.format(node_name, args, opts))
            node.start(*args, **opts)

            log.msg(u'Running {}'.format(node_name))
            reactor.run()

            # TODO: Implement proper shutdown process
            for pid, process in started_process_list.items():
                log.msg('Stalled subprocess: {}'.format(pid))
                process.transport.signalProcess('KILL')

            log.msg(u'Finished')
        except Exception, exc:
            log.err(traceback.format_exc())
            raise
