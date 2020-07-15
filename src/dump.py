"""
dump.py

INTRO - TODO
"""
import gevent
from gevent.event import AsyncResult
# gevent.event.ready(): Return true if and only if the internal flag is true.

global _dump
_dump = AsyncResult()

global _channels
_channels = []

def dump_clear():
    global _dump
    #print('')
    _dump = AsyncResult()

import inspect

def dump():
    global _dump
    # Return the frame object for the caller’s stack frame.
    curframe = inspect.currentframe()
    # Get a list of frame records for a frame and all outer frames.
    calframe = inspect.getouterframes(curframe, 2)
    #print('\n\t\t*********** dumping from={} *****************'.format(calframe[1][3]))
    if _dump.ready(): print('\n\n\t****** DUMP ALREADY CALLED ****'); print('caller name:', calframe[1][3])
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

