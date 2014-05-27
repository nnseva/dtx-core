
from dtx.core import logger
log = logger.log(__name__, enabled=True)

def time(*args, **kwargs):
    raise Exception(u'{}.time() is deprecated'.format(__name__))

def coiterate(iterator, name=u'***', parent=None, verbose=True, verbose_details=True):
    if (isinstance(iterator, (dict))):
        with log.enter(name=name, parent=parent, verbose=verbose) as rt:
            for k in iterator.keys():
                for ss in coiterate(iterator[k], k, rt if not parent else parent, verbose_details):
                    yield ss            
    else:
        with log.enter(name=name, parent=parent, verbose=verbose) as rt:
            for ss in iterator:
                yield ss

print u'Module {} is deprecated'.format(__name__)
        
def test():
    with log.enter() as rt:
        for i in xrange(0, 100):
            a = i * 2
            with log.enter('Add', parent=rt, verbose=False) as rt_add:
                for j in xrange(0, 100000):
                    b = a + i
            with log.enter('Mul', parent=rt, verbose=False) as rt_add:
                for j in xrange(0, 100000):
                    b = a * i

if __name__ == '__main__':
    test()