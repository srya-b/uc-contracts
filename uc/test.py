from itm import *
from utils import wait_for
import gevent

#ch1 = GenChannel()
#ch2 = GenChannel()
#pump = GenChannel()
#
#def foo():
#    while True:
#        r = gevent.wait([ch1])
#        m = r[0].read()
#        r[0].reset()
#        print('foo', m)
#        pump.write('')
#
#def bar():
#    while True:
#        r = gevent.wait([ch2])
#        m = r[0].read()
#        r[0].reset()
#        print('bar', m)
#        pump.write('')
#
#def run():
#    gevent.spawn(foo)
#    gevent.spawn(bar)
#
#gevent.spawn(run)
#
#ch1.write('hello')
#gevent.wait([pump])
#pump.reset()
#ch2.write('world')
#gevent.wait([pump])
#pump.reset()


ch1 = GenChannel()

ch12 = wrapwrite(ch1, 'A2P')
ch13 = wrapwrite(ch1, 'A2F')

ch12.write(('commit', 2,3))
m = wait_for(ch1)
print('a2p', m)
ch13.write(('send', 'asa'))
m = wait_for(ch1)
print('a2f', m)
