#
# -*- coding: utf-8 -*-
#

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

__all__ = ['options_list']
