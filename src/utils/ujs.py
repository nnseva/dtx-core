#
# -*- coding: utf-8 -*-
#

## use Ultrajson (https://github.com/esnme/ultrajson) if available
try:
   import ujson
   json_lib = ujson
   json_loads = ujson.loads
   json_dumps = lambda x: ujson.dumps(x, ensure_ascii = False)
except:
   import json
   json_lib = json
   json_loads = json.loads
   json_dumps = json.dumps

loads = json_loads
dumps = json_dumps

if __name__ == '__main__':
    import datetime
    s1 = dict(
        s1 = 'Hello',
        u1 = u'World',
        i1 = 123,
        f1 = 45.6,
        d1 = datetime.datetime.now()
    )
    print dumps(s1)
