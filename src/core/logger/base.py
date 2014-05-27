#
# -*- coding: utf-8 -*-
#

import logging

class Base:

	def msg(self, message, logLevel=logging.INFO):
		pass

	def fatal(self, message):
		self.msg(message, logLevel=logging.FATAL)
		
	def err(self, message):
		self.msg(message, logLevel=logging.ERROR)

	def warn(self, message):
		self.msg(message, logLevel=logging.WARNING)

	def debug(self, message):
		self.msg(message, logLevel=logging.DEBUG)

class Block(Base):
	pass

class Logger(Base):
	pass
