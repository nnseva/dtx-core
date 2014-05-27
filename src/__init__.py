#
# -*- coding: utf-8 -*-
#

import pkg_resources
try:
    version=pkg_resources.get_distribution('dtx').version
except:
    version="0.0.0"
revision=int('$Id: __init__.py 15888 2013-10-11 04:53:59Z azykov $'.split(' ')[2])

api = 'http://wampeer.net/dtx/v1/'
