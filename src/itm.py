import os
import sys
from utils import gwrite, z_write, wait_for, MessageTag
from gevent.queue import Queue, Channel, Empty
from gevent.event import AsyncResult, Event
from numpy.polynomial.polynomial import Polynomial
import dump
import gevent
import comm
import logging
from collections import defaultdict

'''
There are 2 options with channels:
    1. The channels are greenlets themselves where they wait for
        the AsyncResult to be set and then write the result to the
        input of the 'to' itm. However, the channel itself needs
        to be the input to the itm, otherwise there's just an extra
        layer that ads another call to it.
    2. Calling 'write' on the channel writes to the input tape of the
        'to' itm. This allows the same interface for the party that's
        writing, but the recipient can be someone different. If the
        simulator want to run a sandbox of the adversary, then the 
        desired construction is that all channels connect to the 
        simulator and the simulator can control the output messages
        to the actual intended recipient.

Design Decision:
    * Instead 'to' and 'fro' will be just identifiers of the form
        (sid,pid). Having 'to' be the AsyncResult itself means the 
        code will still be at the mercy of having to spawn itms
        in a specific order based on the protocol at hand. Which
        really blows.
    * Can't be ^ (above) either. If 'to' is the identifier and the
        itm is got from 'comm' then you're screwed because you have 
        to fake an identifier and register is in 'comm' for the 
        simulator to be able to sandbox run the adversary and
        intercept outputs.
    * Actually, shit the channel has to be the AsyncResult itself
        that's the only way. That's the way it was the first time
        idk how I convinced myself to change it. rip
'''
class MSG:
    def __init__(self, msg, imp=1):
        self.msg = msg
        self.imp = imp
    def __repr__(self):
        return 'MSG:' + str((self.msg,self.imp))

class GenChannel(Event):
    def __init__(self, i=-1):
        Event.__init__(self)
        self._data = None
        self.i = i

    def write(self, data, imp=0):
        if not self.is_set():
            self._data = MSG(data, imp); self.set()
            #print('\033[91m WRITE id={}, msg={}, imp={}\033[0m'.format(self.i, self._data, imp))
        else: 
            raise Exception("\033[1mwriting to channel already full with {}. Writing {} in {}\033[0m".format(self._data,data,self.i))
            dump.dump()

    def read(self): 
        #print('\033[91m READ id={}, msg={}\033[0m'.format(self.i, self._data))
        return self._data
    def reset(self, s=''): 
        self.clear()

class ITM:
    def __init__(self, sid, pid, channels, handlers, poly):
        self.sid = sid
        self.pid = pid
        self.poly = poly
        self.channels = channels
        self.handlers = handlers

        self.imp_in = 0
        self.imp_out = 0
        self.spent = 0
        self.marked = 0
        self.log = logging.getLogger(type(self).__name__)

    def write(self, ch, msg, imp=0):
        #self.tick(1)    # each write consumes a tick
        #print('\033[93m[ITM WRITE] pid={}] msg={}, imp={}, \n\timp_in={}, \n\timp_out={}\033[0m\n'.format(self.pid, msg, imp, self.imp_in, self.imp_out))
        #print('\033[93m[ITM WRITE] pid={}] msg={}, imp={}\033[0m\n'.format(self.pid, msg, imp))
        if self.imp_in - self.imp_out + self.marked >= imp:
            self.imp_out += imp
            self.channels[ch].write(msg, imp)
            self.log.debug("[{}] import remaining: {}".format(self.pid, self.imp_in - self.imp_out))
        else:
            raise Exception("out of import")

    def tick(self, n):
        if self.poly(self.marked) < self.spent + n:
            self.log.critical("Out of potential, generating more")
            self.generate_pot(1)
        self.spent += 1

    def generate_pot(self, n):
        if self.imp_in - self.imp_out - self.marked >= n:
            self.marked += n
        else:
            raise Exception("Can't mark any more tokens, you're out!")

    def run(self):
        while True:
            ready = gevent.wait(
                objects=self.handlers.keys(),
                count=1
            )
            assert len(ready) == 1
            r = ready[0]
            d = r.read()
            msg = d.msg
            imp = d.imp
            self.imp_in += imp
            #print('\033[92m[ITM READ] sid={}, pid={}] msg={}, imp={} \n\timp_in={}, \n\timp_out={}\033[0m\n'.format(self.sid, self.pid, msg, imp, self.imp_in, self.imp_out))
            #print('\033[92m[ITM READ] sid={}, pid={}] msg={}, imp={}\033[0m\n'.format(self.sid, self.pid, msg, imp))
            r.reset()
            #self.handlers[r](msg)
            #print("Calling: ", self.sid, self.__class__, self.handlers[r].__name__)
            self.handlers[r](d)

class UCProtocol(ITM):
    def __init__(self, sid, pid, channels, poly):
        self.sid = sid
        self.pid = pid
        self.p2a = channels['p2a']; self.a2p = channels['a2p']
        self.p2f = channels['p2f']; self.f2p = channels['f2p']
        self.p2z = channels['p2z']; self.z2p = channels['z2p']
        self.handlers = {
            self.z2p : self.env_msg,
            self.f2p : self.func_msg,
            self.a2p : self.adv_msg,
        }
        ITM.__init__(self, sid, pid, channels, self.handlers, poly)

    def adv_msg(self, msg):
        Exception("adv_msg needs to be defined")

    def func_msg(self, msg):
        Exception("func_msg needs to be defined")

    def env_msg(self, msg):
        Exception("env_msg needs to be defined")

class UCFunctionality(ITM):
    def __init__(self, sid, pid, channels, poly):
        self.f2a = channels['f2a']; self.a2f = channels['a2f']
        self.f2z = channels['f2z']; self.z2f = channels['z2f']
        self.f2p = channels['f2p']; self.p2f = channels['p2f']
        #print('UCFunctionality channels', channels)
        #print('UCFunctionality handlers', handlers)
        self.handlers = {
            self.p2f : self.party_msg,
            self.a2f : self.adv_msg,
        }
        ITM.__init__(self, sid, pid, channels, self.handlers, poly)

    def adv_msg(self, msg):
        Exception("adv_msg needs to be defined")

    def party_msg(self, msg):
        Exception("func_msg needs to be defined")

    def env_msg(self, msg):
        Exception("env_msg needs to be defined")

class UCWrappedFunctionality(ITM):
    def __init__(self, sid, pid, channels, poly):
        self.f2a = channels['f2a']; self.a2f = channels['a2f']
        self.f2z = channels['f2z']; self.z2f = channels['z2f']
        self.f2p = channels['f2p']; self.p2f = channels['p2f']
        self.f2w = channels['f2w']; self.w2f = channels['w2f']
        self.handlers = {
            self.z2f : self.env_msg,
            self.p2f : self.party_msg,
            self.a2f : self.adv_msg,
            self.w2f : self.wrapper_msg,
        }
        ITM.__init__(self, sid, pid, channels, self.handlers, poly)

    def adv_msg(self, msg):
        Exception("adv_msg needs to be defined")

    def party_msg(self, msg):
        Exception("party_msg needs to be defined")

    def env_msg(self, msg):
        Exception("env_msg needs to be defined")

    def wrapper_msg(self, msg):
        Exception("wrapper_msg needs to be defined")

    def leak(self, msg, imp):
        #self.channels['f2w'].write( ('leak', msg), imp)
        self.write('f2w', ('leak',msg), imp)

class UCWrappedProtocol(ITM):
    def __init__(self, sid, pid, channels, poly):
        self.p2a = channels['p2a']; self.a2p = channels['a2p']
        self.p2z = channels['p2z']; self.z2p = channels['z2p']
        self.p2f = channels['p2f']; self.f2p = channels['f2p']
        self.p2w = channels['p2w']; self.w2p = channels['w2p']
        self.handlers = {
            self.z2p : self.env_msg,
            self.f2p : self.func_msg,
            self.a2p : self.adv_msg,
            self.w2p : self.wrapper_msg,
        }
        ITM.__init__(self, sid, pid, channels, self.handlers, poly)

    def adv_msg(self, msg):
        Exception("adv_msg needs to be defined")

    def func_msg(self, msg):
        Exception("func_msg needs to be defined")

    def env_msg(self, msg):
        Exception("env_msg needs to be defined")

    def wrapper_msg(self, msg):
        Exception("wrapper_msg needs to be defined")

    def leak(self, msg):
        Exception("leak needs to be defined")

class UCWrapper(ITM):
    def __init__(self, sid, pid, channels, poly):
        self.w2a = channels['w2a']; self.a2w = channels['a2w']
        self.w2z = channels['w2z']; self.z2w = channels['z2w']
        self.w2f = channels['w2f']; self.f2w = channels['f2w']
        self.w2p = channels['w2p']; self.p2w = channels['p2w']
        self.handlers = {
            self.z2w : self.env_msg,
            self.f2w : self.func_msg,
            self.a2w : self.adv_msg,
            self.p2w : self.party_msg,
        }
        ITM.__init__(self, sid, pid, channels, self.handlers, poly)

    def adv_msg(self, msg):
        Exception("adv_msg needs to be defined")

    def func_msg(self, msg):
        Exception("func_msg needs to be defined")

    def env_msg(self, msg):
        Exception("env_msg needs to be defined")

    def party_msg(self, msg):
        Exception("party_msg needs to be defined")

    def leak(self, msg):
        Exception("leak needs to be defined")

class UCAsyncWrappedFunctionality(UCWrappedFunctionality):
        
    def __init__(self, sid, pid, channels, poly):
        UCWrappedFunctionality.__init__(self, sid, pid, channels, poly)
        
    def wrapper_msg(self, d):
        msg = d.msg
        imp = d.imp
        if msg[0] == MessageTag.EXECUTE:
            func, args = msg[1]
            func(*args)
        
    def leak(self, msg):
        self.write('f2w', (MessageTag.LEAK, msg) )
        return wait_for(self.w2f)
        
    def eventually(self, func, args, leak_msg = None):
        self.write('f2w', (MessageTag.EVENTUALLY, (func, args), leak_msg) )
        return wait_for(self.w2f)
        
class UCAsyncWrappedProtocol(UCWrappedProtocol):
    def __init__(self, sid, pid, channels, poly):
        UCWrappedProtocol.__init__(self, sid, pid, channels, poly)
        
    def leak(self, msg):
        dump.dump() # should not generally happen
        
    def eventually(self, msg):
        dump.dump() # should not generally happen
        
class ITMFunctionality(object):
    #def __init__(self, sid, pid, a2f, f2a, z2f, f2z, p2f, f2p, _2f, f2_):
    def __init__(self, sid, pid, channels, handlers):
        self.sid = sid; self.pid = pid
        self.sender = (sid,pid)
        self.channels = channels
        self.handlers = handlers

       
    def __str__(self):
        return str(self.F)

    def init(self, functionality):
        self.F = functionality
        self.outputs = self.F.outputs
    def run(self):
        while True:
            ready = gevent.wait(
                objects=self.channels,
                count=1
            )
            assert len(ready) == 1
            r = ready[0]
            msg = r.read()
            r.reset()
            self.handlers[r](msg)

class ITMPassthrough(object):
    def __init__(self, sid, pid, a2p, p2a, z2p, p2z, f2p, p2f):
        self.sid = sid
        self.pid = pid
        self.sender = (sid,pid)

        self.z2p = z2p; self.p2z = p2z
        self.f2p = f2p; self.p2f = p2f###
        self.a2p = a2p; self.p2a = p2a
        #self.a2p = a2p; self.p2f = p2f; self.z2p = z2p 
        #self.p2c = None; self.clock = None

        self.input = AsyncResult()
        self.subroutine = AsyncResult()
        self.backdoor = AsyncResult()
        self.outputidx = 0
       
    def __str__(self):
        return '\033[1mITM(%s, %s)\033[0m' % (self.sid, self.pid)

    def write(self, to, msg):
        gwrite(u'1m', 'ITM(%s, %s)'%(self.sid,self.pid), to, msg)

    def init(self, functionality):
        self.F = functionality
        self.outputs = self.F.outputs

    def set_clock(self, p2c, clock):
        self.p2c = p2c; self.clock = clock

    def clock_update(self):
        self.p2c.write(('clock-update',))

    def clock_register(self):
        self.p2c.write(('register',))

    def clock_read(self):
        return self.clock.subroutine_msg( self.sender, ('clock-read',))

    def subroutine_call(self, inp):
        sender,reveal,msg = inp
        if msg[0] == 'read':
            return self.subroutine_read()
        else:
            return self.F.subroutine_call((
                (self.sid, self.pid),
                True,
                msg
            ))
   
    def ping(self):
        o = self.F.subroutine_call((
            (self.sid, self.pid),
            True,
            ('read',)
        ))
        if o:
            z_write((self.sid,self.pid), o)
        dump.dump()

    def subroutine_read(self):
        outputs = self.F.subroutine_call( (self.sender, True, ('read',)))
        for o in outputs[self.outputidx:]:
            z_write( (self.sid,self.pid), o )
        self.outputidx = len(outputs)
    
    def input_write(self, p2_, msg):
        p2_.write( msg )

    def run(self):
        while True:
            ready = gevent.wait(
                #objects=[self.a2p, self.z2p],
                objects=[self.z2p, self.a2p, self.f2p],
                count=1
            )
            assert len(ready) == 1
            r = ready[0]
            msg = r.read().msg
            if r == self.z2p:
                if comm.isdishonest(self.sid, self.pid):
                    self.z2p.reset()
                    assert False
                #print('PASSTHROUGH MESSAGE', msg) 
                if msg[0] == 'ping':
                    self.ping()
                elif msg[0] == 'write':
                    self.input_write(msg[1], msg[2])
                elif msg[0] == 'clock-update':
                    self.clock_update()
                elif msg[0] == 'register':
                    self.clock_register()
                else:
                    self.p2f.write( msg )
                self.z2p.reset('z2p in itm')
            elif r == self.a2p:
                self.a2p.reset()
                if comm.ishonest(self.sid, self.pid):
                    assert False
                #print('\n\t alright then', msg)
                self.p2f.write( msg )
                #self.p2f.write( msg )
                #dump.dump()
            elif r == self.f2p:
                self.f2p.reset()
                if comm.ishonest(self.sid,self.pid):
                    self.p2z.write( msg )
                else:
                    self.p2a.write( msg )
            else:
                print('else dumping somewhere ive never been'); dump.dump()

class ITMSyncCruptProtocol(object):
    def __init__(self, sid, pid, a2p, p2a, z2p, p2z, f2p, p2f):
        self.sid = sid
        self.pid = pid
        self.sender = (sid,pid)

        self.z2p = z2p; self.p2z = p2z
        self.f2p = f2p; self.p2f = p2f###
        self.a2p = a2p; self.p2a = p2a

        self.input = AsyncResult()
        self.subroutine = AsyncResult()
        self.backdoor = AsyncResult()
        self.outputidx = 0
        self.roundok = False

        print('[{}] Sending start synchronization...'.format(self.pid))
        self.p2f.write( ((self.sid,'F_clock'), ('RoundOK',)) )
        self.roundok = True
       
    def __str__(self):
        return '\033[1mITM(%s, %s)\033[0m' % (self.sid, self.pid)

    def write(self, to, msg):
        gwrite(u'1m', 'ITM(%s, %s)'%(self.sid,self.pid), to, msg)

    def init(self, functionality):
        self.F = functionality
        self.outputs = self.F.outputs

    def subroutine_call(self, inp):
        sender,reveal,msg = inp
        if msg[0] == 'read':
            return self.subroutine_read()
        else:
            return self.F.subroutine_call((
                (self.sid, self.pid),
                True,
                msg
            ))
   
    def ping(self):
        o = self.F.subroutine_call((
            (self.sid, self.pid),
            True,
            ('read',)
        ))
        if o:
            z_write((self.sid,self.pid), o)
        dump.dump()

    def subroutine_read(self):
        outputs = self.F.subroutine_call( (self.sender, True, ('read',)))
        for o in outputs[self.outputidx:]:
            z_write( (self.sid,self.pid), o )
        self.outputidx = len(outputs)
    
    def input_write(self, p2_, msg):
        p2_.write( msg )

    def wait_for(self, chan):
        r = gevent.wait(objects=[chan],count=1)
        r = r[0]
        fro,msg = r.read()
        chan.reset()
        return fro,msg

    def adv_msg(self, msg):
        if msg[0] == 'send':
            self.adv_send(msg[1], msg[2])
        else:
            self.p2f.write(msg)

    def run(self):
        while True:
            ready = gevent.wait(
                #objects=[self.a2p, self.z2p],
                objects=[self.z2p, self.a2p, self.f2p],
                count=1
            )
            assert len(ready) == 1
            r = ready[0]

#            if self.roundok:
#                self.p2f.write( ((self.sid,'F_clock'), ('RequestRound',)) )
#                fro,di = self.wait_for(self.f2p)
#                if di == 1: raise Exception('Start synchronization not complete')
#                self.roundok = False
#
            msg = r.read()
            if r == self.z2p:
                assert False
            elif r == self.a2p:
                self.a2p.reset()
                if comm.ishonest(self.sid, self.pid):
                    assert False
                self.adv_msg(msg)
            elif r == self.f2p:
                self.f2p.reset()
                if comm.ishonest(self.sid,self.pid):
                    self.p2z.write( msg )
                else:
                    self.p2a.write( msg )
            else:
                print('else dumping somewhere ive never been'); dump.dump()

class ITMWrappedPassthrough(ITM):
    def __init__(self, sid, pid, a2p, p2a, z2p, p2z, f2p, p2f, w2p, p2w, pump, poly):
        self.sid = sid
        self.pid = pid
        self.sender = (sid,pid)
        self.pump = pump

        self.z2p = z2p; self.p2z = p2z
        self.f2p = f2p; self.p2f = p2f###
        self.a2p = a2p; self.p2a = p2a
        self.w2p = w2p; self.p2w = p2w

        channels = {'z2p':z2p, 'p2z':p2z, 'a2p':a2p,'p2a':p2a, 'f2p':f2p,'p2f':p2f, 'w2p':w2p, 'p2w':p2w}

        handlers = {
            z2p: self.env_msg,
            f2p: self.func_msg,
            a2p: self.adv_msg,
            w2p: self.wrapper_msg
        }

        ITM.__init__(self, sid, pid, channels, handlers, poly)

    def __str__(self):
        return '\033[1mITM(%s, %s)\033[0m' % (self.sid, self.pid)

    def input_write(self, p2_, msg):
        p2_.write( msg )

    def env_msg(self, d):
        msg = d.msg
        imp = d.imp
        if comm.ishonest(self.sid, self.pid):
            self.z2p.reset()
            self.write('p2f', msg, imp )
        else: assert False

    def adv_msg(self, d):
        msg = d.msg
        imp = d.imp
        if comm.ishonest(self.sid, self.pid):
            assert False
        self.write('p2f', msg, imp )

    def func_msg(self, d):
        msg = d.msg
        imp = d.imp
        if comm.ishonest(self.sid,self.pid):
            self.write('p2z', msg, imp )
        else:
            self.write('p2a', msg, imp )

    def wrapper_msg(self, d):
        self.pump.write('dump')#dump.dump()

class ITMCruptWrappedPassthrough(ITMWrappedPassthrough):
    def __init__(self, sid, pid, a2p, p2a, z2p, p2z, f2p, p2f, w2p, p2w, pump, poly):
        ITMWrappedPassthrough.__init__(self, sid, pid, a2p, p2a, z2p, p2z, f2p, p2f, w2p, p2w, pump, poly)

    def env_msg(self, d):
        raise Exception("Env writing to a crupt party")
   
    def wrapper_msg(self, d):
        self.write( 'p2a', d.msg )

    def adv_msg(self, d):
        msg = d.msg
        imp = d.imp
        if msg[0] == 'P2W':
            self.write( 'p2w', msg[1] )
        elif msg[0] == 'P2F':
            self.write( 'p2f', msg[1])
        else:
            self.pump.write('dump')
    

from comm import setFunctionality2, setParty
class PartyWrapper:
    def __init__(self, z2p, p2z, f2p, p2f, a2p, p2a, tof):
        self.z2pid = {}
        self.f2pid = {}
        self.a2pid = {}
        self.z2p = z2p; self.p2z = p2z;
        self.f2p = f2p; self.p2f = p2f;
        self.a2p = a2p; self.p2a = p2a
        self.tof = tof  # TODO: for GUC this will be a problems, who to passthrough message to?

    def _newPID(self, sid, pid, _2pid, p2_, tag):
        pp2_ = GenChannel(('write-translate',sid,pid))
        _2pp = GenChannel(('read',sid,pid)) # _ to 

        def _translate():
            while True:
                r = gevent.wait(objects=[pp2_],count=1)
                r = r[0]
                d = r.read()
                msg = d.msg
                imp = d.imp
                pp2_.reset('pp2_ translate reset')
                p2_.write( ((sid,pid), msg), imp )
        gevent.spawn(_translate)

        _2pid[sid,pid] = _2pp
        return (_2pp, pp2_) 


    def newPID(self, sid, pid):
        print('[{}] Creating new party with pid: {}'.format(sid, pid))
        _z2p,_p2z = self._newPID(sid, pid, self.z2pid, self.p2z, 'NA')
        _f2p,_p2f = self._newPID(sid, pid, self.f2pid, self.p2f, 'NA')
        _a2p,_p2a = self._newPID(sid, pid, self.a2pid, self.p2a, 'NA')
        
        itm = ITMPassthrough(sid, pid, _a2p, _p2a, _z2p, _p2z, _f2p, _p2f) 
        setParty(itm)
        gevent.spawn(itm.run)

    def getPID(self, _2pid, sid, pid):
        if (sid,pid) in _2pid: return _2pid[sid,pid]
        else:
            self.newPID(sid, pid)
            return _2pid[sid,pid]

    def spawn(self,sid,pid):
        print('Spawning sid={}, pid={}'.format(sid,pid))
        self.newPID(sid,pid)

    def run(self):
        while True:
            ready = gevent.wait(objects=[self.z2p, self.f2p, self.a2p], count=1)
            r = ready[0]
            m = r.read() 
            if r == self.z2p:
                (sid,pid),msg = m.msg
                self.z2p.reset('z2p party reset')
                if not comm.ishonest(sid,pid):
                    raise Exception
                _pid = self.getPID(self.z2pid,sid,pid)
                _pid.write( ((sid,self.tof), msg) )
            elif r == self.f2p:
                self.f2p.reset('f2p in party')
                fro,(to,msg) = m.msg
                _pid = self.getPID(self.f2pid,sid,pid)
                _pid.write(msg)
            elif r == self.a2p:
                if comm.ishonest(self.sid,pid):
                    raise Exception
                self.a2p.reset('a2p in party')
                _pid = self.getPID(self.a2pid, sid, pid)
                _pid.write( msg )
                r = gevent.wait(objects=[self.f2p], count=1, timeout=0.1)
                if r:
                    r = r[0]
                    msg = r.read().msg
                    self.p2a.write( msg )
            else:
                dump.dump()

from collections import defaultdict
class ProtocolWrapper:
    def __init__(self, z2p, p2z, f2p, p2f, a2p, p2a, prot):
        self.z2pid = {}
        self.f2pid = {}
        self.a2pid = {}
        self.p2pid = {}
        self.z2p = z2p; self.p2z = p2z;
        self.f2p = f2p; self.p2f = p2f;
        self.a2p = a2p; self.p2a = p2a
        self.p2_ = GenChannel()
        self.prot = prot
        self.leaks = defaultdict(list)

    def _newPID(self, sid, pid, _2pid, p2_, tag):
        pp2_ = GenChannel(('write-translate',sid,pid)) 
        _2pp = GenChannel(('read',sid,pid)) # _ to 

        def _translate():
            while True:
                r = gevent.wait(objects=[pp2_],count=1)
                r = r[0]
                m = r.read()
                msg = m.msg
                imp = m.imp
                pp2_.reset('pp2_ translate reset')
                p2_.write( ((sid,pid), msg), imp )
        gevent.spawn(_translate)

        _2pid[sid,pid] = _2pp
        return (_2pp, pp2_) 

    def newPID(self, sid, pid):
        print('\033[1m[{}]\033[0m Creating new party with pid: {}'.format('PWrapper', pid))
        _z2p,_p2z = self._newPID(sid, pid, self.z2pid, self.p2z, 'NA')
        _f2p,_p2f = self._newPID(sid, pid, self.f2pid, self.p2f, 'NA')
        _a2p,_p2a = self._newPID(sid, pid, self.a2pid, self.p2a, 'NA')
        _2p, p2_ = self._newPID(sid, pid, self.p2pid, self.p2_, 'NA')
        
        if comm.isdishonest(sid, pid):
            print('\033[1m[{}]\033[0m Party is corrupt, so ITMSyncCruptProtocol'.format(pid))
            p = ITMSyncCruptProtocol(sid, pid, _a2p, _p2a, _z2p, _p2z, _f2p, _p2f)
        else:
            p = self.prot(sid, pid, _p2f,_f2p, _p2a,_a2p, _p2z,_z2p)
        setParty(p)
        gevent.spawn(p.run)

    def getPID(self, _2pid, sid, pid):
        if (sid,pid) in _2pid: return _2pid[sid,pid]
        else:
            self.newPID(sid,pid)
            return _2pid[sid,pid]

    def spawn(self, sid, pid):
        self.newPID(sid, pid)

    def run(self):
        while True:
            ready = gevent.wait(objects=[self.z2p, self.f2p, self.a2p, self.p2_], count=1)
            r = ready[0]
            if r == self.z2p:
                ((sid,pid), msg) = r.read() 
                self.z2p.reset('z2p party reset')
                if not comm.ishonest(sid,pid):
                    raise Exception
                # pass onto the functionality
                _pid = self.getPID(self.z2pid,sid,pid)
                _pid.write(msg)
            elif r == self.f2p:
                m = r.read()
                (fro,(to,msg)) = m
                sid,pid = to
                self.f2p.reset('f2p in party')
                _pid = self.getPID(self.f2pid, sid, pid)
                _pid.write( (fro, msg) )
            elif r == self.a2p:
                (sid,pid), msg = r.read() 
                self.a2p.reset('a2p in party')
                if comm.ishonest(sid,pid):
                    raise Exception
                _pid = self.getPID(self.a2pid, sid, pid)
                _pid.write( msg )
            elif r == self.p2_:
                (fro, msg) = r.read() 
                self.p2_.reset()
                _to,_m = msg
                _s,_p = _to
                print('[{}] Message for ({}): {}'.format(_s, _p, _m))
                if comm.ishonest(_s,_p):
                    _pid = self.getPID(self.p2pid,_s, _p)
                    _pid.write( (fro, _m)  )
                else:
                    self.p2a.write( (fro,_m) )
            else:
                dump.dump()
        print('Its over??')

class WrappedPartyWrapper:
    def __init__(self, z2p, p2z, f2p, p2f, a2p, p2a, w2p, p2w, pump, tof, poly):
        self.z2pid = {}
        self.f2pid = {}
        self.a2pid = {}
        self.w2pid = {}
        self.poly = poly
        self.pump = pump
        self.z2p = z2p; self.p2z = p2z
        self.f2p = f2p; self.p2f = p2f
        self.a2p = a2p; self.p2a = p2a
        self.w2p = w2p; self.p2w = p2w
        self.tof = tof  # TODO: for GUC this will be a problems, who to passthrough message to?
        self.log = logging.getLogger('WrappedPartyWrapper')

    def _newPID(self, sid, pid, _2pid, p2_, tag):
        pp2_ = GenChannel(('write-translate',sid,pid))
        _2pp = GenChannel(('read',sid,pid)) # _ to 

        def _translate():
            while True:
                r = gevent.wait(objects=[pp2_],count=1)
                r = r[0]
                d = r.read()
                msg = d.msg
                imp = d.imp
                pp2_.reset('pp2_ translate reset')
                p2_.write( ((sid,pid), msg), imp )
        gevent.spawn(_translate)

        _2pid[sid,pid] = _2pp
        return (_2pp, pp2_) 


    def newPID(self, sid, pid):
        self.log.debug('\033[1m[Wrapped Party {}]\033[0m Creating new party with pid: {}'.format(sid, pid))
        _z2p,_p2z = self._newPID(sid, pid, self.z2pid, self.p2z, 'NA')
        _f2p,_p2f = self._newPID(sid, pid, self.f2pid, self.p2f, 'NA')
        _a2p,_p2a = self._newPID(sid, pid, self.a2pid, self.p2a, 'NA')
        _w2p,_p2w = self._newPID(sid, pid, self.w2pid, self.p2w, 'NA')
        
        #itm = ITMPassthrough(sid, pid, _a2p, _p2a, _z2p, _p2z, _f2p, _p2f) 
        itm = ITMWrappedPassthrough(sid, pid, _a2p, _p2a, _z2p, _p2z, _f2p, _p2f, _w2p, _p2w, self.pump, self.poly)
        setParty(itm)
        gevent.spawn(itm.run)

    def getPID(self, _2pid, sid, pid):
        if (sid,pid) in _2pid: return _2pid[sid,pid]
        else:
            self.newPID(sid, pid)
            return _2pid[sid,pid]

    def spawn(self,sid,pid):
        print('Spawning sid={}, pid={}'.format(sid,pid))
        self.newPID(sid,pid)

    def run(self):
        while True:
            ready = gevent.wait(objects=[self.z2p, self.f2p, self.a2p], count=1)
            r = ready[0]
            m = r.read() 
            if r == self.z2p:
                (sid,pid),msg = m.msg
                self.z2p.reset('z2p party reset')
                #print('z2p import', m.imp)
                if not comm.ishonest(sid,pid):
                    raise Exception
                _pid = self.getPID(self.z2pid,sid,pid)
                _pid.write( ((sid,self.tof), msg), m.imp)
            elif r == self.f2p:
                self.f2p.reset('f2p in party')
                fro,(to,msg) = m.msg
                sid,pid = to
                _pid = self.getPID(self.f2pid,sid,pid)
                _pid.write(msg, m.imp)
            elif r == self.a2p:
                (sid,pid),msg = m.msg
                if comm.ishonest(sid,pid):
                    raise Exception
                self.a2p.reset('a2p in party')
                _pid = self.getPID(self.a2pid, sid, pid)
                _pid.write( msg, m.imp )
                r = gevent.wait(objects=[self.f2p], count=1, timeout=0.1)
                if r:
                    r = r[0]
                    msg = r.read().msg
                    self.f2p.reset()
                    self.p2a.write( msg, m.imp )
            else:
                dump.dump()

class WrappedProtocolWrapper:
    def __init__(self, z2p, p2z, f2p, p2f, a2p, p2a, w2p, p2w, pump, prot, poly):
        self.z2pid = {}
        self.f2pid = {}
        self.a2pid = {}
        self.p2pid = {}
        self.w2pid = {}
        self.poly = poly
        self.z2p = z2p; self.p2z = p2z;
        self.f2p = f2p; self.p2f = p2f;
        self.a2p = a2p; self.p2a = p2a
        self.w2p = w2p; self.p2w = p2w
        self.p2_ = GenChannel()
        self.prot = prot
        self.leaks = defaultdict(list)
        self.pump = pump
        self.log = logging.getLogger('WrappedProtocolWrapper')

    def _newPID(self, sid, pid, _2pid, p2_, tag):
        pp2_ = GenChannel(('write-translate',sid,pid)) 
        _2pp = GenChannel(('read',sid,pid)) # _ to 

        def _translate():
            while True:
                r = gevent.wait(objects=[pp2_],count=1)
                r = r[0]
                m = r.read()
                msg = m.msg
                imp = m.imp
                pp2_.reset('pp2_ translate reset')
                #print('\n\t Translating: {} --> {}'.format(msg, ((sid,pid),msg)))
                #print('\t\t\033[93m {} --> {}, msg={}\033[0m'.format((self.sid,pid), msg[0], msg[1]))
                #print('\ntranslate protocol, pid={}, msg={}, import={}\n'.format(pid, msg, imp))
                self.leaks[sid,pid].append( msg )
                p2_.write( ((sid,pid), msg), imp )
        gevent.spawn(_translate)

        _2pid[sid,pid] = _2pp
        return (_2pp, pp2_) 

    def newPID(self, sid, pid):
        self.log.debug('\033[1m[WrappedProtocol {}]\033[0m Creating new party with pid: {}'.format('PWrapper', pid))
        _z2p,_p2z = self._newPID(sid, pid, self.z2pid, self.p2z, 'NA')
        _f2p,_p2f = self._newPID(sid, pid, self.f2pid, self.p2f, 'NA')
        _a2p,_p2a = self._newPID(sid, pid, self.a2pid, self.p2a, 'NA')
        _w2p,_p2w = self._newPID(sid, pid, self.w2pid, self.p2w, 'NA')
        _2p, p2_ = self._newPID(sid, pid, self.p2pid, self.p2_, 'NA')
       
        # TODO add wrapped passthrough party
        if comm.isdishonest(sid, pid):
            print('\033[1m[{}]\033[0m Party is corrupt, so ITMCruptWrappedPassthrough'.format(pid))
            #p = ITMSyncCruptProtocol(sid, pid, _a2p, _p2a, _z2p, _p2z, _f2p, _p2f)
            #p = ITMWrappedPassthrough(sid, pid, _a2p, _p2a, _z2p, _p2z, _f2p, _p2f, _w2p, _p2w)
            p = ITMCruptWrappedPassthrough(sid, pid, _a2p, _p2a, _z2p, _p2z, _f2p, _p2f, _w2p, _p2w, self.pump, self.poly)
        else:
            p = self.prot(sid, pid, {'p2f':_p2f, 'f2p':_f2p, 'p2a':_p2a, 'a2p':_a2p, 'p2z':_p2z, 'z2p':_z2p, 'p2w':_p2w, 'w2p':_w2p}, self.pump, self.poly)
        setParty(p)
        gevent.spawn(p.run)

    def getPID(self, _2pid, sid, pid):
        if (sid,pid) in _2pid: return _2pid[sid,pid]
        else:
            self.newPID(sid,pid)
            return _2pid[sid,pid]

    def spawn(self, sid, pid):
        self.newPID(sid, pid)

    def run(self):
        while True:
            ready = gevent.wait(objects=[self.z2p, self.f2p, self.a2p, self.w2p, self.p2_], count=1)
            r = ready[0]
            if r == self.z2p:
                d = r.read()
                ((sid,pid), msg) = d.msg
                self.z2p.reset('z2p party reset')
                if not comm.ishonest(sid,pid):
                    raise Exception
                # pass onto the functionality
                _pid = self.getPID(self.z2pid,sid,pid)
                _pid.write(msg, d.imp)
            elif r == self.f2p:
                d = r.read()
                (fro,(to,msg)) = d.msg
                sid,pid = to
                self.f2p.reset('f2p in party')
                _pid = self.getPID(self.f2pid, sid, pid)
                _pid.write( (fro, msg), d.imp)
            elif r == self.a2p:
                d = r.read()
                route,msg = d.msg
                sid,pid = route
                self.a2p.reset('a2p in party')
                if comm.ishonest(sid,pid):
                    raise Exception
                _pid = self.getPID(self.a2pid, sid, pid)
                _pid.write( msg, d.imp )
            elif r == self.p2_:
                (fro, msg) = r.read() 
                self.p2_.reset()
                _to,_m = msg
                _s,_p = _to
                print('[{}] Message for ({}): {}'.format(_s, _p, _m))
                if comm.ishonest(_s,_p):
                    _pid = self.getPID(self.p2pid,_s, _p)
                    _pid.write( (fro, _m)  )
                else:
                    self.p2a.write( (fro,_m) )
            elif r == self.w2p:
                d = r.read()
                (_s,_p),msg = d.msg
                self.w2p.reset()
                _pid = self.getPID(self.w2pid, _s, _p)
                _pid.write( msg, d.imp )
            else:
                print('Its over'); dump.dump()
        print('Its over??')

class FunctionalityWrapper:
    def __init__(self, p2f, f2p, a2f, f2a, z2f, f2z):
        self.z2fid = {}
        self.p2fid = {}
        self.a2fid = {}
        self.f2fid = {}
        self.p2f = p2f; self.f2p = f2p
        self.a2f = a2f; self.f2a = f2a
        self.z2f = z2f; self.f2z = f2z
        self.f2_ = GenChannel('f2_')
        self.tagtocls = {}


    def newcls(self, tag, cls):
        print('New cls', tag, cls)
        self.tagtocls[tag] = cls

    def _newFID(self, _2fid, f2_, sid, tag):
        ff2_ = GenChannel(('write-translate',sid,tag))
        _2ff = GenChannel(('read',sid,tag))

        def _translate():
            while True:
                r = gevent.wait(objects=[ff2_],count=1)
                m = r[0].read()
                msg = m.msg
                imp = m.imp
                ff2_.reset()
                f2_.write( ((sid,tag), msg), imp )
        gevent.spawn(_translate) 
        _2fid[sid,tag] = _2ff
        return (_2ff, ff2_) 


    '''Received a message for a functionality that doesn't exist yet
    create a new functionality and add it to the wrapper'''
    def newFID(self, sid, tag, cls, params=()):
        #print('\033[1m[{}]\033[0m Creating new Functionality with sid={}, pid={}'.format('FWrapper',sid, tag))
        _z2f,_f2z = self._newFID(self.z2fid, self.f2z, sid, tag)
        _p2f,_f2p = self._newFID(self.p2fid, self.f2p, sid, tag)
        _a2f,_f2a = self._newFID(self.a2fid, self.f2a, sid, tag)
        _2f,_f2_ = self._newFID(self.f2fid, self.f2_, sid, tag)
      
        f = cls(sid, -1, _f2p, _p2f, _f2a, _a2f, _f2z, _z2f)
        setFunctionality2(sid,tag)
        gevent.spawn(f.run)

    '''Get the relevant channel for the functionality with (sid,tag)
    for example, if call is getFID(self, self.a2fid, sid, tag) this
    means: get the a2f channel for the functionality.'''
    def getFID(self, _2pid, sid,tag):
        if (sid,tag) in _2pid: return _2pid[sid,tag]
        else:
            cls = self.tagtocls[tag]
            self.newFID(sid, tag, cls)
            return _2pid[sid,tag]

    '''Basic gevent loop that will run forever'''
    def run(self):
        while True:
            ready = gevent.wait(objects=[self.z2f, self.p2f, self.a2f, self.f2_], count=1)
            r = ready[0]
            if r == self.z2f:  # should never happen
                dump.dump()
                self.z2f.reset()
            elif r == self.p2f:
                ((_sid,_pid), msg) = r.read() 
                self.p2f.reset()
                ((__sid,_tag), msg) = msg
                _fid = self.getFID(self.p2fid, __sid, _tag)
                _fid.write( ((_sid,_pid), msg) )
            elif r == self.a2f:
                msg = r.read()
                self.a2f.reset()
                ((sid,tag), msg) = msg
                _fid = self.getFID(self.a2fid, sid, tag)
                _fid.write( msg )
            elif r == self.f2_:
                ((_sid,_pid), msg) = r.read()
                self.f2_.reset()
                ((__sid,__pid), _msg) = msg
                _fid = self.getFID(self.f2fid, __sid,__pid)
                _fid.write( ((_sid,_pid), _msg) )
            else:
                print('SHEEEit')
                dump.dump()

class WrappedFunctionalityWrapper:
    def __init__(self, p2f, f2p, a2f, f2a, z2f, f2z, w2f, f2w, pump, poly):
        self.z2fid = {}
        self.p2fid = {}
        self.a2fid = {}
        self.f2fid = {}
        self.w2fid = {}
        self.poly = poly
        self.pump = pump
        self.p2f = p2f; self.f2p = f2p
        self.a2f = a2f; self.f2a = f2a
        self.z2f = z2f; self.f2z = f2z
        self.w2f = w2f; self.f2w = f2w
        self.f2_ = GenChannel('f2_')
        self.tagtocls = {}


    def newcls(self, tag, cls):
        print('New cls', tag, cls)
        self.tagtocls[tag] = cls

    def _newFID(self, _2fid, f2_, sid, tag):
        ff2_ = GenChannel(('write-translate',sid,tag))
        _2ff = GenChannel(('read',sid,tag))

        def _translate():
            while True:
                r = gevent.wait(objects=[ff2_],count=1)
                m = r[0].read()
                msg = m.msg
                imp = m.imp
                ff2_.reset()
                f2_.write( ((sid,tag), msg), imp )
        gevent.spawn(_translate) 
        _2fid[sid,tag] = _2ff
        return (_2ff, ff2_) 


    '''Received a message for a functionality that doesn't exist yet
    create a new functionality and add it to the wrapper'''
    def newFID(self, sid, tag, cls, params=()):
        #print('\033[1m[{}]\033[0m Creating new Functionality with sid={}, pid={}'.format('FWrapper',sid, tag))
        _z2f,_f2z = self._newFID(self.z2fid, self.f2z, sid, tag)
        _p2f,_f2p = self._newFID(self.p2fid, self.f2p, sid, tag)
        _a2f,_f2a = self._newFID(self.a2fid, self.f2a, sid, tag)
        _w2f,_f2w = self._newFID(self.w2fid, self.f2w, sid, tag)
        _2f,_f2_ = self._newFID(self.f2fid, self.f2_, sid, tag)
      
        #f = cls(sid, -1, _f2p, _p2f, _f2a, _a2f, _f2z, _z2f, _f2w, _w2f)
        f = cls(sid, -1, {'f2p':_f2p, 'p2f':_p2f, 'f2a':_f2a, 'a2f':_a2f, 'f2z':_f2z, 'z2f':_z2f, 'f2w':_f2w, 'w2f':_w2f}, self.pump, self.poly)
        setFunctionality2(sid,tag,f)
        gevent.spawn(f.run)

    '''Get the relevant channel for the functionality with (sid,tag)
    for example, if call is getFID(self, self.a2fid, sid, tag) this
    means: get the a2f channel for the functionality.'''
    def getFID(self, _2pid, sid,tag):
        if (sid,tag) in _2pid: return _2pid[sid,tag]
        else:
            cls = self.tagtocls[tag]
            self.newFID(sid, tag, cls)
            return _2pid[sid,tag]

    '''Basic gevent loop that will run forever'''
    def run(self):
        while True:
            ready = gevent.wait(objects=[self.z2f, self.p2f, self.a2f, self.f2_, self.w2f], count=1)
            r = ready[0]
            if r == self.z2f:  # should never happen
                dump.dump()
                self.z2f.reset()
            elif r == self.p2f:
                d = r.read()
                ((_sid,_pid), msg) = d.msg
                self.p2f.reset()
                ((__sid,_tag), msg) = msg
                _fid = self.getFID(self.p2fid, __sid, _tag)
                _fid.write( ((_sid,_pid), msg), d.imp)
            elif r == self.a2f:
                d = r.read()
                msg = d.msg
                self.a2f.reset()
                ((sid,tag), msg) = msg
                _fid = self.getFID(self.a2fid, sid, tag)
                _fid.write( msg, d.imp )
            elif r == self.f2_:
                # TODO : deprecated until GUC
                ((_sid,_pid), msg) = r.read()
                self.f2_.reset()
                ((__sid,__pid), _msg) = msg
                _fid = self.getFID(self.f2fid, __sid,__pid)
                _fid.write( ((_sid,_pid), _msg) )
            elif r == self.w2f:
                d = r.read()
                ((__sid,__pid), _msg) = d.msg
                self.w2f.reset()
                _fid = self.getFID(self.w2fid, __sid, __pid) 
                _fid.write( _msg, d.imp )
            else:
                print('SHEEEit')
                dump.dump()
