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
    newchan = GenChannel('wrap(' + str(chan.id) + ')')
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
        """ Write a message on a channel specified by the string `ch`. `ch` is looked up 
        in the ITMs channels and written to. A default `wrapwrite` function is applied to 
        the message being written. Unless overridden, it does not modify the message.

        Args:
            ch (str): the name of the channel to write to
            msg (tuple), the message to be written
        """
        self.channels[ch].write(self.wrapwrite(msg))

    def read(self, ch):
        """ Blocking function that reads from the channel names `ch`.

        Args:
            ch (str): the name of the channel to read from

        Returns:
            (tuple): the message written on the channel
        """
        return wait_for(self.channels[ch])

    def write_and_wait_for(self, ch=None, msg=None, read=None):
        """ Write to a channel `ch` and wait for an incoming message on the channel
        `read`. 

        Args:
            ch (str): the channel to write on
            msg (tuple): the message to write
            read (str): the channel to wait for a message on

        Returns:
            (tuple): the message read from `read`
        """
        self.write(ch, msg)
        m = self.read(read)
        return m

    def write_and_expect_msg(self, ch=None, msg=None, read=None, expect=None):
        """ Write on a channel, wait for an incoming message and expect it to equal
        some value. Useful for things like "expect an OK back from the ITM".

        Args:
            ch (str): the channel to write on
            msg (tuple): the message to write
            read (str): the channel to read on
            expect (tuple): the message to expect on `read`

        Throws:
            AssertionError: if the message is not what is expected.

        Returns:
            (tuple): the message to be expected
        """
        m = self.write_and_wait_for(ch, msg, read)
        assert m == expect, 'Expected: {}, Received: {}'.format(expect, m)
        return m

    def _sample(self, n):
        r = ''
        for _ in range(n):
            r += str(self.bits.randint(0,1))
        return r

    def sample(self, n):
        """ Sample some bits of randomness from the ITMs random tape.

        Args:
            n (int): number of bits to sample

        Returns:
            r (int): an n-bit random integer
        """
        return int(self._sample(n), 2)

    def run(self):
        """ The main function of an ITM. It runs forever and waits for messages on any
        of the channels for whom a handler is specified (self.handlers.keys()). Once read
        is activates the channel's handler with the message.

        And ITM is run by running `gevent.spawn(machin.run)`.
        """
        while True:
            # wait for any of the channels to return a message
            ready = gevent.wait(
                objects=self.handlers.keys(),
                count=1
            )

            # sanity check only on channel should return
            assert len(ready) == 1
            r = ready[0]
            msg = r.read()
            r.reset()
            
            # send the message to the handler for this channel
            self.handlers[r](msg)

