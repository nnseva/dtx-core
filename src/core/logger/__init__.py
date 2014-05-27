#
# -*- coding: utf-8 -*-
#

import dummy
import twist

def log(module=None, enabled=True):
	"""
	if not enabled:
		return dummy.Logger()
	"""
	return twist.Logger(module)

test_log = log(__name__, enabled=True)
null_log = dummy.Logger()

class Foo:
	def bar(self, log):
		with log.enter(obj=self) as tm:
			tm.msg('World')
			tm.reportResult(True)

def __test__(log):
	with log.enter() as tm:
		tm.msg('Hello')
		foo = Foo()
		foo.bar(log)
		
def __test_profiler__():
    with log.enter() as rt:
        for i in xrange(0, 30):
            a = i * 2
            with log.enter('Add', parent=rt, verbose=False) as rt_add:
                for j in xrange(0, 100000):
                    b = a + i
            with log.enter('Mul', parent=rt, verbose=False) as rt_add:
                for j in xrange(0, 100000):
                    b = a * i
        
if __name__ == '__main__':
	with test_log.enter() as tm:
		__test__(test_log)
		__test__(null_log)
		__test_profiler__(test_log)