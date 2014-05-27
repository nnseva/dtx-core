from twisted.internet import reactor, threads
from twisted.internet import task
from twisted.internet.task import deferLater
from twisted.internet.defer import inlineCallbacks as IC
from twisted.internet.defer import returnValue as Return
from twisted.internet.defer import Deferred, DeferredList, maybeDeferred, execute, succeed

import datetime
import decimal
import json

import copy

from dtx.utils.snippets.sorted_collection import SortedCollection

from django.utils import timezone

def schedulePause(seconds):
    """Async sleep equivalent"""
    #reactor.callLater(seconds,lambda: d.callback(None))
    return deferLater(reactor,seconds,lambda: None)

class Cache:
    def __init__(self,get_item_defer_callable,seconds=120):
        self.get_item_defer_callable = get_item_defer_callable
        self.seconds = seconds
        self.cache = {}
        self.keys = SortedCollection([],key=lambda item:item['ts'])
        self.update_requests = {}

    @IC
    def get(self,key):
        item = None
        if key in self.cache:
            item = self.cache[key]['item']
            if self.cache[key]['ts'] < timezone.now() - datetime.timedelta(seconds=self.seconds):
                reactor.callLater(0,self.update_cache,key)
        else:
            yield self.update_cache(key)
            item = self.cache.get(key,None)
            if item:
                item = item['item']
        Return(item)

    @IC
    def update_cache(self,key):
        try:
            if not key in self.update_requests:
                self.update_requests[key] = maybeDeferred(self.get_item_defer_callable,key)
                item = None
                try:
                    item = yield self.update_requests[key]
                except Exception,ex:
                    print "ERROR IN DEFERRED UPDATING CACHE:",ex
                    import traceback
                    traceback.print_exc()
                del self.update_requests[key]
                ts = timezone.now()
                item_d = {
                    'item':item,
                    'ts':ts,
                    'key':key,
                }
                if key in self.cache:
                    self.keys.remove(self.cache[key])
                self.cache[key] = item_d
                self.keys.insert(item_d)
                while 42:
                    try:
                        old = self.keys.find_le(ts-datetime.timedelta(seconds=self.seconds*2))
                        del self.cache[old['key']]
                        self.keys.remove(old)
                    except ValueError,ex:
                        break
            else:
                d = Deferred()
                yield self.update_requests[key].chainDeferred(d)
        except Exception,ex:
            print "ERROR WHILE UPDATING CACHE:",ex

def clear_object_cache(o):
    for n in dir(o):
        if n[0] == '_' and n[-6:] == '_cache' and len(n) > 7:
            delattr(o,n)

class S_Encoder(json.JSONEncoder):
    def default(self,o):
        if isinstance(o,S):
            return o.__dict__
        if isinstance(o,datetime.timedelta):
            return {'@t':'td','d':o.days,'s':o.seconds,'ms':o.microseconds}
        if isinstance(o,datetime.datetime):
            # fixes absent timezone by default timezone (MSK)
            return {'@t':'dt','d':o.date(),'t':o.time(),'tz':o.tzinfo.zone if o.tzinfo else timezone.get_default_timezone()}
        if isinstance(o,datetime.date):
            return {'@t':'d','y':o.year,'m':o.month,'d':o.day}
        if isinstance(o,datetime.time):
            if o.tzinfo:
                return {'@t':'t','h':o.hour,'m':o.minute,'s':o.second,'ms':o.microsecond,'tz':o.tzinfo.zone}
            # doesn't fix absent timezone because of already fixed of it in datetime processing
            return {'@t':'t','h':o.hour,'m':o.minute,'s':o.second,'ms':o.microsecond}
        if isinstance(o,decimal.Decimal):
            return float(o)
        return json.JSONEncoder.default(self, o)

class S_Decoder(json.JSONDecoder):
    def decode_t(self,dct):
        # doesn't fix absent timezone because of already fixed of it in datetime processing
        return datetime.time(dct['h'],dct['m'],dct['s'],dct['ms'],tzinfo=timezone.pytz.timezone(dct['tz']) if 'tz' in dct and dct['tz'] else None)
    def decode_d(self,dct):
        return datetime.date(dct['y'],dct['m'],dct['d'])
    def decode_td(self,dct):
        return datetime.timedelta(dct['d'],dct['s'],dct['ms'])
    def decode_dt(self,dct):
        r = datetime.datetime.combine(dct['d'],dct['t'])
        if 'tz' in dct and dct['tz'] and not r.tzinfo:
            return timezone.make_aware(r,timezone.pytz.timezone(dct['tz']))
        # fixes absent timezone by default timezone (MSK)
        return timezone.make_aware(r,timezone.get_default_timezone())
    def object_hook(self,dct):
        if '@t' in dct:
            m = getattr(self,'decode_'+dct['@t'])
            return m(dct)
        #ddct = dict([ (str(k),dct[k]) for k in dct ])
        #return S(**ddct)
        return S(**dct)
    def __init__(self):
        json.JSONDecoder.__init__(self,object_hook=self.object_hook)

    def iterate_buffer(self,buffer):
        p = 0
        while p < len(buffer):
            m,p = self.scan_once(buffer,p)
            yield m

    def iterate_buffer_restore(self,buffer):
        p = 0
        while p < len(buffer):
            try:
                m,p = self.scan_once(buffer,p)
                yield m
            except:
                p += 1
                pass

    def list_from_buffer(self,buffer):
        return [m for m in self.iterate_buffer(buffer)]

class S:
    def __init__(self,**kw):
        self.__dict__.update(kw)

    @staticmethod
    def _to_simple(v):
        if isinstance(v,S):
            v = S._to_simple(v.__dict__)
        elif isinstance(v,datetime.timedelta):
            v = v.total_seconds()
        elif isinstance(v,datetime.datetime):
            if timezone.is_naive(v):
                v = timezone.make_aware(v,timezone.get_current_timezone())
            v = v.isoformat()
        elif isinstance(v,datetime.date):
            v = v.isoformat()
        elif isinstance(v,datetime.time):
            v = v.isoformat()
        elif isinstance(v,decimal.Decimal):
            v = float(v)
        elif hasattr(v,'keys') and (hasattr(v,'__getitem__') or hasattr(v,'__item__')):
            v = dict([(k,S._to_simple(v[k])) for k in v.keys()])
        elif isinstance(v,(str,unicode)):
            v = v
        elif hasattr(v,'__getitem__'):
            v = [S._to_simple(vv) for vv in v]
        return v

    def to_simple(self):
        return self._to_simple(self)

    @classmethod
    def list_from_cursor(cls,cursor):
        return [cls(**dict(zip([col[0] for col in cursor.description],row))) for row in cursor.fetchall()]

    @classmethod
    def iterate_from_cursor(cls,cursor):
        while 42:
            block = cursor.fetchmany(100)
            for row in block:
                yield cls(**dict(zip([col[0] for col in cursor.description],row)))
            if not block:
                break

    @classmethod
    def from_cursor(cls,cursor):
        row = cursor.fetchone()
        if row:
            return cls(**dict(zip([col[0] for col in cursor.description],row)))

    @classmethod
    def iterate_json_buffer(cls,buffer,decoder=S_Decoder()):
        for s in decoder.iterate_buffer(buffer):
            yield s

    @classmethod
    def iterate_json_buffer_restore(cls,buffer,decoder=S_Decoder()):
        for s in decoder.iterate_buffer_restore(buffer):
            yield s

    @classmethod
    def list_from_buffer(cls,buffer,decoder=S_Decoder()):
        return decoder.list_from_buffer(buffer)

    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return str(self)

    def __getitem__(self,ind):
        return getattr(self,str(ind))

    def __eq__(self,other):
        return (self.__dict__ == other.__dict__) if hasattr(other,'__dict__') else False

    def has_key(self,k):
        return str(k) in self.__dict__.keys()

    def keys(self):
        return [str(k) for k in self.__dict__.keys()]

def _dict_deep_join(dct,other,ignore_none,ops):
    for name in other.keys():
        if not name in dct.keys():
            dct[name] = copy.deepcopy(other[name])
        else:
            dct[name] = _deep_join(dct[name],other[name],ignore_none,ops)
    return dct

def _list_deep_join(lst,other,ignore_none,ops):
    for i in xrange(min(len(lst),len(other))):
        #print "DEBUG:",i,lst[i],other[i]
        lst[i] = _deep_join(lst[i],other[i],ignore_none,ops)
    #print "DEBUG2:",i
    for i in xrange(i+1,len(other)):
        #print "DEBUG3:",i,other[i]
        lst.append(copy.deepcopy(other[i]))
    return lst

def deep_join(dst,other,ignore_none=True,ops={}):
    return _deep_join(copy.deepcopy(dst),other,ignore_none,ops)

def _deep_join(dst,other,ignore_none,ops):
    if ignore_none and other == None:
        return dst
    dst_dir = set(dir(dst))
    other_dir = set(dir(other))
    if 'keys' in other_dir and 'keys' in dst_dir and '__setitem__' in dst_dir:
        return _dict_deep_join(dst,other,ignore_none,ops)
    if '__getitem__' in other_dir and '__len__' in other_dir and not 'isalnum' in other_dir:
        if '__setitem__' in dst_dir and 'append' in dst_dir:
            return _list_deep_join(dst,other,ignore_none,ops)
    for t in ops:
        if isinstance(other,t) and isinstance(dst,t):
            op = ops[t]
            return op(dst,other)
    return copy.deepcopy(other)

def deep_get(dst,key):
    if not key:
        return
    if not isinstance(key,(tuple,list)):
        key = key.split('.')
    v = None
    try:
        v = dst[key[0]]
    except:
        pass
    if not v and key[0].isdigit():
        try:
            v = dst[long(key[0])]
        except:
            pass
    if len(key) == 1:
        return v
    return deep_get(v,key[1:])

def _dict_deep_comp(dct,other):
    for name in dct.keys():
        if not name in other.keys():
            return False
        if not deep_comp(dct[name],other[name]):
            return False
    return True

def _list_deep_comp(lst,other):
    if len(lst) > len(other):
        return False
    for i in xrange(len(lst)):
        if not deep_comp(lst[i],other[i]):
            return False
    return True

def deep_comp(dst,other):
    dst_dir = set(dir(dst))
    other_dir = set(dir(other))
    if 'keys' in other_dir and 'keys' in dst_dir:
        return _dict_deep_comp(dst,other)
    if ('__getitem__' in other_dir and '__len__' in other_dir and not 'isalnum' in other_dir and
        '__getitem__' in dst_dir and   '__len__' in dst_dir and   not 'isalnum' in dst_dir):
        return _list_deep_comp(dst,other)
    return dst == other

def safe_dt(dt):
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt,timezone.get_default_timezone())
    else:
        dt = timezone.localtime(dt,timezone.utc)
    return dt

def safe_str(s):
    if isinstance(s,unicode):
        return s.encode('utf-8','replace')
    if isinstance(s,str):
        return s
    try:
        s = unicode(s)
        return s.encode('utf-8','replace')
    except:
        pass
    try:
        s = str(s)
        return s
    except:
        pass
    return "<CAN'T DECODE>"

def run():
    @IC
    def get_item_test(key):
        ts = timezone.now()
        print "Getting:",key,ts
        yield schedulePause(3)
        print "Got:",key,ts
        Return((key,ts))

    c = Cache(get_item_test,20)
    k = 0

    @IC
    def tests():
        k = timezone.now().minute
        n = timezone.now()
        print "Checking:",k,n
        r = yield c.get(k)
        print "Checked:",k,r,n,timezone.now()

    def test():
        reactor.callLater(0,tests)
        reactor.callLater(0,tests)
        reactor.callLater(0,tests)
        reactor.callLater(0,tests)
        reactor.callLater(0,tests)
        reactor.callLater(0,tests)
        reactor.callLater(0,tests)
        reactor.callLater(0,tests)
        reactor.callLater(1,test)
        print "Cache:",c.cache
        print "Cache keys:",c.keys

    reactor.callLater(0,test)

    reactor.run()

if __name__ == "__main__":
    run()


'''
from tastypie.cache import SimpleCache

class ApiCache(SimpleCache):
  def __init__(self,timeout=60):
    super(ApiCache,self).__init__()
    self.timeout = timeout

  def set(self, key, value, timeout=None):
    if timeout == None:
      timeout = self.timeout
    return super(ApiCache,self).set(key,value,timeout)
'''
