import os
import sys
from uc.utils import wait_for, waits
from gevent.queue import Queue, Channel, Empty
from gevent.event import AsyncResult, Event
from numpy.polynomial.polynomial import Polynomial
from uc.errors import WriteImportError, TickError
from uc.messages import *
import gevent
import logging
import inspect

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
        self.id = i

    def write(self, data, imp=0):
        if not self.is_set():
            self._data = MSG(data, imp); self.set()
            #print('\033[91m WRITE id={}, msg={}, imp={}\033[0m'.format(self.i, self._data, imp))
        else: 
            raise Exception("\033[1mwriting to channel already full with {}. Writing {} in {}\033[0m".format(self._data,data,self.i))
            dump.dump()

    def __str__(self):
        return "Channel id:{}".format(self.id)

    def read(self): 
        return self._data
    def reset(self, s=''): 
        self.clear()

def forever(f):
    while True:
        f()

def fork(f):
    gevent.spawn(f)

def fwd(ch1, ch2):
    def foo(ch1,ch2):
        print('Foo function. Ch1:', ch1, 'Ch2:', ch2)
        while True:
            r = gevent.wait([ch1])
            m = r[0].read()
            print('Read mesage on ch1:', m)
            ch2.write( m.msg, m.imp )
    gevent.spawn(foo, ch1, ch2)

class ITMContext:
    def __init__(self, poly):
        self.imp_in = 0
        self.imp_out = 0
        self.spent = 0
        self.marked = 0
        self.poly = poly
    
    def tick(self, poly, n):
#        print('tick imp_in', self.imp_in, 'imp_out', self.imp_out, 'spent', self.spent, 'marked', self.marked)
        if self.poly(self.marked) < self.spent + n:
            self.generate_pot(1)
        self.spent += 1

    def generate_pot(self, n):
        if self.imp_in - self.imp_out - self.marked >= n:
            self.marked += n
        else:
            raise Exception("Can't mark any more tokens, you're out!")

class ITM:
    def __init__(self, k, bits, sid, pid, channels, handlers, poly, pump, importargs):
        self.k = k
        self.bits = bits
        self.sid = sid
        self.pid = pid
        self.pump = pump
        self.poly = poly
        self.channels = channels
        self.handlers = handlers
        self.importargs = importargs

        if 'ctx' not in importargs:
            self.ctx = ITMContext(self.poly)
        else:
            self.ctx = importargs['ctx']
        if 'impflag' in importargs:
            self.impflag = importargs['impflag']
        else:
            self.impflag = True

        self.log = logging.getLogger(type(self).__name__)

    @property
    def imp_in(self):
        return self.ctx.imp_in
    @imp_in.setter
    def imp_in(self, x):
        self.ctx.imp_in = x
    @property
    def imp_out(self):
        return self.ctx.imp_out
    @imp_out.setter
    def imp_out(self, x):
        self.ctx.imp_out = x
    @property
    def marked(self):
        return self.ctx.marked
    @marked.setter
    def marked(self, x):
        self.ctx.marked = x
    @property
    def spent(self):
        return self.ctx.spent
    @spent.setter
    def spent(self, x):
        self.ctx.spent = x
    
    def assertimp(self, x, y):
        if self.impflag:
            assert x == y

    def printstate(self):
        print('[sid={}, pid={}, imp_in={}, imp_out={}, spend={}, marked={}]'.format(self.sid, self.pid, self.imp_in, self.imp_out, self.spent, self.marked))


    def write(self, ch, msg, imp=0):
        if self.impflag:
            if self.imp_in - self.imp_out + self.marked >= imp:
                self.imp_out += imp
                self.channels[ch].write(msg, imp)
            else:
                # self.printstate() => this can print the import state out
                raise WriteImportError((self.sid,self.pid), msg, imp)
        else:
            self.channels[ch].write(msg, 0)

    def read(self, ch=None):
        return wait_for(self.channels[ch])

    def write_and_wait_for(self, ch=None, msg=None, imp=0, read=None):
        self.write(ch, msg, imp)
        m = self.read(read)
        return m

    def write_and_wait_expect(self, ch=None, msg=None, imp=0, read=None, expect=None):
        m = self.write_and_wait_for(ch, msg, imp, read)
        assert m.msg == expect, 'Expected: {}, Received: {}'.format(expect, m.msg)
        return m

    def sample(self, n):
        r = ""
        for _ in range(n):
            r += str(self.bits.randint(0,1))
        return int(r)

    def tick(self, n):
        self.ctx.tick(self.poly, n)

    def generate_pot(self, n):
        self.ctx.generate_pot(n)

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
            r.reset()
            try:
                self.handlers[r](d)
            except WriteImportError as e:
                self.log.error('WriteImportError: from={}, msg={}, imp={}'.format(e.fro, e.msg, e.imp))
                self.pump.write('dump')
            except TickError as e:
                self.log.error("TickError: from={}, amount={}".format(e.fro, e.amt))
                self.pump.write('dump')


class UCProtocol(ITM):
    def __init__(self, k, bits, sid, pid, channels, poly, pump, importargs):
        self.handlers = {
            channels['z2p'] : self.env_msg,
            channels['f2p'] : self.func_msg,
            channels['a2p'] : self.adv_msg,
        }
        ITM.__init__(self, k, bits, sid, pid, channels, self.handlers, poly, pump, importargs)

    def adv_msg(self, msg):
        Exception("adv_msg needs to be defined")

    def func_msg(self, msg):
        Exception("func_msg needs to be defined")

    def env_msg(self, msg):
        Exception("env_msg needs to be defined")

class UCFunctionality(ITM):
    def __init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs):
        print('functionality:', 'pump', pump, 'poly', poly)
        self.crupt = crupt
        self.handlers = {
            channels['p2f'] : self.party_msg,
            channels['a2f'] : self.adv_msg,
            channels['z2f'] : self.env_msg
        }
        ITM.__init__(self, k, bits, sid, pid, channels, self.handlers, poly, pump, importargs)

    def is_honest(self, sid, pid):
        return (sid,pid) in self.crupt

    def is_dishonest(self, sid, pid):
        return not self.is_honest(sid, pid)

    def adv_msg(self, msg):
        Exception("adv_msg needs to be defined")

    def party_msg(self, msg):
        Exception("func_msg needs to be defined")

    def env_msg(self, msg):
        Exception("env_msg needs to be defined")

class UCAdversary(ITM):
    def __init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs):
        self.crupt = crupt
        self.handlers = {
            channels['p2a'] : self.party_msg,
            channels['f2a'] : self.func_msg,
            channels['z2a'] : self.env_msg
        }
        ITM.__init__(self, k, bits, sid, pid, channels, self.handlers, poly, pump, importargs)

    def is_honest(self, sid, pid):
        return (sid,pid) in self.crupt

    def party_msg(self, d):
        Exception("party_msg needs to be implemented")

    def func_msg(self, d):
        Exception("func_msg needs to be implemented")

    def env_msg(self, d):
        Exception("env_msg needs to be implemented")

class UCWrappedAdversary(ITM):
    def __init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs):
        self.crupt = crupt
        self.handlers = {
            channels['p2a'] : self.party_msg,
            channels['f2a'] : self.func_msg,
            channels['z2a'] : self.env_msg,
            channels['w2a'] : self.wrapper_msg
        }
        ITM.__init__(self, k, bits, sid, pid, channels, self.handlers, poly, pump, importargs)

    def is_honest(self, sid, pid):
        return (sid,pid) in self.crupt

    def party_msg(self, d):
        Exception("party_msg needs to be implemented")

    def func_msg(self, d):
        Exception("func_msg needs to be implemented")

    def env_msg(self, d):
        Exception("env_msg needs to be implemented")

    def wrapper_msg(self, d):
        Exception("wrapper_msg needs to be implemented")

#class UCWrappedGlobalF(UCWrappedFunctionality):
#    def __init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs):
#        UCWrappedFunctionality.__init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs)

class UCWrappedFunctionality(ITM):
    def __init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs):
        self.crupt = crupt
        self.handlers = {
            channels['z2f'] : self.env_msg,
            channels['p2f'] : self.party_msg,
            channels['a2f'] : self.adv_msg,
            channels['w2f'] : self.wrapper_msg,
        }
        ITM.__init__(self, k, bits, sid, pid, channels, self.handlers, poly, pump, importargs)

    def is_honest(self, sid, pid):
        return (sid,pid) in self.crupt

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
        self.write('f2w', ((self.sid, 'F_Wrapper'), ('leak', msg)), imp)
        m = wait_for(self.channels['w2f']).msg
        assert m == ((self.sid, 'F_Wrapper'), ('OK',))

    def clock_round(self):
        m = self.write_and_wait_for(
            ch='f2w', msg=((self.sid, 'F_Wrapper'), ('clock-round',)),
            imp=0, read='w2f'
        )

        #self.write('f2w', ('clock-round',), 0)
        #rnd = wait_for(self.channels['w2f']).msg[1]
        return m.msg[1]

    def schedule(self, f, args, d):
        self.write_and_wait_expect(
            ch='f2w', msg=((self.sid, 'F_Wrapper'), ('schedule', f, args, d)),
            read='w2f', expect=((self.sid, 'F_Wrapper'), ('OK',))
        )

class UCWrappedProtocol(ITM):
    def __init__(self, k, bits, sid, pid, channels, poly, pump, importargs):
        self.handlers = {
            channels['z2p'] : self.env_msg,
            channels['f2p'] : self.func_msg,
            channels['a2p'] : self.adv_msg,
            channels['w2p'] : self.wrapper_msg,
        }
        ITM.__init__(self, k, bits, sid, pid, channels, self.handlers, poly, pump, importargs)

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
    
    def clock_round(self):
        m = self.write_and_wait_for(
            ch='p2w', msg=((self.sid, 'F_Wrapper'), ('clock-round',)),
            imp=0, read='w2p'
        )
        return m.msg[1]

class UCGlobalF(ITM):
    def __init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs):
        self.crupt = crupt
        self.handlers = {
            channels['z2w'] : self.env_msg,
            channels['f2w'] : self.func_msg,
            channels['a2w'] : self.adv_msg,
            channels['p2w'] : self.party_msg,
            channels['_2w'] : self._2w_msg,
        }
        ITM.__init__(self, k, bits, sid, pid, channels, self.handlers, poly, pump, importargs)

    def is_honest(self, sid, pid):
        return (sid,pid) in self.crupt

    def adv_msg(self, msg):
        Exception("adv_msg needs to be defined")

    def func_msg(self, msg):
        Exception("func_msg needs to be defined")

    def env_msg(self, msg):
        Exception("env_msg needs to be defined")

    def party_msg(self, msg):
        Exception("party_msg needs to be defined")

    def _2w_msg(self, msg):
        Exception("_2w_msg needs to be implemented")

    def leak(self, msg):
        Exception("leak needs to be defined")

class UCAsyncWrappedFunctionality(UCWrappedFunctionality):
    def __init__(self, k, bits, crupt, sid, pid, channels):
        UCWrappedFunctionality.__init__(self, k, bits, crupt, sid, pid, channels)
        
    def leak(self, msg):
        self.f2w(("leak", msg))
        
    def eventually(self, msg):
        self.f2w(("eventually", msg))
        
class UCAsyncWrappedProtocol(UCWrappedProtocol):
    def __init__(self, k, bits, sid, pid, channels):
        UCWrappedProtocol.__init__(self, k, bits, sid, pid, channels)
        
    def leak(self, msg):
        dump.dump() # should not generally happen
        
    def eventually(self, msg):
        dump.dump() # should not generally happen
       

def ideal_party(tof):
    def _f(k, bits, sid, pid, channels, poly, pump, importargs):
        return DummyParty(k, bits, sid, pid, channels, poly, pump, importargs, tof)
    return _f

class DummyParty(ITM):
    def __init__(self, k, bits, sid, pid, channels, poly, pump, importargs):
        self.handlers = {
            channels['z2p'] : self.env_msg,
            channels['a2p'] : self.adv_msg,
            channels['f2p'] : self.func_msg
        }
        ITM.__init__(self, k, bits, sid, pid, channels, self.handlers, poly, pump, importargs)

    def adv_msg(self, d):
        self.write('p2f', d.msg, d.imp)
        raise Exception('Adv cant write to an honest party')

    def env_msg(self, d):
        self.write('p2f', d.msg, d.imp)

    def func_msg(self, d):
        fro,msg = d.msg
        self.write('p2z', msg, d.imp)

class WrappedDummyParty(ITM):
    def __init__(self, k, bits, sid, pid, channels, poly, pump, importargs):
        self.handlers = {
            channels['z2p'] : self.env_msg,
            channels['a2p'] : self.adv_msg,
            channels['f2p'] : self.func_msg,
            channels['w2p'] : self.wrapper_msg
        }
        ITM.__init__(self, k, bits, sid, pid, channels, self.handlers, poly, pump, importargs)

    def adv_msg(self, d):
        raise Exception("Adv can't write to an honest party")

    def env_msg(self, d):
        self.write('p2f', d.msg, d.imp)

    def func_msg(self, d):
        fro,msg = d.msg
        self.write('p2z', msg, d.imp)

    def wrapper_msg(self, d):
        self.write('p2z', d.msg, d.imp)

def partyWrapper(tof):
    def f(k, bits, crupt, sid, channels, pump, poly, importargs):
        return PartyWrapper(k, bits, crupt, sid, channels, pump, tof, poly, importargs)
    return f

#class PartyWrapper(ITM):
#    def __init__(self, k, bits, crupt, sid, channels, pump, tof, poly, importargs):
#        self.crupt = crupt
#        self.z2pid = {}
#        self.f2pid = {}
#        self.a2pid = {}
#        self.tof = tof  # TODO: for GUC this will be a problems, who to passthrough message to?
#        self.log = logging.getLogger('PartyWrapper')
#        self.handlers = {
#            channels['z2p'] : self.env_msg,
#            channels['f2p'] : self.func_msg,
#            channels['a2p'] : self.adv_msg,
#        }
#        ITM.__init__(self, k, bits, sid, None, channels, self.handlers, poly, pump, importargs)
#
#    def is_dishonest(self, sid, pid):
#        return (sid,pid) in self.crupt
#
#    def is_honest(self, sid, pid):
#        return not self.is_dishonest(sid,pid)
#
#    def _newPID(self, sid, pid, _2pid, p2_, tag):
#        pp2_ = GenChannel(('write-translate',sid,pid))
#        _2pp = GenChannel(('read',sid,pid)) # _ to 
#
#        def _translate():
#            while True:
#                r = gevent.wait(objects=[pp2_],count=1)
#                m = r[0].read()
#                pp2_.reset('pp2_ translate reset')
#                p2_.write( ((sid,pid), m.msg), m.imp )
#        gevent.spawn(_translate)
#
#        _2pid[sid,pid] = _2pp
#        return (_2pp, pp2_) 
#
#    def newPID(self, sid, pid):
#        print('[{}] Creating new party with pid: {}'.format(sid, pid))
#        _z2p,_p2z = self._newPID(sid, pid, self.z2pid, self.channels['p2z'], 'NA')
#        _f2p,_p2f = self._newPID(sid, pid, self.f2pid, self.channels['p2f'], 'NA')
#        _a2p,_p2a = self._newPID(sid, pid, self.a2pid, self.channels['p2a'], 'NA')
#        
#        itm = DummyParty(self.k, self.bits, self.sid, pid, {'a2p':_a2p,'p2a':_p2a, 'z2p':_z2p,'p2z':_p2z, 'f2p':_f2p,'p2f':_p2f}, self.poly, self.pump, self.importargs)
#        gevent.spawn(itm.run)
#
#    def getPID(self, _2pid, sid, pid):
#        if (sid,pid) in _2pid: return _2pid[sid,pid]
#        else:
#            self.newPID(sid, pid)
#            return _2pid[sid,pid]
#   
#    def env_msg(self, d):
#        msg = d.msg
#        imp = d.imp
#        (sid,pid),msg = msg
#        if self.is_dishonest(sid,pid): raise Exception("Env writing to corrupt party: {}\n\tCruptset: {}".format((sid,pid), self.crupt))
#        _pid = self.getPID(self.z2pid,sid,pid)
#        _pid.write( ((sid,self.tof), msg), imp )
#
#    def func_msg(self, d):
#        msg = d.msg
#        imp = d.imp
#        print('func message', d)
#        fro,((sid,pid),msg) = msg
#        if self.is_dishonest(sid,pid):
#            self.write( 'p2a', ((sid,pid), msg), 0)#imp)
#        else:
#            _pid = self.getPID(self.f2pid,sid,pid)
#            _pid.write( (fro, msg), imp)
#
#    def adv_msg(self, d):
#        msg = d.msg
#        imp = d.imp
#        (sid,pid), msg = msg
#        if self.is_honest(sid,pid): raise Exception("adv writing to honest party")
#        #_pid = self.getPID(self.a2pid, sid, pid)
#        #_pid.write( msg, imp )
#        self.write( 'p2f', ((sid,pid), m.msg), m.imp )

def protocolWrapper(prot):
    def f(k, bits, crupt, sid, channels, pump, poly, importargs):
        return ProtocolWrapper(k, bits, crupt, sid, channels, pump, prot, poly, importargs)
    return f

from collections import defaultdict
class ProtocolWrapper(ITM):
    def __init__(self, k, bits, crupt, sid, channels, pump, prot, poly, importargs):
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
        ITM.__init__(self, k, bits, sid, None, channels, self.handlers, poly, pump, importargs)

    def is_dishonest(self, sid, pid):
        return (sid,pid) in self.crupt

    def is_honest(self, sid, pid):
        return not self.is_dishonest(sid,pid)

    def _newPID(self, sid, pid, _2pid, p2_, tag):
        pp2_ = GenChannel(('write-translate-{}'.format(tag),sid,pid)) 
        _2pp = GenChannel(('read-{}'.format(tag),sid,pid)) # _ to 

        def _translate():
           while True:
                r = gevent.wait(objects=[pp2_],count=1)
                m = r[0].read()
                pp2_.reset('pp2_ translate reset')
                p2_.write( ((sid,pid), m.msg), m.imp )
        gevent.spawn(_translate)

        _2pid[sid,pid] = _2pp
        return (_2pp, pp2_) 

    def newPID(self, sid, pid):
        print('\033[1m[{}]\033[0m Creating new party with pid: {}'.format('PWrapper', pid))
        _z2p,_p2z = self._newPID(sid, pid, self.z2pid, self.channels['p2z'], 'p2z')
        _f2p,_p2f = self._newPID(sid, pid, self.f2pid, self.channels['p2f'], 'p2f')
        _a2p,_p2a = self._newPID(sid, pid, self.a2pid, self.channels['p2a'], 'p2a')
        
        p = self.prot(self.k, self.bits, self.sid, pid, {'a2p':_a2p,'p2a':_p2a, 'z2p':_z2p,'p2z':_p2z, 'f2p':_f2p, 'p2f':_p2f}, self.poly, self.pump, self.importargs)
        gevent.spawn(p.run)

    def getPID(self, _2pid, sid, pid):
        if (sid,pid) in _2pid: return _2pid[sid,pid]
        else:
            self.newPID(sid,pid)
            return _2pid[sid,pid]

    def env_msg(self, d):
        msg = d.msg
        imp = d.imp
        ((sid,pid), msg) = msg
        if self.is_dishonest(sid,pid): raise Exception("Environment writing to corrupt party")
        _pid = self.getPID(self.z2pid,sid,pid)
        _pid.write(msg, imp)
    
    def func_msg(self, d):
        msg = d.msg
        imp = d.imp
        #(fro, ((sid,pid), msg)) = msg
        (sid,pid),msg = msg
        print('func message ot adversary, msg: {}'.format(msg))
        if self.is_dishonest(sid,pid):
            self.write('p2a', ((sid,pid), msg), 0)#imp)
        else:
            _pid = self.getPID(self.f2pid, sid, pid)
            #_pid.write( (fro, msg), imp )
            _pid.write( msg, imp )

    def adv_msg(self, d):
        msg = d.msg
        imp = d.imp
        (sid,pid), msg = msg
        if self.is_honest(sid,pid): raise Exception("adv writing to an honest party: {}. Cruptset: {}".format((sid,pid), self.crupt))
        tag,msg = msg
        #_pid = self.getPID(self.a2pid, sid, pid)
        #_pid.write( msg, imp )
        self.write( 'p2f', ((sid,pid), msg), imp)

#def wrappedPartyWrapper(tof):
#    def f(k, bits, crupt, sid, channels, pump, poly, importargs):
#        return WrappedPartyWrapper(k, bits, crupt, sid, channels, pump, tof, poly, importargs)
#    return f
#
#class WrappedPartyWrapper(PartyWrapper):
#    def __init__(self, k, bits, crupt, sid, channels, pump, tof, poly, importargs):
#        self.w2pid = {}
#        self.log = logging.getLogger('WrappedPartyWrapper')
#        PartyWrapper.__init__(self, k, bits, crupt, sid, channels, pump, tof, poly, importargs)
#        self.handlers[ channels['w2p'] ] = self.wrapper_msg
#
#    def newPID(self, sid, pid):
#        self.log.debug('\033[1m[Wrapped Party {}]\033[0m Creating new party with pid: {}'.format(sid, pid))
#        _z2p,_p2z = self._newPID(sid, pid, self.z2pid, self.channels['p2z'], 'NA')
#        _f2p,_p2f = self._newPID(sid, pid, self.f2pid, self.channels['p2f'], 'NA')
#        _a2p,_p2a = self._newPID(sid, pid, self.a2pid, self.channels['p2a'], 'NA')
#        _w2p,_p2w = self._newPID(sid, pid, self.w2pid, self.channels['p2w'], 'NA')
#        
#        itm = WrappedDummyParty(self.k, self.bits, self.sid, pid, {'a2p':_a2p,'p2a':_p2a, 'z2p':_z2p,'p2z':_p2z, 'f2p':_f2p,'p2f':_p2f, 'w2p':_w2p,'p2w':_p2w}, self.poly, self.pump, self.importargs)
#        gevent.spawn(itm.run)
#
#    def getPID(self, _2pid, sid, pid):
#        if (sid,pid) in _2pid: return _2pid[sid,pid]
#        else:
#            assert sid == self.sid
#            self.newPID(sid, pid)
#            return _2pid[sid,pid]
#
#    def adv_msg(self, d):
#        msg = d.msg
#        imp = d.imp
#        (sid,pid), msg = msg
#        if self.is_honest(sid,pid): raise Exception("adv writing to an honest party: {}. Cruptset: {}".format((sid,pid), self.crupt))
#        tag,msg = msg
#        if tag == 'P2W':
#            self.write('p2w', ((sid,pid), msg), imp)
#        elif tag == 'P2F':
#            self.write('p2f', ((sid,pid), msg), imp)
#        else:
#            raise Exception("Not such tag over a2p: {}".format(tag))
#
#    def wrapper_msg(self, d):
#        msg = d.msg
#        imp = d.imp
#        (sid,pid),msg = msg
#        if self.is_dishonest(sid,pid):
#            self.write('p2a', ((sid,pid), msg), 0)#imp)
#        else:
#            _pid = self.getPID(self.w2pid, sid, pid)
#            _pid.write( msg, imp )

def wrappedProtocolWrapper(prot):
    def f(k, bits, crupt, sid, channels, pump, poly, importargs):
        return WrappedProtocolWrapper(k, bits, crupt, sid, channels, pump, prot, poly, importargs)
    return f

class WrappedProtocolWrapper(ProtocolWrapper):
    def __init__(self, k, bits, crupt, sid, channels, pump, prot, poly, importargs):
        self.w2pid = {}
        self.log = logging.getLogger('WrappedProtocolWrapper')
        ProtocolWrapper.__init__(self, k, bits, crupt, sid, channels, pump, prot, poly, importargs)
        print('Wrapped protocol wrapper crupt', crupt)
        self.handlers[channels['w2p']] = self.wrapper_msg


    def newPID(self, sid, pid):
        self.log.debug('\033[1m[WrappedProtocol {}]\033[0m Creating new party with pid: {}'.format('PWrapper', pid))
        _z2p,_p2z = self._newPID(sid, pid, self.z2pid, self.channels['p2z'], 'NA')
        _f2p,_p2f = self._newPID(sid, pid, self.f2pid, self.channels['p2f'], 'NA')
        _a2p,_p2a = self._newPID(sid, pid, self.a2pid, self.channels['p2a'], 'NA')
        _w2p,_p2w = self._newPID(sid, pid, self.w2pid, self.channels['p2w'], 'NA')
       
        p = self.prot(self.k, self.bits, self.sid, pid, {'p2f':_p2f, 'f2p':_f2p, 'p2a':_p2a, 'a2p':_a2p, 'p2z':_p2z, 'z2p':_z2p, 'p2w':_p2w, 'w2p':_w2p}, self.pump, self.poly, self.importargs)
        gevent.spawn(p.run)

    def getPID(self, _2pid, sid, pid):
        if (sid,pid) in _2pid: return _2pid[sid,pid]
        else:
            assert sid == self.sid
            self.newPID(sid,pid)
            return _2pid[sid,pid]
    
    def adv_msg(self, d):
        msg = d.msg
        imp = d.imp
        (sid,pid), msg = msg
        if self.is_honest(sid,pid): raise Exception("adv writing to an honest party: {}, Cruptset: {}".format((sid,pid), self.crupt))
        tag,msg = msg
        if tag == 'P2W':
            self.write('p2w', ((sid,pid), msg), imp)
        elif tag == 'P2F':
            self.write('p2f', ((sid,pid), msg), imp)
        else:
            raise Exception("No such tag over a2p: {}".format(tag))

    def wrapper_msg(self, d):
        msg = d.msg
        imp = d.imp
        sender, msg = msg
        (sid, pid), msg = msg
        if self.is_dishonest(sid,pid):
            self.write('p2a', ((sid,pid), (sender, msg)), 0)
        else:
            _pid = self.getPID(self.w2pid, sid, pid)
            _pid.write((sender, msg), imp)

def DuplexWrapper(f1, f1tag, f2, f2tag):
    def f(k, bits, crupt, sid, channels, pump, poly, importargs):
        return GlobalFunctionalityWrapper(k, bits, crupt, sid, channels, pump, poly, importargs, [f1, f2], [f1tag, f2tag])
    return f

def GlobalFWrapper( _fs, _ftags ):
    def f(k, bits, crupt, sid, channels, pump, poly, importargs):
        return GlobalFunctionalityWrapper(k, bits, crupt, sid, channels, pump, poly, importargs, _fs, _ftags)
    return f

class GlobalFunctionalityWrapper(ITM):
    def __init__(self, k, bits, crupt, sid, channels, pump, poly, importargs, _fs, _ftags):
        self.z2wid = {}
        self.p2wid = {}
        self.a2wid = {}
        self.f2wid = {}
        self._2wid = {}
        self.crupt = crupt
        
        self.handlers = {
            channels['p2w'] : self.party_msg,
            channels['a2w'] : self.adv_msg,
            channels['z2w'] : self.env_msg,
            channels['f2w'] : self.func_msg,
            #channels['w2_'] : self.wrapper_msg,
        }
        ITM.__init__(self, k, bits, sid, None, channels, self.handlers, poly, pump, importargs)
        
        self.channels['w2_'] = GenChannel('w2_')
        self.handlers[self.channels['w2_']] = self._2w_msg

        for _f_, _ftag_ in zip(_fs, _ftags):
            self.newFID(self.sid, _ftag_, _f_)

    def _newFID(self, _2fid, f2_, sid, tag):
        ff2_ = GenChannel(('write-translate',sid,tag))
        _2ff = GenChannel(('read',sid,tag))

        def _translate():
            while True:
                r = gevent.wait(objects=[ff2_],count=1)
                m = r[0].read()
                print('translate')
                ff2_.reset()
                f2_.write( ((sid,tag), m.msg), m.imp )
        gevent.spawn(_translate) 
        _2fid[sid,tag] = _2ff
        return (_2ff, ff2_) 
    
    def getFID(self, _2pid, sid,tag):
        return _2pid[sid,tag]
    
    def newFID(self, sid, tag, cls):
        _z2w,_w2z = self._newFID(self.z2wid, self.channels['w2z'], sid, tag)
        _p2w,_w2p = self._newFID(self.p2wid, self.channels['w2p'], sid, tag)
        _a2w,_w2a = self._newFID(self.a2wid, self.channels['w2a'], sid, tag)
        _f2w,_w2f = self._newFID(self.f2wid, self.channels['w2f'], sid, tag)
        __2w,_w2_ = self._newFID(self._2wid, self.channels['w2_'], sid, tag)

        print('cls', cls)
        f = cls(self.k, self.bits, self.crupt, self.sid, tag, {'p2w':_p2w, 'w2p':_w2p, 'z2w':_z2w, 'w2z':_w2z, 'f2w':_f2w, 'w2f':_w2f, 'a2w':_a2w, 'w2a':_w2a, 'w2_':_w2_, '_2w':__2w}, self.pump, self.poly, self.importargs)
        gevent.spawn(f.run)

    def party_msg(self, m):
        fro, ((sid, tag), msg) = m.msg
        imp = m.imp
        fid = self.getFID( self.p2wid, sid, tag)
        fid.write( (fro, msg), imp )

    def adv_msg(self, m):
        (sid,tag),msg = m.msg
        imp = m.imp
        fid = self.getFID(self.a2wid, sid, tag)
        fid.write( msg,imp )

    def env_msg(self, m):
        (sid,tag), msg = m.msg
        imp = m.imp
        fid = self.getFID(self.z2wid, sid, tag)
        fid.write( msg, imp )

    def func_msg(self, m):
        print('fro', m.msg[0])
        print('sid,tag', m.msg[1][0])
        print('msg', m.msg[1][1])
        fro, ((sid,tag), msg) = m.msg
        imp = m.imp
        fid = self.getFID(self.f2wid, sid, tag)
        fid.write( (fro, msg), imp )

    def _2w_msg(self, m):
        print('2w_msg', m)
        fro, ((sid,tag), msg) = m.msg
        imp = m.imp
        fid = self.getFID(self._2wid, sid, tag)
        fid.write( (fro, msg), imp )

class FunctionalityWrapper(ITM):
    def __init__(self, k, bits, crupt, sid, channels, pump, poly, importargs):
        self.z2fid = {}
        self.p2fid = {}
        self.a2fid = {}
        self.f2fid = {}
       
        self.crupt = crupt
        self.tagtocls = {}
        self.handlers = {
            channels['p2f'] : self.party_msg,
            channels['a2f'] : self.adv_msg,
            channels['z2f'] : self.env_msg,
        }
    
        ITM.__init__(self, k, bits, sid, None, channels, self.handlers, poly, pump, importargs)


    def getFID(self, _2pid, sid, tag):
        return _2pid[sid,]

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
                ff2_.reset()
                f2_.write( ((sid,tag), m.msg), m.imp )
        gevent.spawn(_translate) 
        _2fid[sid,tag] = _2ff
        return (_2ff, ff2_) 


    '''Received a message for a functionality that doesn't exist yet
    create a new functionality and add it to the wrapper'''
    def newFID(self, sid, tag, cls, params=()):
        _z2f,_f2z = self._newFID(self.z2fid, self.channels['f2z'], sid, tag)
        _p2f,_f2p = self._newFID(self.p2fid, self.channels['f2p'], sid, tag)
        _a2f,_f2a = self._newFID(self.a2fid, self.channels['f2a'], sid, tag)
      
        f = cls(self.k, self.bits, self.crupt, sid, -1, {'f2p':_f2p,'p2f':_p2f, 'f2a':_f2a,'a2f':_a2f, 'f2z':_f2z,'z2f':_z2f}, self.pump, self.poly, self.importargs)
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

    def party_msg(self, m):
        print('Party msg:', m.msg)
        print(m.msg[0])
        print(m.msg[1][0])
        print(m.msg[1][1])
        fro, ((sid,tag),msg) = m.msg
        imp = m.imp
        fid = self.getFID(self.p2fid, sid, tag)
        fid.write( (fro, msg), imp )

    def adv_msg(self, m):
        (sid,tag),msg = m.msg
        imp = m.imp
        fid = self.getFID(self.a2fid, sid, tag)
        fid.write( msg, imp )

    def env_msg(self, m):
        raise Exception("env talking to F")

class WrappedFunctionalityWrapper(FunctionalityWrapper):
    #def __init__(self, k, bits, crupt, p2f, f2p, a2f, f2a, z2f, f2z, w2f, f2w, pump, poly, importargs):
    def __init__(self, k, bits, crupt, sid, channels, pump, poly, importargs):
        self.w2fid = {}
        FunctionalityWrapper.__init__(self, k, bits, crupt, sid, channels, pump, poly, importargs)
        self.handlers[channels['w2f']] = self.wrapper_msg

    def newcls(self, tag, cls):
        print('New cls', tag, cls)
        self.tagtocls[tag] = cls

    '''Received a message for a functionality that doesn't exist yet
    create a new functionality and add it to the wrapper'''
    def newFID(self, sid, tag, cls, params=()):
        #print('\033[1m[{}]\033[0m Creating new Functionality with sid={}, pid={}'.format('FWrapper',sid, tag))
        _z2f,_f2z = self._newFID(self.z2fid, self.channels['f2z'], sid, tag)
        _p2f,_f2p = self._newFID(self.p2fid, self.channels['f2p'], sid, tag)
        _a2f,_f2a = self._newFID(self.a2fid, self.channels['f2a'], sid, tag)
        _w2f,_f2w = self._newFID(self.w2fid, self.channels['f2w'], sid, tag)
      
        f = cls(self.k, self.bits, self.crupt, sid, -1, {'f2p':_f2p, 'p2f':_p2f, 'f2a':_f2a, 'a2f':_a2f, 'f2z':_f2z, 'z2f':_z2f, 'f2w':_f2w, 'w2f':_w2f}, self.pump, self.poly, self.importargs)
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

    def wrapper_msg(self, m):
        print('wrapper message', m)
        (fro, ((sid, tag), msg)) = m.msg
        imp = m.imp
        fid = self.getFID(self.w2fid, sid, tag)
        fid.write( (fro, msg), imp )
