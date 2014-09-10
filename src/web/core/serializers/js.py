#
# -*- coding: utf-8 -*-
#

from dtx.web.core.serializers.base import SerializerBase, registry

#from dtx.utils import ujs

from datetime import date, datetime
from decimal import Decimal

import json

from dtx.utils.cache import S

from dtx.core import logger
log = logger.log(__name__)


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            obj = obj.isoformat()
        elif isinstance(obj, date):
            obj = obj.isoformat()
        elif isinstance(obj, Decimal):
            obj = float(obj)
        elif isinstance(obj, S):
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

#loads = ujs.loads
#dumps = ujs.dumps

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
