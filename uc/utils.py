from __future__ import print_function
import inspect
import gevent 
from collections import defaultdict

global pouts
pouts = defaultdict(list)

try:
    import __builtin__
except ImportError:
    import builtins as __builtin__

def print(*args, **kwargs):
    return __builtin__.print(*args, **kwargs)

def wait_for(_2_):
    try:
        r = gevent.wait(objects=[_2_],count=1)
        r = r[0]
        _2_.reset()
        return r.read()
    except gevent.exceptions.LoopExit:
        dump.dump_wait()
        return None

def waits(*cs):
    r = gevent.wait(objects=[*cs],count=1)
    assert len(r) == 1
    r = r[0]
    r.reset()
    return r.read()

def read(ch):
    r = gevent.wait([ch])[0]
    r.reset()
    return r.read()

def read_one(*cs):
    r = gevent.wait([*cs],count=1)
    assert len(r) == 1
    r[0].reset()
    return r[0], r[0].read()

def collectOutputs(ch, l, p):
    def _f():
        while True:
            m = waits(ch)
            l.append(ch.id + ': ' + str(m))
            print('\n' + ch.id + ': ' + str(m))
            p.write('')
    gevent.spawn(_f)

def wrapwrite(wchan, outchan, f):
    _chanout = GenChannel(('write-translate-{}'.format(prefix), prefix))
    _chanin = GenChannel('read-{}'.format(prefix))

    def _translate():
        while True:
            m = wait_for(_chanout)
            #outchan.write( (prefix, m.msg), m.imp )
            outchan.write( f(m))
        gevent.spawn(_translate)
        return _chanin, _chanout
    return _chanin,_chanout
            
