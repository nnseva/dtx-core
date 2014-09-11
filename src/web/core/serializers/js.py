#
# -*- coding: utf-8 -*-
#

from django.utils import timezone

from dtx.web.core.serializers.base import SerializerBase, registry

import datetime
from decimal import Decimal

import json

from dtx.core import logger
log = logger.log(__name__)


def normalize_datetime(x):
    if (x.tzinfo):
        # Should be timezone.get_defaulttimezone() instead of timezone.utc?
        return x.astimezone(timezone.utc).replace(tzinfo=None)
    else:
        return x
        

encoders = {}

encoders[type(datetime.date.today())] = lambda x: x.isoformat()
encoders[type(datetime.datetime.now())] = lambda x: normalize_datetime(x).isoformat() + 'Z'
encoders[type(datetime.time())] = lambda x: x.isoformat()
encoders[type(datetime.timedelta())] = lambda x: x.total_seconds()
encoders[type(Decimal())] = lambda x: float(x)


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        global encoders
        tp = type(obj)
        if (tp in encoders.keys()):
            obj = encoders[tp](obj)
        elif hasattr(obj, '__dict__'):
            obj = obj.__dict__
        else:
            obj = super(JSONEncoder, self).default(obj)
        return obj
        

dumps = lambda data: json.dumps(data, ensure_ascii=False, cls=JSONEncoder)
loads = json.loads
        
        
class Serializer(SerializerBase):

    format = 'json'
    ctname = 'application/json'

    @classmethod
    def content_type(cls, **kwargs):
        charset = kwargs.get('charset', None)
        return cls.ctname + '; charset=' + charset if (charset) else cls.ctname

    def serialize(self, data, **kwargs):
        return dumps(data)

    def deserialize(self, data, **kwargs):
        return loads(data)


registry.register(Serializer)

__all__ = [
    'loads',
    'dumps',
]


if __name__ == '__main__':
    s1 = dict(
        s1 = 'Hello',
        u1 = u'World',
        i1 = 123,
        f1 = 45.6,
        d1 = datetime.now()
    )
    print dumps(s1)
