#
# -*- coding: utf-8 -*-
#

from django import get_version
from distutils.version import LooseVersion

if (LooseVersion(get_version()) < LooseVersion('1.8')):
    from optparse import make_option

    options_list = (
        make_option('-f', '--logfile',
            action='store',
            dest='logfile',
            default=None,
            help='Tells server where to log information. Leaving this blank logs to stderr'
        ),
        make_option('-l', '--loglevel',
            action='store',
            dest='loglevel',
            default='info',
            help='Tells server what level of information to log'
        ),
    )
else:
    options_list = (
        dict(args=('-f', '--logfile'),
            kw=dict(
                action='store',
                dest='logfile',
                default=None,
                help='Tells server where to log information. Leaving this blank logs to stderr'
            )
        ),
        dict(args=('-l', '--loglevel'),
            kw=dict(
                action='store',
                dest='loglevel',
                default='info',
                help='Tells server what level of information to log'
            )
        ),
    )

__all__ = ['options_list']
