import gevent
from gevent.event import AsyncResult

global _dump
_dump = AsyncResult()

def dump_clear():
    _dump = AsyncResult()

def dump():
    _dump.set(0)

def dump_wait():
    gevent.wait([_dump])
    dump_clear()

def isset():
    return _dump.ready()
