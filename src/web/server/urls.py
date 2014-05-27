#
# -*- coding: utf-8 -*-
#

import re
import types
import logging

from importlib import import_module as module

from dtx import log
from dtx.utils import profiler

from views.static import serve

class url:
		
	def __init__(self, pattern, handler, kwargs={}):
		p = unicode(pattern)
		if (not handler):
			self.handler = handler	
		elif p[len(p) - 1] == u'$':
			if (hasattr(handler, '__call__')):
				self.handler = handler
			elif (isinstance(handler, (str))):
				p = handler.split('.')
				m = module('.'.join(p[:len(p)-1]))
				h = getattr(m, p[len(p)])
				if (hasattr(h, '__call__')):
					self.handler = h
				else:
					raise Exception(u'Handler is {}, callable expected'.format(type(h)))
			else:
				raise Exception(u'Handler is {}, callable or string expected'.format(type(handler)))
		else:
			p += u'(?P<tail>.*)$'
			if (isinstance(handler, (types.ModuleType))):
				self.handler = handler
			elif (isinstance(handler, (str))):
				self.handler = module(handler)
			else:
				raise Exception(u'Handler is {}, module expected'.format(type(handler)))
		self.pattern = re.compile(p)
		self.kwargs = kwargs
		self.p = p		
		
	def __unicode__(self):
		return u'url({}, {}, {})'.format(self.p, self.handler, self.kwargs)

__all__ = ['url', 'module', 'load_from_file']
