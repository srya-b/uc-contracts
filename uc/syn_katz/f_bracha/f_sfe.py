import dump
import gevent
from syn_katz import ITMKatzSFE
from comm import ishonest, isdishonest, isadversary, isf, isparty
from math import ceil
from queue import Queue as qqueue
from utils import print, gwrite, z_write, z_crupt
from hashlib import sha256
from collections import defaultdict
from gevent.queue import Queue, Channel

class SFE_Bracha_Functionality(ITMKatzSFE):
    def __init__(self, sid, pid, _f2p, _p2f, _f2a, _a2f, _f2z, _z2f):
        self.channels = {'a2f':_a2f, 'f2a':_f2a,'z2f':_z2f, 'f2z':_f2z, 'p2f':_p2f, 'f2p':_f2p}
        self.handlers = {
            _a2f: self.adversary_msg,
            _p2f: self.input_msg,
            _z2f: lambda x: dump.dump()
        }
        ITMKatzSFE.__init__(self, sid, pid, self.channels, self.handlers)

        # Bracha only cares about honest dealer's input
        for p in self.parties:
            if p != 1:  # skip the dealer
                self.x[p] = 'bot'
    
    # Require to be implemented by base class ITMSyncFunctionality
    def function(self):
        return dict( (p,self.x[1]) for p in self.parties)

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

from comm import setAdversary
from itm import FunctionalityWrapper, PartyWrapper, ProtocolWrapper, GenChannel
from syn_katz import KatzDummyAdversary, Clock_Functionality, BD_SEC_Functionality
from utils import z_inputs, z_ainputs, wait_for
from prot_bracha import Bracha_Protocol
from execuc import createUC

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

        ## launch simulation of the real world
        ## channels for simulated world, simulator acts as environment
        _f2p,_p2f,_f2a,_a2f,_f2z,_z2f,_p2a,_a2p,_p2z,_z2p,_z2a,_a2z,_static = createUC( [('F_clock',Clock_Functionality),('F_bd',BD_SEC_Functionality)], ProtocolWrapper, Bracha_Protocol, KatzDummyAdversary)
        self._f2p,self._p2f = _f2p,_p2f
        self._f2a,self._a2f = _f2a,_a2f
        self._f2z,self._z2f = _f2z,_z2f
        self._p2a,self._a2p = _p2a,_a2p
        self._p2z,self._z2p = _p2z,_z2p
        self._z2a,self._a2z = _z2a,_a2z
        self._static = _static

        self._static.write( ('sid',self.sid) )

        for x in self.parties:
            self._z2p.write( ((self.sid,x), ('sync',)) )
            wait_for(self._a2z)

        self.num_activations = [len(self.parties) for _ in range(len(self.parties))]

    def leak_input(self, _, pid, v):
        # send this input to the dealer
        leaderpid = 1
        self._z2p.write( ((self.sid,leaderpid), ('input',v)) )

    def leak_activation(self, _, pid):
        # Is this the first time, deliver messages to pid
        activationsleft = self.num_activations[pid-1]
        if activationsleft == len(self.parties):  # first one
            # send an output signal to the parties to do its job
            self._z2p.write( ((self.sid,pid), ('output',)) )
            # Party could respond with: [prot_bracha:170] self.p2z.write( ('early',) )
          

    def func_msg(self, msg):
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

    def env_msg(self, msg):
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
                self.env_msg( m )
                #self._z2a.write( m )
            elif r == self.f2a:
                m = self.f2a.read()
                self.f2a.reset()
                self.func_msg(m)
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
    advitm = BrachaSimulator(sid,-1, z2a,a2z, p2a,a2p, a2f,f2a)
    setAdversary(advitm)
    gevent.spawn(advitm.run)

    p = PartyWrapper(z2p, p2z, f2p, p2f, a2p, p2a, 'F_sfe')
    gevent.spawn(p.run)

    p.spawn(sid,1); wait_for(a2z)
    p.spawn(sid,2); wait_for(a2z)
    p.spawn(sid,3); wait_for(a2z)

    z2p.write( ((sid,1), ('input',3)) )
    wait_for(a2z)

    for _ in range(3):
        z2p.write( ((sid,1), ('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,2), ('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,3), ('output',)) )
        wait_for(a2z)

    for _ in range(3):
        z2p.write( ((sid,1), ('output',)) )
        fro,msg = wait_for(a2z)
        z2p.write( ((sid,2), ('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,3), ('output',)) )
        wait_for(a2z)
    
    for _ in range(2):
        z2p.write( ((sid,1), ('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,2), ('output',)) )
        fro,msg = wait_for(a2z)
        z2p.write( ((sid,3), ('output',)) )
        wait_for(a2z)
    
    z2p.write( ((sid,1), ('output',)) )
    wait_for(a2z)
    z2p.write( ((sid,1), ('output',)) )
    fro,msg= wait_for(p2z)
    assert msg[0] == 'early'
    z2p.write( ((sid,2), ('output',)) )
    wait_for(a2z)
    z2p.write( ((sid,3), ('output',)) )
    wait_for(a2z)
    
    for _ in range(3):
        z2p.write( ((sid,3), ('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,1), ('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,2), ('output',)) )
        wait_for(a2z)

    z2p.write( ((sid,1), ('output',)) )
    fro,msg = wait_for(p2z);
    print('P1 output', msg)
    z2p.write( ((sid,2), ('output',)) )
    fro,msg = wait_for(p2z)
    print('P2 output', msg)
    z2p.write( ((sid,3), ('output',)) )
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

    p = PartyWrapper(z2p, p2z, f2p, p2f, a2p, p2a, 'F_sfe')
    gevent.spawn(p.run)

    z2a.write( ('corrupt',4) )
    wait_for(a2z)

    p.spawn(sid,1); wait_for(a2z)
    p.spawn(sid,2); wait_for(a2z)
    p.spawn(sid,3); wait_for(a2z)
    p.spawn(sid,4); wait_for(a2z)
   
    z2p.write( ((sid,1), ('input',3)) )
    m = wait_for(a2z)

    #z2a.write( ('A2P', (4, ( ((sid, 'F_clock'), ('RoundOK',))))) )
    #wait_for(a2z)

    for _ in range(4):
        z2p.write( ((sid,1), ('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,2), ('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,3), ('output',)) )
        wait_for(a2z)

    for _ in range(4):
        z2p.write( ((sid,1), ('output',)) )
        fro,msg = wait_for(a2z)
        z2p.write( ((sid,2), ('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,3), ('output',)) )
        wait_for(a2z)
    
    for _ in range(4):
        z2p.write( ((sid,1), ('output',)) )
        fro,msg = wait_for(a2z)
        z2p.write( ((sid,2), ('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,3), ('output',)) )
        wait_for(a2z)
    
    for _ in range(4):
        z2p.write( ((sid,1), ('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,2), ('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,3), ('output',)) )
        wait_for(a2z)
    
    z2p.write( ((sid,1), ('output',)) )
    fro,m = wait_for(p2z)
    print('P1 output:', m)
    z2p.write( ((sid,2), ('output',)) )
    fro,m = wait_for(p2z)
    print('P2 output;', m)
    z2p.write( ((sid,3), ('output',)) )
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

    p = PartyWrapper(sid, z2p, p2z, f2p, p2f, a2p, p2a, 'F_sfe')
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

def env1(static, z2p, z2f, z2a, a2z, p2z, f2z):
    sid = ('one', 4, (1,2,3))
    static.write( ('sid',sid))

    z2p.write( ((sid,1), ('sync',)) )
    wait_for(a2z)
    z2p.write( ((sid,2), ('sync',)) )
    wait_for(a2z)
    z2p.write( ((sid,3), ('sync',)) )
    wait_for(a2z)
    #z2p.write( ((sid,4), ('sync',)) )
    #wait_for(a2z)

    z2p.write( ((sid,1), ('input',3)) )
    wait_for(a2z)

    for _ in range(3):
        z2p.write( ((sid,1), ('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,2), ('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,3), ('output',)) )
        wait_for(a2z)

    for _ in range(3):
        z2p.write( ((sid,1), ('output',)) )
        fro,msg = wait_for(a2z)
        z2p.write( ((sid,2), ('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,3), ('output',)) )
        wait_for(a2z)
    
    for _ in range(2):
        z2p.write( ((sid,1), ('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,2), ('output',)) )
        fro,msg = wait_for(a2z)
        z2p.write( ((sid,3), ('output',)) )
        wait_for(a2z)
    
    z2p.write( ((sid,1), ('output',)) )
    wait_for(a2z)
    z2p.write( ((sid,1), ('output',)) )
    fro,msg= wait_for(p2z)
    assert msg[0] == 'early'
    z2p.write( ((sid,2), ('output',)) )
    wait_for(a2z)
    z2p.write( ((sid,3), ('output',)) )
    wait_for(a2z)
    
    for _ in range(3):
        z2p.write( ((sid,3), ('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,1), ('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,2), ('output',)) )
        wait_for(a2z)

    z2p.write( ((sid,1), ('output',)) )
    fro,msg = wait_for(p2z);
    print('P1 output', msg)
    z2p.write( ((sid,2), ('output',)) )
    fro,msg = wait_for(p2z)
    print('P2 output', msg)
    z2p.write( ((sid,3), ('output',)) )
    fro,msg = wait_for(p2z)
    print('P3 output', msg)
    
    
from execuc import execUC
if __name__=='__main__':
    #test_all_honest()
    #test_sim()
    #test_one_crupt_party()
    sid = ('one', 4, (1,2,3))
    execUC(env1, [('F_sfe', SFE_Bracha_Functionality)], PartyWrapper, 'F_sfe', BrachaSimulator)
