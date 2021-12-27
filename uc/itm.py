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

# Generic message containin some messafe data msg.msg and 
#class MSG:
#    def __init__(self, msg, imp=1):
#        self.msg = msg
#        self.imp = imp
#    def __repr__(self):
#        return 'MSG:' + str((self.msg,self.imp))

class GenChannel(Event):
    def __init__(self, i=-1):
        Event.__init__(self)
        self._data = None
        self.id = i

    def write(self, data):
        if not self.is_set():
            self._data = data; self.set() 
        else: 
            raise Exception("\033[1mwriting to channel already full with {}. Writing {} in {}\033[0m".format(self._data,data,self.i))

    def __str__(self):
        return "Channel id:{}".format(self.id)

    def read(self): 
        return self._data
    def reset(self, s=''): 
        self.clear()

#class ITMContext:
#    def __init__(self, poly):
#        self.imp_in = 0
#        self.imp_out = 0
#        self.spent = 0
#        self.marked = 0
#        self.poly = poly
#    
#    def tick(self, poly, n):
#        if self.poly(self.marked) < self.spent + n:
#            self.generate_pot(1)
#        self.spent += 1
#
#    def generate_pot(self, n):
#        if self.imp_in - self.imp_out - self.marked >= n:
#            self.marked += n
#        else:
#            raise Exception("Can't mark any more tokens, you're out!")

class ITM:
    #def __init__(self, k, bits, sid, pid, channels, handlers, poly, pump, importargs):
    def __init__(self, k, bits, sid, pid, channels, handlers, pump):
        self.k = k
        self.bits = bits
        self.sid = sid
        self.pid = pid
        self.pump = pump
        self.channels = channels
        self.handlers = handlers

        self.log = logging.getLogger(type(self).__name__)

    def wrapwrite(self, msg):
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

#class GUCProtocol(UCProtocol):
#    def __init__(self, k, bits, sid, pid, channels, poly, pump, importargs):
#        #self.handlers = {
#        #    channels['z2p'] : self.env_msg,
#        #    channels['f2p'] : self.func_msg,
#        #    channels['a2p'] : self.adv_msg,
#        #    channels['w2p'] : self.wrapper_msg,
#        #}
#        #ITM.__init__(self, k, bits, sid, pid, channels, self.handlers, poly, pump, importargs)
#        #self.env_msgs = {}
#        #self.adv_msgs = {}
#        #self.func_msgs = {}
#        UCProtocol.__init__(self, k, buts, sid, pid, channels, poly, pump, importargs)
#        self.gf = lambda x: x[0]
#        self.gparse = lambda x: x[1:]
#        self.handlers[channels['g2p']] = self.gfunc_msg
#        self.gfunc_msgs = {}
#
#    #def adv_msg(self, msg):
#    #    Exception("adv_msg needs to be defined")
#
#    def gfunc_msg(self, m):
#        msg = m.msg
#        imp = m.imp
#        sender,msg = msg
#        if self.gf(msg) in self.gfunc_msgs:
#            self.gfunc_msgs[self.gf(msg)](sender, *(self.gparse(msg)))
#        else:
#            self.pump.write('')
#
#    def func_msg(self, m):
#        msg = m.msg
#        imp = m.imp
#        sender,msg = msg
#        if msg[0] in self.func_msgs:
#            self.func_msgs[msg[0]](sender, *msg[1:])
#        else:
#            self.pump.write('')
#
#    #def env_msg(self, msg):
#    #    Exception("env_msg needs to be defined")
#
#    #def wrapper_msg(self, msg):
#    #   Exception("wrapper_msg needs to be defined")
#
#    #def leak(self, msg):
#    #    Exception("leak needs to be defined")
#    
#    #def clock_round(self):
#    #    m = self.write_and_wait_for(
#    #        ch='p2w', msg=((self.sid, 'F_Wrapper'), ('clock-round',)),
#    #        imp=0, read='w2p'
#    #    )
#    #    return m.msg[1]

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

#class GUCAdversary(UCAdversary):
#    def __init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs, gsid, ssids):
#        UCAdversary.__init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs)
#        self.handlers[ channels['g2a'] ] = self.gfunc_msg
#        self.gsid = gsid
#        self.ssids = ssids
#        self.gfunc_msgs = {}
#        self.gf = lambda x: x[0]
#        self.gfparse = lambda x: x[1:]
#
#    def func_msg(self, d):
#        msg = d.msg
#        imp = d.imp
#        sender,msg = msg
#        if self.f(msg) in self.func_msgs:
#            self.func_msgs[self.f(msg)](imp, sender, *self.fparse(msg))
#        else:
#            self.pump.write('')
#
#    def gfunc_msg(self, d):
#        msg = d.msg
#        imp = d.imp
#        sender, msg = msg
#        if self.gf(msg) in self.gfunc_msgs:
#            self.gfunc_msgs[self.gf(msg)](imp, sender, *self.gfparse(msg))
#        else:
#            self.pump.write('')
#
#    def env_msg(self, d):
#        if d.msg == ('',):
#            print('Just giving me import')
#            self.pump.write('')
#        else:
#            t,msg = d.msg
#            if t is 'A2F' and msg[0] in self.a2f_msgs:
#                self.a2f_msgs[msg[0]](*msg[1:])
#            elif t is 'A2P' and msg[1][0] in self.a2p_msgs:
#                self.a2p_msgs[msg[1][0]](msg[0], msg[1][1:])
#            elif t is 'A2G' and msg[1][0] in self.a2p_msgs:
#                self.a2g_msgs[msg[1][0]](msg[0], msg[1][1:])
#            elif t in self.env_msgs:
#                print('Fallback adversary msg')
#                self.env_msgs[t](msg, d.imp)
#            else:
#                raise Exception('Message {} not handled by adversary'.format(msg[1][0]))
#                self.pump.write('')

#def ideal_party(tof):
#    def _f(k, bits, sid, pid, channels, poly, pump, importargs):
#        return DummyParty(k, bits, sid, pid, channels, poly, pump, importargs, tof)
#    return _f

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

#class GUCDummyParty(ITM):
#    def __init__(self, k, bits, sid, pid, channels, poly, pump, importargs, gsid, ssids):
#        self.handlers = {
#            channels['z2p'] : self.env_msg,
#            channels['a2p'] : self.adv_msg,
#            channels['f2p'] : self.func_msg,
#            channels['g2p'] : self.wrapper_msg
#        }
#        ITM.__init__(self, k, bits, sid, pid, channels, self.handlers, poly, pump, importargs)
#        self.gsid = gsid
#        self.ssids = ssids
#
#    def adv_msg(self, d):
#        raise Exception("Adv can't write to an honest party")
#
#    def env_msg(self, d):
#        self.write('p2f', d.msg, d.imp)
#
#    def func_msg(self, d):
#        fro,msg = d.msg
#        self.write('p2z', msg, d.imp)
#
#    def wrapper_msg(self, d):
#        self.write('p2z', d.msg, d.imp)

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
                pp2_.reset('pp2_ translate reset')
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


#def gucProtocolWrapper(prot):
#    def f(k, bits, crupt, sid, channels, pump, poly, importargs, gsid, ssids):
#        return GUCProtocolWrapper(k, bits, crupt, sid, channels, pump, prot, poly, importargs, gsid, ssids)
#    return f
#
#class GUCProtocolWrapper(ProtocolWrapper):
#    def __init__(self, k, bits, crupt, sid, channels, pump, prot, poly, importargs, gsid, ssids):
#        ProtocolWrapper.__init__(self, k, bits, crupt, sid, channels, pump, prot, poly, importargs)
#        self.gsid = gsid
#        self.ssids = ssids
#        self.g2pid = {}
#        self.log = logging.getLogger('WrappedProtocolWrapper')
#        print('Wrapped protocol wrapper crupt', crupt)
#        self.handlers[channels['g2p']] = self.gfunc_msg
#
#
#    def newPID(self, sid, pid):
#        self.log.debug('\033[1m[WrappedProtocol {}]\033[0m Creating new party with pid: {}'.format('PWrapper', pid))
#        _z2p,_p2z = self._newPID(sid, pid, self.z2pid, self.channels['p2z'], 'p2z')
#        _f2p,_p2f = self._newPID(sid, pid, self.f2pid, self.channels['p2f'], 'p2f')
#        _a2p,_p2a = self._newPID(sid, pid, self.a2pid, self.channels['p2a'], 'p2a')
#        _g2p,_p2g = self._newPID(sid, pid, self.g2pid, self.channels['p2g'], 'p2g')
#       
#        p = self.prot(self.k, self.bits, self.sid, pid, {'p2f':_p2f, 'f2p':_f2p, 'p2a':_p2a, 'a2p':_a2p, 'p2z':_p2z, 'z2p':_z2p, 'p2g':_p2g, 'g2p':_g2p}, self.pump, self.poly, self.importargs, self.gsid, self.ssids)
#        gevent.spawn(p.run)
#
#    def getPID(self, _2pid, sid, pid):
#        if (sid,pid) in _2pid: return _2pid[sid,pid]
#        else:
#            assert sid == self.sid
#            self.newPID(sid,pid)
#            return _2pid[sid,pid]
#    
#    def adv_msg(self, d):
#        msg = d.msg
#        imp = d.imp
#        (sid,pid), msg = msg
#        if self.is_honest(sid,pid): raise Exception("adv writing to an honest party: {}, Cruptset: {}".format((sid,pid), self.crupt))
#        tag,msg = msg
#        if tag == 'P2G':
#            self.write('p2g', ((sid,pid), msg), imp)
#        elif tag == 'P2F':
#            self.write('p2f', ((sid,pid), msg), imp)
#        else:
#            raise Exception("No such tag over a2p: {}".format(tag))
#
#    def gfunc_msg(self, d):
#        msg = d.msg
#        imp = d.imp
#        (sid, pid), msg = msg
#        if self.is_dishonest(sid,pid):
#            self.write('p2a', ((sid,pid), msg), 0)
#        else:
#            _pid = self.getPID(self.w2pid, sid, pid)
#            _pid.write(msg, imp)
#
#
#class GUCGlobalFunctionality(ITM):
#    def __init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs):
#        self.crupt = crupt
#        self.handlers = {
#            channels['p2g'] : self.party_msg,
#            channels['a2g'] : self.adv_msg,
#            channels['z2g'] : self.env_msg,
#            channels['f2g'] : self.func_msg
#        }
#        ITM.__init__(self, k, bits, sid, pid, channels, self.handlers, poly, pump, importargs)
#        
#        self.party_msgs = {}
#        self.adv_msgs = {}
#        self.env_msgs = {}
#        self.func_msgs = {}
#
#        self.f = lambda x: x[0]
#        self.fparse = lambda x: x[1:]
#        self._start = True
#   
#    def on_init(self):
#        pass
#
#    def is_honest(self, sid, pid):
#        return (sid,pid) not in self.crupt
#
#    def wrapwrite(self, msg):
#        return (self.sid, msg)
#
#    def adv_msg(self, m):
#        if self._start: 
#            self.on_init()
#            self._start = False
#        to,msg = m.msg
#        if msg[0] in self.adv_msgs:
#            print('adv msg')
#            self.adv_msgs[msg[0]](m.imp, *msg[1:])
#        else:
#            print('sid:', self.sid)
#            print('adv_msgs:', self.adv_msgs)
#            raise Exception("No such message: {}".format(msg[0]))
#            self.pump.write('')
#
#    def party_msg(self, m):
#        if self._start: 
#            self.on_init()
#            self._start = False
#        sender, (to, msg) = m.msg
#        if msg[0] in self.party_msgs:
#            self.party_msgs[msg[0]](m.imp, sender, *msg[1:])
#        else:
#            raise Exception('unknown message', msg)
#            self.pump.write('')
#
#    def env_msg(self, m):
#        if self._start: 
#            self.on_init()
#            self._start = False
#        to,msg = m.msg
#        imp = m.imp
#        if msg[0] in self.env_msgs:
#            self.env_msgs[msg[0]](imp, *msg[1:])
#        else:
#            raise Exception('unknown message={} with type={}'.format(msg, msg[0]))
#            self.pump.write('')
#
#    def func_msg(self, m):
#        if self._start:
#            self.on_init()
#            self._start = False
#        msg = m.msg
#        imp = m.msg
#        sender,(to, msg) = msg
#        if self.f(msg) in self.func_msgs:
#            self.func_msgs[self.f(msg)](imp, sender, *self.fparse(msg))
#        else:
#            raise Exception('unknown message', self.f(msg))
#            self.pump.write('')
#
#class GUCWrappedGlobalFunctionality(GUCGlobalFunctionality):
#    def __init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs, _ssids):
#        GUCGlobalFunctionality.__init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs)
#        self.handlers[ channels['ssid2g'] ] = self.ssid2g_msg
#        self.ssid2g_msgs = {}
#        self._ssids = _ssids
#
#    def ssid2g_msg(self, d):
#        msg = d.msg
#        imp = d.imp
#        frosid, msg = msg
#        if msg[0] in self.ssid2g_msgs:
#            self.ssid2g_msgs[msg[0]](imp, frosid, *msg[1:])
#        else:
#            raise Exception('Unknown msg', msg)
#
#
#def DuplexWrapper(f1, f1tag, f2, f2tag):
#    def f(k, bits, crupt, sid, channels, pump, poly, importargs):
#        return GlobalFunctionalityWrapper(k, bits, crupt, sid, channels, pump, poly, importargs, [f1, f2], [f1tag, f2tag])
#    return f
#
#def GlobalFWrapper( _fs, _ftags ):
#    def f(k, bits, crupt, sid, channels, pump, poly, importargs):
#        return GlobalFunctionalityWrapper(k, bits, crupt, sid, channels, pump, poly, importargs, _fs, _ftags)
#    return f
#
#def duplexGUCWrapper(f1, f2):
#    def f(k, bits, crupt, sid, pid, channels, poly, pump, importargs, ssids):
#        return GUCGlobalFunctionalityWrapper(k, bits, crupt, sid, pid, channels, poly, pump, importargs, [f1,f2], ssids)
#    return f
#
#class GUCGlobalFunctionalityWrapper(GUCGlobalFunctionality):
#    def __init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs, gs, ssids):
#        GUCGlobalFunctionality.__init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs)
#        self.z2gid = {}
#        self.p2gid = {}
#        self.f2gid = {}
#        self.a2gid = {}
#        self.ssid2gid = {}
#        self.ssids = ssids 
#        self.gs = gs
#
#        self.channels['g2ssid'] = GenChannel('g2ssid')
#
#        #self.handlers[ channels['ssid2g'] ] = self.ssid2g_msg # global F receiving from another ssid
#        self.handlers[ self.channels['g2ssid'] ] = self.g2ssid_msg # global F sending to another ssid
#        
#        for s,g in zip(ssids, gs):
#            self.newFID(s, g)
#
#    def _newFID(self, _2fid, real_f2outside, sid):
#        #ff2_ = GenChannel(('write-translate',sid))
#        internal_f2outside = GenChannel(('write-translate',sid))
#        #_2ff = GenChannel(('read',sid))
#        internal_outside2f = GenChannel(('read',sid))
#
#        def _translate():
#            while True:
#                r = gevent.wait(objects=[internal_f2outside],count=1)
#                m = r[0].read()
#                internal_f2outside.reset()
#                #real_f2outside.write( (sid, m.msg), m.imp )
#                real_f2outside.write( m.msg, m.imp )
#        gevent.spawn(_translate) 
#        _2fid[sid] = internal_outside2f
#        return (internal_outside2f, internal_f2outside) 
#    
#    def newFID(self, ssid, cls):
#        _z2g,_g2z = self._newFID(self.z2gid, self.channels['g2z'], ssid)
#        _p2g,_g2p = self._newFID(self.p2gid, self.channels['g2p'], ssid)
#        _a2g,_g2a = self._newFID(self.a2gid, self.channels['g2a'], ssid)
#        _f2g,_g2f = self._newFID(self.f2gid, self.channels['g2f'], ssid)
#        _ssid2g,_g2ssid = self._newFID(self.ssid2gid, self.channels['g2ssid'], ssid)
#
#        chset = {'p2g':_p2g, 'g2p':_g2p, 'z2g':_z2g, 'g2z':_g2z, 'f2g':_f2g, 'g2f':_g2f, 'a2g':_a2g, 'g2a':_g2a, 'g2ssid':_g2ssid, 'ssid2g':_ssid2g}
#
#        f = cls(self.k, self.bits, self.crupt, ssid, -1, chset, self.poly, self.pump, self.importargs, self.ssids)
#        gevent.spawn(f.run)
#
#    def getFID(self, ssid, _2gid):
#        return _2gid[ssid]
#    
#    def party_msg(self, d): 
#        msg = d.msg
#        imp = d.imp
#        fro,(to, (ssid,msg)) = msg
#        sid,pid = fro
#        self.p2gid[ssid].write( (fro, msg), imp )
#
#    def func_msg(self, d):
#        msg = d.msg 
#        imp = d.imp
#        fro,(to, (ssid,msg)) = msg
#        self.f2gid[ssid].write( (fro, (ssid, msg)), imp )
#
#    def g2ssid_msg(self, d):
#        msg = d.msg
#        imp = d.imp
#        fro, (ssid, msg) = msg
#        print('g2ssid_msg="{}", fro="{}", ssid="{}"'.format(msg, fro, ssid))
#        self.ssid2gid[ssid].write( (fro, msg), imp )
#
#    def adv_msg(self, d):
#        msg = d.msg
#        imp = d.imp
#        to,(ssid,msg) = msg
#        self.a2gid[ssid].write( (ssid, msg), imp)
#
#    def env_msg(self, d):
#        msg = d.msg
#        imp = d.imp
#        to,(ssid,msg) = msg
#        self.z2gid[ssid].write( (ssid, msg), imp ) 

#class GlobalFunctionalityWrapper(ITM):
#    def __init__(self, k, bits, crupt, sid, channels, pump, poly, importargs, _fs, _ftags):
#        self.z2wid = {}
#        self.p2wid = {}
#        self.a2wid = {}
#        self.f2wid = {}
#        self._2wid = {}
#        self.crupt = crupt
#        
#        self.handlers = {
#            channels['p2w'] : self.party_msg,
#            channels['a2w'] : self.adv_msg,
#            channels['z2w'] : self.env_msg,
#            channels['f2w'] : self.func_msg,
#            #channels['w2_'] : self.wrapper_msg,
#        }
#        ITM.__init__(self, k, bits, sid, None, channels, self.handlers, poly, pump, importargs)
#        
#        self.channels['w2_'] = GenChannel('w2_')
#        self.handlers[self.channels['w2_']] = self._2w_msg
#
#        for _f_, _ftag_ in zip(_fs, _ftags):
#            self.newFID(self.sid, _ftag_, _f_)
#
#    def _newFID(self, _2fid, f2_, sid, tag):
#        ff2_ = GenChannel(('write-translate',sid,tag))
#        _2ff = GenChannel(('read',sid,tag))
#
#        def _translate():
#            while True:
#                r = gevent.wait(objects=[ff2_],count=1)
#                m = r[0].read()
#                ff2_.reset()
#                f2_.write( ((sid,tag), m.msg), m.imp )
#        gevent.spawn(_translate) 
#        _2fid[sid,tag] = _2ff
#        return (_2ff, ff2_) 
#    
#    def getFID(self, _2pid, sid,tag):
#        return _2pid[sid,tag]
#    
#    def newFID(self, sid, tag, cls):
#        _z2w,_w2z = self._newFID(self.z2wid, self.channels['w2z'], sid, tag)
#        _p2w,_w2p = self._newFID(self.p2wid, self.channels['w2p'], sid, tag)
#        _a2w,_w2a = self._newFID(self.a2wid, self.channels['w2a'], sid, tag)
#        _f2w,_w2f = self._newFID(self.f2wid, self.channels['w2f'], sid, tag)
#        __2w,_w2_ = self._newFID(self._2wid, self.channels['w2_'], sid, tag)
#
#        f = cls(self.k, self.bits, self.crupt, self.sid, tag, {'p2w':_p2w, 'w2p':_w2p, 'z2w':_z2w, 'w2z':_w2z, 'f2w':_f2w, 'w2f':_w2f, 'a2w':_a2w, 'w2a':_w2a, 'w2_':_w2_, '_2w':__2w}, self.pump, self.poly, self.importargs)
#        gevent.spawn(f.run)
#
#    def party_msg(self, m):
#        fro, ((sid, tag), msg) = m.msg
#        imp = m.imp
#        fid = self.getFID( self.p2wid, sid, tag)
#        fid.write( (fro, msg), imp )
#
#    def adv_msg(self, m):
#        (sid,tag),msg = m.msg
#        imp = m.imp
#        fid = self.getFID(self.a2wid, sid, tag)
#        fid.write( msg,imp )
#
#    def env_msg(self, m):
#        (sid,tag), msg = m.msg
#        imp = m.imp
#        fid = self.getFID(self.z2wid, sid, tag)
#        fid.write( msg, imp )
#
#    def func_msg(self, m):
#        fro, ((sid,tag), msg) = m.msg
#        imp = m.imp
#        fid = self.getFID(self.f2wid, sid, tag)
#        fid.write( (fro, msg), imp )
#
#    def _2w_msg(self, m):
#        fro, ((sid,tag), msg) = m.msg
#        imp = m.imp
#        fid = self.getFID(self._2wid, sid, tag)
#        fid.write( (fro, msg), imp )
