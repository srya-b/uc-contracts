import os
import sys
from uc.utils import wait_for, waits
from gevent.queue import Queue, Channel, Empty
from gevent.event import AsyncResult, Event
from uc.errors import WriteImportError, TickError
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
            raise Exception("\033[1mwriting to channel already full with {}. Writing {} in {}\033[0m".format(self._data,data,self.i))

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

    def read(self, ch=None):
        return wait_for(self.channels[ch])

    def write_and_wait_for(self, ch=None, msg=None, read=None):
        self.write(ch, msg)
        m = self.read(read)
        return m

    def write_and_wait_expect(self, ch=None, msg=None, read=None, expect=None):
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


class UCProtocol(ITM):
    def __init__(self, k, bits, sid, pid, channels, pump):
        self.handlers = {
            channels['z2p'] : self.env_msg,
            channels['f2p'] : self.func_msg,
            channels['a2p'] : self.adv_msg,
        }
        ITM.__init__(self, k, bits, sid, pid, channels, self.handlers, pump)
        self.f = lambda x: x[0]
        self.parse = lambda x: x[1:]
        self.env_msgs = {}
        self.adv_msgs = {}
        self.func_msgs = {}

    def adv_msg(self, msg):
        Exception("adv_msg needs to be defined")

    def func_msg(self, msg):
        if self.f(msg) in self.func_msgs:
            self.func_msgs[self.f(msg)](*(self.parse(msg)))
        else:
            self.pump.write('')

    def env_msg(self, msg):
        if msg[0] in self.env_msgs:
            self.env_msgs[msg[0]](*msg[1:])
        else:
            self.pump.write('')

class UCFunctionality(ITM):
    def __init__(self, k, bits, crupt, sid, pid, channels, pump):
        self.crupt = crupt
        self.handlers = {
            channels['p2f'] : self.party_msg,
            channels['a2f'] : self.adv_msg,
            channels['z2f'] : self.env_msg
        }
        
        ITM.__init__(self, k, bits, sid, pid, channels, self.handlers, pump)

        self.party_msgs = {}
        self.adv_msgs = {}

    def is_honest(self, sid, pid):
        return (sid,pid) not in self.crupt

    def is_dishonest(self, sid, pid):
        return not self.is_honest(sid, pid)

    def wrapwrite(self, msg):
        return (self.sid, msg)

    def adv_msg(self, msg):
        if msg[0] in self.adv_msgs:
            self.adv_msgs[msg[0]](*msg[1:])
        else:
            self.pump.write('')

    def party_msg(self, m):
        sender,msg = m
        if msg[0] in self.party_msgs:
            self.party_msgs[msg[0]](sender, *msg[1:])
        else:
            raise Exception('unknown message', msg)
            self.pump.write('')

    def env_msg(self, msg):
        Exception("env_msg needs to be defined")

class UCAdversary(ITM):
    def __init__(self, k, bits, crupt, sid, pid, channels, pump):
        self.crupt = crupt
        self.handlers = {
            channels['p2a'] : self.party_msg,
            channels['f2a'] : self.func_msg,
            channels['z2a'] : self.env_msg
        }
        ITM.__init__(self, k, bits, sid, pid, channels, self.handlers, pump)
        self.env_msgs = {}
        self.func_msgs = {}
        self.party_msgs = {}
        
        self.a2f_msgs = {}
        self.a2p_msgs = {}

        self.f = lambda x: x[0]
        self.fparse = lambda x: x[1:]

    def is_dishonest(self, sid, pid):
        return (sid,pid) in self.crupt

    def party_msg(self, d):
        sender, msg = d
        if msg[0] in self.party_msgs:
            self.party_msgs[msg[0]](sender, *msg[1:])
        else:
            self.pump.write('')

    def func_msg(self, msg):
        if self.f(msg[0]) in self.func_msgs:
            self.func_msgs[self.f(msg[0])](*self.fparse(msg))
        else:
            self.pump.write('')

    def env_msg(self, m):
        t,msg = m
        if t is 'A2F' and msg[0] in self.a2f_msgs:
            self.a2f_msgs[msg[0]](*msg[1:])
        elif t is 'A2P' and msg[1][0] in self.a2p_msgs:
            self.a2p_msgs[msg[1][0]](msg[0], msg[1][1:])
        elif t in self.env_msgs:
            self.env_msgs[t](msg)
        else:
            raise Exception('Message {} not handled by adversary'.format(msg))
            self.pump.write('')

class DummyParty(ITM):
    def __init__(self, k, bits, sid, pid, channels, pump):
        self.handlers = {
            channels['z2p'] : self.env_msg,
            channels['a2p'] : self.adv_msg,
            channels['f2p'] : self.func_msg
        }
        ITM.__init__(self, k, bits, sid, pid, channels, self.handlers, pump)

    def adv_msg(self, msg):
        self.write('p2f', msg)
        raise Exception('Adv cant write to an honest party')

    def env_msg(self, msg):
        self.write('p2f', msg)

    def func_msg(self, msg):
        self.write('p2z', msg)

def protocolWrapper(prot):
    def f(k, bits, crupt, sid, channels, pump):
        return ProtocolWrapper(k, bits, crupt, sid, channels, pump, prot)
    return f

from collections import defaultdict
class ProtocolWrapper(ITM):
    def __init__(self, k, bits, crupt, sid, channels, pump, prot):
        self.crupt = crupt
        self.z2pid = {}
        self.f2pid = {}
        self.a2pid = {}
        self.p2pid = {}
        self.prot = prot
        self.log = logging.getLogger('ProtocolWrapper')
        self.handlers = {
            channels['z2p'] : self.env_msg,
            channels['a2p'] : self.adv_msg,
            channels['f2p'] : self.func_msg,
        }
        ITM.__init__(self, k, bits, sid, None, channels, self.handlers, pump)

    def is_dishonest(self, sid, pid):
        return (sid,pid) in self.crupt

    def is_honest(self, sid, pid):
        return not self.is_dishonest(sid,pid)

    def _newPID(self, sid, pid, _2pid, p2_, tag):
        pp2_ = GenChannel(('write-translate-{}'.format(tag),sid,pid)) 
        _2pp = GenChannel(('read-{}'.format(tag),sid,pid)) 

        def _translate():
           while True:
                r = gevent.wait(objects=[pp2_],count=1)
                msg = r[0].read()
                pp2_.reset()
                p2_.write( ((sid,pid), msg))
        gevent.spawn(_translate)

        _2pid[sid,pid] = _2pp
        return (_2pp, pp2_) 

    def newPID(self, sid, pid):
        print('\033[1m[{}]\033[0m Creating new party with pid: {}'.format('PWrapper', pid))
        _z2p,_p2z = self._newPID(sid, pid, self.z2pid, self.channels['p2z'], 'p2z')
        _f2p,_p2f = self._newPID(sid, pid, self.f2pid, self.channels['p2f'], 'p2f')
        _a2p,_p2a = self._newPID(sid, pid, self.a2pid, self.channels['p2a'], 'p2a')
        
        p = self.prot(self.k, self.bits, self.sid, pid, {'a2p':_a2p,'p2a':_p2a, 'z2p':_z2p,'p2z':_p2z, 'f2p':_f2p, 'p2f':_p2f}, self.pump)
        gevent.spawn(p.run)

    def getPID(self, _2pid, sid, pid):
        if (sid,pid) in _2pid: return _2pid[sid,pid]
        else:
            self.newPID(sid,pid)
            return _2pid[sid,pid]

    def env_msg(self, msg):
        ((sid,pid), msg) = msg
        if self.is_dishonest(sid,pid): raise Exception("Environment writing to corrupt party")
        _pid = self.getPID(self.z2pid,sid,pid)
        _pid.write(msg)
    
    def func_msg(self, msg):
        fromsid,((tosid,topid),msg) = msg
        if self.is_dishonest(tosid,topid):
            self.write('p2a', ((tosid,topid), msg))
        else:
            _pid = self.getPID(self.f2pid, tosid, topid)
            _pid.write( msg)

    def adv_msg(self, msg):
        (sid,pid), msg = msg
        if self.is_honest(sid,pid): raise Exception("adv writing to an honest party: {}. Cruptset: {}".format((sid,pid), self.crupt))
        self.write( 'p2f', ((sid,pid), msg))
