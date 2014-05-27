#
# -*- coding: utf-8 -*-
#

from django.http import HttpResponse

from dtx.core import logger
log = logger.log(__name__)

class SerializerBase:

	@classmethod
	def content_type(self, **kwargs):
		return 'application/octet-stream'

	def serialize(self, data, **kwargs):
		pass

	def deserialize(self, data, **kwargs):
		pass

class Registry:
	def __init__(self):
		self.format_by_content_type = {}
		self.serializers_by_format = {}

	def register(self, serializer):
		self.format_by_content_type[serializer.content_type()] = serializer.format
		self.serializers_by_format[serializer.format] = serializer

	def create(self, format):
		return self.serializers_by_format[format]()

	def parse_content_type(self, content_type):
		ctype = content_type.split(';')
		if (self.format_by_content_type.has_key(ctype[0])):
			format = self.format_by_content_type[ctype[0]]
			params = {}
			if len(ctype) > 1:
				opts = ctype[1].split('=')
				params[opts[0].strip()] = opts[1].strip()
			return (format, params)
		else:
			return (None, None)

	def content_type_by_format(self, format, **kwargs):
		serializer = self.create(format)
		return serializer.__class__.content_type(**kwargs)

	def read_from_string(self, format, data, **kwargs):
		serializer = self.create(format)
		return serializer.deserialize(data, **kwargs)

	def render_to_string(self, format, data, **kwargs):
		serializer = self.create(format)
		return serializer.serialize(data, **kwargs)

	def render_to_response(self, format, data, content_type=None, status=None, prepared=False, **kwargs):
		serializer = self.create(format)
		content = data if (prepared) else serializer.serialize(data, **kwargs)
		return HttpResponse(content, content_type=content_type if content_type else serializer.__class__.content_type(**kwargs), status=status)

registry = Registry()

def parse_content_type(content_type):
	global registry
	return registry.parse_content_type(content_type)

def content_type_by_format(format, **kwargs):
	global registry
	return registry.content_type_by_format(format, **kwargs)

def read_from_string(format, data, **kwargs):
	global registry
	return registry.read_from_string(format, data, **kwargs)

def render_to_string(format, data, **kwargs):
	global registry
	return registry.render_to_string(format, data, **kwargs)

def render_to_response(format, data, content_type=None, status=None, prepared=False, **kwargs):
	global registry
	return registry.render_to_response(format, data, content_type, status, **kwargs)

__all__ = [
	'SerializerBase',
	'registry',
	'parse_content_type',
	'content_type_by_format',
	'read_from_string',
	'render_to_string',
	'render_to_response',
]
