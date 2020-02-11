import dump
import gevent
from itm import ITMFunctionality
from comm import ishonest, isdishonest, isadversary, isf, isparty
from math import ceil
from queue import Queue as qqueue
from utils2 import print, gwrite, z_write, z_crupt
from hashlib import sha256
from collections import defaultdict
from gevent.queue import Queue, Channel

class SFE_Bracha_Functionality(object):
    def __init__(self, sid, pid, _f2p, _p2f, _f2a, _a2f, _f2z, _z2f):
        self.sid = sid
        self.ssid = self.sid[0]
        self.Rnd = self.sid[1]
        self.parties = self.sid[2]
        self.pid = pid
        
        self.f2p = _f2p; self.p2f = _p2f
        self.f2a = _f2a; self.a2f = _a2f
        self.f2z = _f2z; self.z2f = _z2f

        self.x = dict( (p,None) for p in self.parties )
        self.y = dict( (p,None) for p in self.parties )
        self.t = dict( (p,len(self.parties)) for p in self.parties )
        self.l = 1
        self.crupted = set()

    def input_input(self, pid, v):
        print('\033[1m[F_sfe]\033[0m someone called input with v:', v, pid)
        if pid != 1: dump.dump(); return  # ignore inputs not by dealer
        self.x[pid] = v
        self.f2a.write( ('input',pid, v) )

    def are_all_1(self):
        # TODO only care about `H` which is corrupt parties
        for i in self.t.values():
            if i != 1: return False
        return True
    def are_all_0(self):
        # TODO only care about `H` which is corrupt parties
        for i in self.t.values():
            if i != 0: return False
        return True

    def are_all_honest_0(self):
        for i in self.parties:
            if i not in self.crupted and self.t[i] != 0:
                return False
        return True

    def outputs_set(self):
        for i in self.y.values():
            if i is None:
                return False
        return True

    def input_output(self, pid):
        # TODO maintain internal corrupted set
        if pid == 1 and isdishonest(self.sid, pid) and self.x[pid] is None:
            dump.dump(); return

        # TODO change to > 0 is explained in latex
        #print('\t\033[1m OUTPUT call from: {} \t ti: {}, l: {}\033[0m'.format(pid, self.t[pid],self.l))
        if self.t[pid] > 0:
            self.t[pid] = self.t[pid]-1
            #if self.are_all_0() and self.l < self.Rnd:
            if self.are_all_honest_0() and self.l < self.Rnd:
                self.l += 1
                for i in self.t: self.t[i] = len(self.parties)
            self.f2a.write( ('activated',pid) )
        elif self.t[pid] == 0 and self.l < self.Rnd:
            #print('\n\t \033[1mOutput message\n\033[0m', pid)
            self.f2p.write( (pid, ('early',)) )
        else:
            # TODO only check that corrupt inputs have been set
            if self.x[1] is not None and not self.outputs_set():
                # TODO functionality needs to sample randomness
                o = self.x[1]
                for i in self.y: self.y[i] = o
            self.f2p.write( (pid, self.y[pid]) )

    def input_msg(self, sender, msg):
        sid,pid = sender
        if msg[0] == 'input' and pid in self.parties:
            self.input_input(pid, msg[1])
        elif msg[0] == 'output' and pid in self.parties:
            self.input_output(pid)
        else: dump.dump()
    
    def adv_corrupt(self, pid):
        self.crupted.add(pid)
        dump.dump()

    def adversary_msg(self, msg):
        if msg[0] == 'corrupted':
            self.adv_corrupt(msg[1])
        else: dump.dump()

    def run(self):
        while True:
            ready = gevent.wait(
                objects=[self.a2f,self.z2f,self.p2f],
                count=1
            )
            assert len(ready) == 1
            r = ready[0]
            if r == self.z2f:
                self.z2f.reset()
                dump.dump()
            elif r == self.p2f:
                msg = r.read()
                sender,msg = msg
                self.p2f.reset()
                self.input_msg(sender,msg)
            elif r == self.a2f:
                msg = r.read()
                self.a2f.reset()
                self.adversary_msg(msg)
            else: dump.dump()

from comm import GenChannel, setAdversary
from itm2 import FunctionalityWrapper, PartyWrapper, DummyAdversary, ProtocolWrapper2
from utils2 import z_inputs, z_ainputs, wait_for
from f_clock import Clock_Functionality
from f_bd_sec import BD_SEC_Functionality
from prot_bracha import Bracha_Protocol
class BrachaSimulator(object):
    def __init__(self, sid, pid, z2a, a2z, p2a, a2p, a2f, f2a):
        self.sid = sid
        self.ssid = self.sid[0]
        self.parties = self.sid[1]
        self.pid = pid
        self.sender = (sid,pid)
        self.z2a = z2a; self.a2z = a2z
        self.p2a = p2a; self.a2p = a2p
        self.f2a = f2a; self.a2f = a2f

        # launch simulation of the real world
        # channels for simulated world, simulator acts as environment
        self._f2p,self._p2f = GenChannel(),GenChannel()
        self._f2a,self._a2f = GenChannel(),GenChannel()
        self._f2z,self._z2f = GenChannel(),GenChannel()
        self._p2a,self._a2p = GenChannel(),GenChannel()
        self._p2z,self._z2p = GenChannel(),GenChannel()
        self._z2a,self._a2z = GenChannel(),GenChannel()

        # simulated functionalities
        f = FunctionalityWrapper(self._p2f,self._f2p, self._a2f,self._f2a, self._z2f,self._f2z)
        gevent.spawn(f.run)
        f.newcls('F_clock', Clock_Functionality)
        f.newcls('F_bd', BD_SEC_Functionality)

        # spawn dummy adversary
        advitm = DummyAdversary('adv', -1, self._z2a,self._a2z, self._p2a,self._a2p, self._a2f,self._f2a)
        gevent.spawn(advitm.run)

        # spawn parties from sid information on parties
        p = ProtocolWrapper2(self.sid, self._z2p,self._p2z, self._f2p,self._p2f, self._a2p,self._p2a, Bracha_Protocol)
        gevent.spawn(p.run)
        p.spawn(1); wait_for(self._a2z)
        p.spawn(2); wait_for(self._a2z)
        p.spawn(3); wait_for(self._a2z)

        # track activations of parties
        self.num_activations = [len(self.parties) for _ in range(len(self.parties))]

    def leak_input(self, _, pid, v):
        # send this input to the dealer
        leaderpid = 1
        self._z2p.write( (leaderpid, ('input',v)) )

    def leak_activation(self, _, pid):
        # Is this the first time, deliver messages to pid
        activationsleft = self.num_activations[pid-1]
        if activationsleft == len(self.parties):  # first one
            # send an output signal to the parties to do its job
            self._z2p.write( (pid, ('output',)) )
            # Party could respond with: [prot_bracha:170] self.p2z.write( ('early',) )
          

    def functionality_msg(self, msg):
        # Assumed to be F_sfe
        fro,msg = msg
        if msg[0] == 'input':
            self.leak_input(*msg)
        elif msg[0] == 'activated':
            self.leak_activation(*msg)
        else: dump.dump()

    # Skeleton sim that only forwards message to/from dummy adversary should work the same
    def run(self):
        while True:
            ready = gevent.wait(
                objects=[self.z2a, self.f2a, self.p2a, self._a2z, self._p2z],
                count=1
            )
            r = ready[0]
            if r == self.z2a:
                self.z2a.reset()
            elif r == self.f2a:
                m = self.f2a.read()
                self.f2a.reset()
                self.functionality_msg(m)
                ## Below: code to simply forward all to/from adversary
                #m = self.f2a.read()
                #self.f2a.reset()
                #self._f2a.write(m)
                #print('Got f2a message in Simulatore', m)
                #ready = gevent.wait(objects=[self._a2z],count=1)
                #r = ready[0]
                #_m = r.read()
                #self._a2z.reset()
                #print("Received respons from dummy adversary", _m)
                #self.a2z.write(_m)
            elif r == self.p2a:
                self.p2a.reset()
            elif r == self._a2z:
                m = self._a2z.read()
                self._a2z.reset()
                self.a2z.write( m )
            elif r == self._p2z:
                m = self._p2z.read()
                self._p2z.reset()
                print('\n p2z message', m)
                dump.dump()
            else: dump.dump()

def test_all_honest(): 
    sid = ('one', 4, (1,2,3))
    f2p,p2f = GenChannel('f2p'),GenChannel('p2f')
    f2a,a2f = GenChannel('f2a'),GenChannel('a2f')
    f2z,z2f = GenChannel('f2z'),GenChannel('z2f')
    p2a,a2p = GenChannel('p2a'),GenChannel('a2p')
    p2z,z2p = GenChannel('p2z'),GenChannel('z2p')
    z2a,a2z = GenChannel('z2a'),GenChannel('a2z')
    
    f = FunctionalityWrapper(p2f,f2p, a2f,f2a, z2f,f2z)
    gevent.spawn(f.run)
    f.newcls('F_sfe', SFE_Bracha_Functionality)

    #advitm = DummyAdversary('adv',-1, z2a,a2z, p2a,a2p, a2f,f2a)
    advitm = BrachaSimulator(('one',(1,2,3)),-1, z2a,a2z, p2a,a2p, a2f,f2a)
    setAdversary(advitm)
    gevent.spawn(advitm.run)

    p = PartyWrapper(sid, z2p, p2z, f2p, p2f, a2p, p2a, (sid, 'F_sfe'))
    gevent.spawn(p.run)

    p.spawn(1); wait_for(a2z)
    p.spawn(2); wait_for(a2z)
    p.spawn(3); wait_for(a2z)

    z2p.write( (1, ('input',3)) )
    wait_for(a2z)

    for _ in range(3):
        z2p.write( (1, ('output',)) )
        wait_for(a2z)
        z2p.write( (2, ('output',)) )
        wait_for(a2z)
        z2p.write( (3, ('output',)) )
        wait_for(a2z)

    for _ in range(3):
        z2p.write( (1, ('output',)) )
        fro,msg = wait_for(a2z)
        z2p.write( (2, ('output',)) )
        wait_for(a2z)
        z2p.write( (3, ('output',)) )
        wait_for(a2z)
    
    for _ in range(2):
        z2p.write( (1, ('output',)) )
        wait_for(a2z)
        z2p.write( (2, ('output',)) )
        fro,msg = wait_for(a2z)
        z2p.write( (3, ('output',)) )
        wait_for(a2z)
    
    z2p.write( (1, ('output',)) )
    wait_for(a2z)
    z2p.write( (1, ('output',)) )
    fro,msg= wait_for(p2z)
    assert msg[0] == 'early'
    z2p.write( (2, ('output',)) )
    wait_for(a2z)
    z2p.write( (3, ('output',)) )
    wait_for(a2z)
    
    for _ in range(3):
        z2p.write( (3, ('output',)) )
        wait_for(a2z)
        z2p.write( (1, ('output',)) )
        wait_for(a2z)
        z2p.write( (2, ('output',)) )
        wait_for(a2z)

    z2p.write( (1, ('output',)) )
    fro,msg = wait_for(p2z);
    print('P1 output', msg)
    z2p.write( (2, ('output',)) )
    fro,msg = wait_for(p2z)
    print('P2 output', msg)
    z2p.write( (3, ('output',)) )
    fro,msg = wait_for(p2z)
    print('P3 output', msg)

def test_crupt_dealer_no_accept():
    sid = ('one', 4, (1,2,3))
    f2p,p2f = GenChannel('f2p'),GenChannel('p2f')
    f2a,a2f = GenChannel('f2a'),GenChannel('a2f')
    f2z,z2f = GenChannel('f2z'),GenChannel('z2f')
    p2a,a2p = GenChannel('p2a'),GenChannel('a2p')
    p2z,z2p = GenChannel('p2z'),GenChannel('z2p')
    z2a,a2z = GenChannel('z2a'),GenChannel('a2z')
   
    z_crupt(sid, 1)

    f = FunctionalityWrapper(p2f,f2p, a2f,f2a, z2f,f2z)
    gevent.spawn(f.run)
    f.newcls('F_sfe', SFE_Bracha_Functionality)

    advitm = BrachaSimulator(('one',(1,2,3)),-1, z2a,a2z, p2a,a2p, a2f,f2a)
    setAdversary(advitm)
    gevent.spawn(advitm.run)

    p = PartyWrapper(sid, z2p, p2z, f2p, p2f, a2p, p2a, (sid, 'F_sfe'))
    gevent.spawn(p.run)

    p.spawn(1); wait_for(a2z)
    p.spawn(2); wait_for(a2z)
    p.spawn(3); wait_for(a2z)
    


# Testing the simulator by simulating messages from the functionality
def test_sim(): 
    sid = ('one', 4, (1,2,3))
    f2p,p2f = GenChannel('f2p'),GenChannel('p2f')
    f2a,a2f = GenChannel('f2a'),GenChannel('a2f')
    f2z,z2f = GenChannel('f2z'),GenChannel('z2f')
    p2a,a2p = GenChannel('p2a'),GenChannel('a2p')
    p2z,z2p = GenChannel('p2z'),GenChannel('z2p')
    z2a,a2z = GenChannel('z2a'),GenChannel('a2z')
    
    f = FunctionalityWrapper(p2f,f2p, a2f,f2a, z2f,f2z)
    gevent.spawn(f.run)
    f.newcls('F_sfe', SFE_Bracha_Functionality)

    #advitm = DummyAdversary('adv',-1, z2a,a2z, p2a,a2p, a2f,f2a)
    advitm = BrachaSimulator(('one',(1,2,3)),-1, z2a,a2z, p2a,a2p, a2f,f2a)
    setAdversary(advitm)
    gevent.spawn(advitm.run)

    p = PartyWrapper(sid, z2p, p2z, f2p, p2f, a2p, p2a, (sid, 'F_sfe'))
    gevent.spawn(p.run)

    p.spawn(1); wait_for(a2z)
    p.spawn(2); wait_for(a2z)
    p.spawn(3); wait_for(a2z)

    z2p.write( (1, ('input',3)) )
    wait_for(a2z)

    print('\n\n\n\n\n\n\n\n\n\n ***')

    f2a.write( ((sid,'F_sfe'),('input', 1, 3)) )
    wait_for(a2z)

    for _ in range(2):
        f2a.write( ((sid,'F_sfe'), ('activated', 1)) )
        fro,msg = wait_for(a2z)
        assert msg == (1, ('sent', ('VAL',3))), msg
    f2a.write( ((sid,'F_sfe'), ('activated', 1)) )
    fro,msg = wait_for(a2z)
    
    for _ in range(3):
        f2a.write( ((sid,'F_sfe'), ('activated', 2)) )
        wait_for(a2z)
        f2a.write( ((sid,'F_sfe'), ('activated', 3)) )
        wait_for(a2z)

    for _ in range(2):
        f2a.write( ((sid,'F_sfe'), ('activated', 1)) )
        fro,msg = wait_for(a2z)
        assert msg == (1, ('sent', ('ECHO',3))), msg
        f2a.write( ((sid,'F_sfe'), ('activated', 2)) )
        fro,msg = wait_for(a2z)
        assert msg == (2, ('sent', ('ECHO',3))), msg
        f2a.write( ((sid,'F_sfe'), ('activated', 3)) )
        fro,msg = wait_for(a2z)
        assert msg == (3, ('sent', ('ECHO',3)))
    f2a.write( ((sid,'F_sfe'), ('activated', 3)) )
    fro,msg = wait_for(a2z)
    assert msg == ('switch',3), msg
    f2a.write( ((sid,'F_sfe'), ('activated', 2)) )
    fro,msg = wait_for(a2z)
    assert msg == ('switch',2), msg
    f2a.write( ((sid,'F_sfe'), ('activated', 1)) )
    fro,msg = wait_for(a2z)
    assert msg == ('switch',1), msg

    for _ in range(2):
        f2a.write( ((sid,'F_sfe'), ('activated', 1)) )
        fro,msg = wait_for(a2z)
        assert msg == (1, ('sent', ('READY',3))), msg
        f2a.write( ((sid,'F_sfe'), ('activated', 2)) )
        fro,msg = wait_for(a2z)
        assert msg == (2, ('sent', ('READY',3))), msg
        f2a.write( ((sid,'F_sfe'), ('activated', 3)) )
        fro,msg = wait_for(a2z)
        assert msg == (3, ('sent', ('READY',3)))
    
    f2a.write( ((sid,'F_sfe'), ('activated', 3)) )
    fro,msg = wait_for(a2z)
    assert msg == ('switch',3), msg
    f2a.write( ((sid,'F_sfe'), ('activated', 2)) )
    fro,msg = wait_for(a2z)
    assert msg == ('switch',2), msg
    f2a.write( ((sid,'F_sfe'), ('activated', 1)) )
    fro,msg = wait_for(a2z)
    assert msg == ('switch',1), msg

    # TODO prot_bracha should only return after |P| activations
    # in the last, Rnd=4, round (output takes the place of 'early')
    for _ in range(1):
        f2a.write( ((sid,'F_sfe'), ('activated', 1)) )
        wait_for(a2z)
        f2a.write( ((sid,'F_sfe'), ('activated', 2)) )
        wait_for(a2z)
        f2a.write( ((sid,'F_sfe'), ('activated', 3)) )
        wait_for(a2z)
    

if __name__=='__main__':
    test_all_honest()
    #test_sim()
