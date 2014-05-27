#
# -*- coding: utf-8 -*-
#

from dtx.web.core.serializers.base import SerializerBase, registry

from dtx.utils import ujs

from dtx.core import logger
log = logger.log(__name__)

class Serializer(SerializerBase):

    format = 'json'
    ctname = 'application/json'

    @classmethod
    def content_type(cls, **kwargs):
        charset = kwargs.get('charset', None)
        return cls.ctname + '; charset=' + charset if (charset) else cls.ctname

    def serialize(self, data, **kwargs):
        return ujs.dumps(data)

    def deserialize(self, data, **kwargs):
        return ujs.loads(data)

loads = ujs.loads
dumps = ujs.dumps

registry.register(Serializer)

__all__ = [
    'loads',
    'dumps',
]
