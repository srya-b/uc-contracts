import gevent
from gevent.event import AsyncResult

global _dump
_dump = AsyncResult()

def dump_clear():
    global _dump
    #print('')
    _dump = AsyncResult()

import inspect

def dump():
    global _dump
    if _dump.ready(): print('\n\n\t****** DUMP ALREADY CALED ****')
    _dump.set(0)

def dump_check():
    global _dump
    return _dump.ready()


def dump_wait():
    global _dump
    gevent.wait([_dump])
    dump_clear()

def isset():
    global _dump
    return _dump.ready()
