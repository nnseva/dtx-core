#
# -*- coding: utf-8 -*-
#

from dtx.web.core.serializers.base import SerializerBase, registry

import yaml as pyyaml

from dtx.core import logger
log = logger.log(__name__)

class Serializer(SerializerBase):

    format = 'pickle'
    ctname = 'application/x-yaml'

    @classmethod
    def content_type(cls, **kwargs):
        charset = kwargs.get('charset', None)
        return cls.ctname + '; charset=' + charset if (charset) else cls.ctname

    def serialize(self, data, **kwargs):
        return pyyaml.dump(data)

    def deserialize(self, data, **kwargs):
        return pyyaml.load(data)

registry.register(Serializer)
