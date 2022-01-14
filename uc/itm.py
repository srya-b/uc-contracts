import os
import sys
from uc.utils import wait_for, waits
from gevent.queue import Queue, Channel, Empty
from gevent.event import AsyncResult, Event
import gevent
import logging
import inspect

class GenChannel(Event):
    """
    A class to represent the basic channel over which everything communicates.
    Inheritds from the gevent.Event class which can be triggered and waited for.
    """
    def __init__(self, i=''):
        """
        Constructs the data and id fields.

        Args:
            i (st): string id name for this channel 
        """
        Event.__init__(self)
        self._data = None
        self.id = i

    def write(self, data):
        """
        Writes data into the channel. Throws an error if channel already is already full.

        Args:
            data: tuple 
                data stored in the channel
        """
        if not self.is_set():
            self._data = data; self.set() 
        else: 
            raise Exception("\033[1mwriting to channel already full with {}. Writing {} in {}\033[0m".format(self._data,data,self.id))

    def __str__(self):
        return "Channel id:{}".format(self.id)

    def read(self): 
        """
        Read the data in the channel.

        Returns:
            Data in the channel.
        """
        return self._data

    def reset(self):
        """
        Reset the channel so it can be written to again.
        """
        self.clear()

def wrapwrite(chan, wrapper):
    newchan = GenChannel('wrap(' + chan.id + ')')
    def _wrapwrite():
        while True:
            m = waits(newchan)
            chan.write( wrapper(m) )
    gevent.spawn(_wrapwrite)
    return newchan

def unwrapread(chans, select, unwrap):
    newchan = GenChannel()
    
    def _unwrapread():
        while True:
            m = waits(newchan)
            select(m).write( unwrap(m) )
    gevent.spawn(_unwrapread)
    return newchan
            

class ITM:
    """
    Class encapsultes the basic ITM with channels in place of the traditional tapes.
    """
    def __init__(self, k, bits, sid, pid, channels, handlers, pump):
        """
        Args:
            k (int): the security parameter
            bits (random.Random): source of randomness for the ITM
            sid (tuple): the session id of this machine
            pid (int): the process id of this ITM
            channels (dict from str to GenChannel): the channels of this ITM keyed by a string: 
                { 'p2f': GenChannel, 'f2p': GenChannel, ...}
            handlers (dict from GenChannel to function): maps a channel to the function handling 
                messages on it
            pump (GenChannel): channel to give control back to the environment
        """
        self.k = k
        self.bits = bits
        self.sid = sid
        self.pid = pid
        self.pump = pump
        self.channels = channels
        self.handlers = handlers

        self.log = logging.getLogger(type(self).__name__)

    def wrapwrite(self, msg):
        """
        Function can be overridden by a child class to modify
        the message however it likes. For example, append a an
        identifier the message.

        Args:
            msg (tuple): the message to modify

        Returns:
            tuple: the modified message
        """
        return msg

    def write(self, ch, msg):
        self.channels[ch].write(self.wrapwrite(msg))

    def read(self, ch):
        return wait_for(self.channels[ch])

    def write_and_wait_for(self, ch=None, msg=None, read=None):
        self.write(ch, msg)
        m = self.read(read)
        return m

    def write_and_expect_msg(self, ch=None, msg=None, read=None, expect=None):
        m = self.write_and_wait_for(ch, msg, read)
        assert m == expect, 'Expected: {}, Received: {}'.format(expect, m)
        return m

    def sample(self, n):
        r = ""
        for _ in range(n):
            r += str(self.bits.randint(0,1))
        return int(r)

    def run(self):
        while True:
            ready = gevent.wait(
                objects=self.handlers.keys(),
                count=1
            )
            assert len(ready) == 1
            r = ready[0]
            msg = r.read()
            r.reset()
            self.handlers[r](msg)

