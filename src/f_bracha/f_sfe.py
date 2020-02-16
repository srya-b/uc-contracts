import dump
import gevent
from itm import ITMFunctionality
from itm2 import ITMSyncFunctionality
from comm import ishonest, isdishonest, isadversary, isf, isparty
from math import ceil
from queue import Queue as qqueue
from utils2 import print, gwrite, z_write, z_crupt
from hashlib import sha256
from collections import defaultdict
from gevent.queue import Queue, Channel

#class SFE_Bracha_Functionality(object):
class SFE_Bracha_Functionality(ITMSyncFunctionality):
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
        
        self.channels = [self.a2f, self.z2f, self.p2f]
        self.handlers = {
            self.a2f: self.adversary_msg,
            self.p2f: self.input_msg,
            self.z2f: lambda x: dump.dump()
        }
        
        ITMSyncFunctionality.__init__(self, self.sid, self.channels, self.handlers)

    def input_input(self, pid, v):
        print('\033[1m[F_sfe]\033[0m someone called input with v:', v, pid)
        if pid != 1: dump.dump(); return  # ignore inputs not by dealer
        self.x[pid] = v
        self.f2a.write( ('input',pid, v) )

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
        if pid == 1 and isdishonest(self.sid, pid) and self.x[pid] is None:
            dump.dump(); return

        if self.t[pid] > 0:
            self.t[pid] = self.t[pid]-1
            if self.are_all_honest_0() and self.l < self.Rnd:
                self.l += 1
                for i in self.t: self.t[i] = len(self.parties)
            self.f2a.write( ('activated',pid) )
        elif self.t[pid] == 0 and self.l < self.Rnd:
            self.f2p.write( (pid, ('early',)) )
        else:
            # TODO only check that corrupt inputs have been set
            if self.x[1] is not None and not self.outputs_set():
                # TODO functionality needs to sample randomness
                o = self.x[1]
                for i in self.y: self.y[i] = o
            self.f2p.write( (pid, self.y[pid]) )

    def input_msg(self, msg):
        sender,msg = msg
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
        if msg[0] == 'corrupt':
            self.adv_corrupt(msg[1])
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
        # ignore sid[1] which is Rnd
        self.parties = self.sid[2]
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
        advitm = DummyAdversary(self.sid, -1, self._z2a,self._a2z, self._p2a,self._a2p, self._a2f,self._f2a)
        gevent.spawn(advitm.run)

        # spawn parties from sid information on parties
        p = ProtocolWrapper2(self.sid, self._z2p,self._p2z, self._f2p,self._p2f, self._a2p,self._p2a, Bracha_Protocol)
        gevent.spawn(p.run)
        for x in self.parties:
            p.spawn(x); wait_for(self._a2z)
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

    def input_corrupt(self, pid):
        self._z2a.write( ('corrupt',pid) )
        m = wait_for(self._a2z) # F_clock gives on output
        assert m[1] == ('OK',)
        #dump.dump_wait()
        # Now we write to F_sfe2f
        self.a2f.write( ((self.sid, 'F_sfe'), ('corrupt',pid)) )

    def input_corrupt_leader(self, msg):
        # TODO assumption about katz:
        #   Assumption is that a party can change their input in F_sfe
        #   before the function f is computed. This means that when
        #   the simulator receives the first VAL message from corrupt
        #   dealer, it sends the input to F_sfe, but waits to see 
        #   if dealer sends VAL to enough players, if not set the input
        #   of the dealer in F_sfe to \bot because in the real world
        #   the party's would not reach consensus on the input and 
        #   instead commit to \bot.
        pass

    def input_msg(self, msg):
        print('\n\n sim message', msg)
        if msg[0] == 'corrupt':
            self.input_corrupt(msg[1])
        #elif msg[0] == 'A2P':
        #    _,msg = msg
        #    if msg[0] == 1:     # message is for corrupt dealer
        #        self.input_corrupt_leader(msg)
        #    else:
        #        print('z2a write', msg)
        #        self._z2a.write(msg)
        else: self._z2a.write(msg)#dummp.dump()

    # Skeleton sim that only forwards message to/from dummy adversary should work the same
    def run(self):
        while True:
            ready = gevent.wait(
                objects=[self.z2a, self.f2a, self.p2a, self._a2z, self._p2z],
                count=1
            )
            r = ready[0]
            if r == self.z2a:
                m = self.z2a.read()
                self.z2a.reset()
                self.input_msg( m )
                #self._z2a.write( m )
            elif r == self.f2a:
                m = self.f2a.read()
                self.f2a.reset()
                self.functionality_msg(m)
            elif r == self.p2a:
                self.p2a.reset()
                dump.dump()
            elif r == self._a2z:
                m = self._a2z.read()
                self._a2z.reset()
                self.a2z.write( m )
            elif r == self._p2z:
                m = self._p2z.read()
                self._p2z.reset()
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

def test_one_crupt_party():
    sid = ('one', 4, (1,2,3,4))
    f2p,p2f = GenChannel('f2p'),GenChannel('p2f')
    f2a,a2f = GenChannel('f2a'),GenChannel('a2f')
    f2z,z2f = GenChannel('f2z'),GenChannel('z2f')
    p2a,a2p = GenChannel('p2a'),GenChannel('a2p')
    p2z,z2p = GenChannel('p2z'),GenChannel('z2p')
    z2a,a2z = GenChannel('z2a'),GenChannel('a2z')
   
    z_crupt(sid, 4)

    f = FunctionalityWrapper(p2f,f2p, a2f,f2a, z2f,f2z)
    gevent.spawn(f.run)
    f.newcls('F_sfe', SFE_Bracha_Functionality)

    advitm = BrachaSimulator(sid,-1, z2a,a2z, p2a,a2p, a2f,f2a)
    setAdversary(advitm)
    gevent.spawn(advitm.run)

    p = PartyWrapper(sid, z2p, p2z, f2p, p2f, a2p, p2a, (sid, 'F_sfe'))
    gevent.spawn(p.run)

    z2a.write( ('corrupt',4) )
    wait_for(a2z)

    p.spawn(1); wait_for(a2z)
    p.spawn(2); wait_for(a2z)
    p.spawn(3); wait_for(a2z)
    p.spawn(4); wait_for(a2z)
   
    z2p.write( (1, ('input',3)) )
    m = wait_for(a2z)

    #z2a.write( ('A2P', (4, ( ((sid, 'F_clock'), ('RoundOK',))))) )
    #wait_for(a2z)

    for _ in range(4):
        z2p.write( (1, ('output',)) )
        wait_for(a2z)
        z2p.write( (2, ('output',)) )
        wait_for(a2z)
        z2p.write( (3, ('output',)) )
        wait_for(a2z)

    for _ in range(4):
        z2p.write( (1, ('output',)) )
        fro,msg = wait_for(a2z)
        z2p.write( (2, ('output',)) )
        wait_for(a2z)
        z2p.write( (3, ('output',)) )
        wait_for(a2z)
    
    for _ in range(4):
        z2p.write( (1, ('output',)) )
        fro,msg = wait_for(a2z)
        z2p.write( (2, ('output',)) )
        wait_for(a2z)
        z2p.write( (3, ('output',)) )
        wait_for(a2z)
    
    for _ in range(4):
        z2p.write( (1, ('output',)) )
        wait_for(a2z)
        z2p.write( (2, ('output',)) )
        wait_for(a2z)
        z2p.write( (3, ('output',)) )
        wait_for(a2z)
    
    z2p.write( (1, ('output',)) )
    fro,m = wait_for(p2z)
    print('P1 output:', m)
    z2p.write( (2, ('output',)) )
    fro,m = wait_for(p2z)
    print('P2 output;', m)
    z2p.write( (3, ('output',)) )
    fro,m = wait_for(p2z)
    print('P3 output:', m)


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
    #test_all_honest()
    #test_sim()
    test_one_crupt_party()
