from uc.itm import ITM, GenChannel
import logging
import gevent

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
        print('dummy party func msg: {}'.format(msg))
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
        self.prot = prot
        self.log = logging.getLogger('ProtocolWrapper')
        self.handlers = {
            channels['z2p'] : self.env_msg,
            channels['a2p'] : self.adv_msg,
            channels['f2p'] : self.func_msg,
        }
        ITM.__init__(self, k, bits, sid, None, channels, self.handlers, pump)

    def is_dishonest(self, pid):
        return pid in self.crupt

    def is_honest(self, sid, pid):
        return not self.is_dishonest(pid)

    def _newPID(self, pid, _2pid, p2_, tag):
        pp2_ = GenChannel(('write-translate-{}'.format(tag),self.sid,pid)) 
        _2pp = GenChannel(('read-{}'.format(tag),self.sid,pid)) 

        def _translate():
           while True:
                r = gevent.wait(objects=[pp2_],count=1)
                msg = r[0].read()
                pp2_.reset()
                p2_.write( (pid, msg) )
        gevent.spawn(_translate)

        _2pid[self.sid,pid] = _2pp
        return (_2pp, pp2_) 

    def newPID(self, pid):
        print('\033[1m[{}]\033[0m Creating new party with pid: {}'.format('PWrapper', pid))
        _z2p,_p2z = self._newPID(pid, self.z2pid, self.channels['p2z'], 'p2z')
        _f2p,_p2f = self._newPID(pid, self.f2pid, self.channels['p2f'], 'p2f')
        _a2p,_p2a = self._newPID(pid, self.a2pid, self.channels['p2a'], 'p2a')
        
        p = self.prot(self.k, self.bits, self.sid, pid, {'a2p':_a2p,'p2a':_p2a, 'z2p':_z2p,'p2z':_p2z, 'f2p':_f2p, 'p2f':_p2f}, self.pump)
        gevent.spawn(p.run)

    def getPID(self, _2pid, pid):
        if (self.sid,pid) in _2pid: return _2pid[self.sid,pid]
        else:
            self.newPID(pid)
            return _2pid[self.sid,pid]

    def env_msg(self, msg):
        pid,msg = msg
        print('new env msg {} to {}'.format(msg, pid))
        if self.is_dishonest(pid): raise Exception("Environment writing to corrupt party")
        _pid = self.getPID(self.z2pid,pid)
        _pid.write(msg)
    
    def func_msg(self, msg):        
        topid, msg = msg
        print('fun msg {} to {}'.format(msg, topid))
        if self.is_dishonest(topid):
            self.write('p2a', (topid, msg))
        else:
            _pid = self.getPID(self.f2pid, topid)
            _pid.write( msg)

    def adv_msg(self, msg):
        pid, msg = msg
        if self.is_honest(self.sid, pid): raise Exception("adv writing to an honest party: {}. Cruptset: {}".format((self.sid,pid), self.crupt))
        self.write( 'p2f', (pid, msg))
