#
# -*- coding: utf-8 -*-
#

from dtx.web.core.serializers.base import SerializerBase, registry

import cPickle as pickle

from dtx.core import logger
log = logger.log(__name__)

class Serializer(SerializerBase):

    format = 'pickle'
    ctname = 'application/python-pickle'

    @classmethod
    def content_type(cls, **kwargs):
        protocol = kwargs.get('protocol', None)
        return cls.ctname + '; protocol=' + protocol if (protocol) else cls.ctname

    def serialize(self, data, **kwargs):
        return pickle.dumps(data, kwargs.get('protocol', 0))

    def deserialize(self, data, **kwargs):
        return pickle.loads(data)

loads = pickle.loads
dumps = pickle.dumps

registry.register(Serializer)

__all__ = [
    'loads',
    'dumps',
]
