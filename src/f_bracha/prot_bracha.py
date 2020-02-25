import dump
import gevent
from comm import ishonest, isdishonest, isadversary, isf, isparty
from math import ceil
from queue import Queue as qqueue
from utils import print, gwrite, z_write, z_crupt
from hashlib import sha256
from collections import defaultdict
from gevent.queue import Queue, Channel
from itm import ITMSyncProtocol

BOLD = '\033[1m'
ENDC = '\033[0m'
P1 = '\033[94m'
P2 = '\033[92m'
P3 = '\033[93m'

class Bracha_Protocol(ITMSyncProtocol):
    def __init__(self, sid, pid, _p2f, _f2p, _p2a, _a2p, _p2z, _z2p):
        # All protocols do this (below)
        self.p2f = _p2f; self.f2p = _f2p
        self.p2a = _p2a; self.a2p = _a2p
        self.p2z = _p2z; self.z2p = _z2p
        self.channels_to_read = [self.a2p, self.z2p, self.f2p]
        self.handlers = {
            self.a2p: lambda x: dump.dump(),
            self.f2p: lambda x: dump.dump(),
            self.z2p: self.input_msg
        }

        ITMSyncProtocol.__init__(self, sid, pid , self.channels_to_read, self.handlers)
        
        # specific to the broadcast
        if self.pid == 1: self.leader = True
        else: self.leader = False
        self.leaderpid = 11
        self.valaccepted = False; self.val = None
        self.echoreceived = 0
        self.readyreceived = 0
    
    def except_me(self):
        return [p for p in self.parties if p != self.pid]

    def input_val(self, m):
        print('\033[1m\t [{}] VAL with val {}, round {}\033[0m'.format(self.pid, m, self.clock_round)) 
        self.val = m
        for pid in self.except_me():
            self.send_in_o1(pid, ('ECHO',self.val))
        self.valaccepted = True
        self.echoreceived = 1

    def input_echo(self, m):
        print('\033[1m\t [{}] ECHO with val {}, round {}\033[0m'.format(self.pid, m, self.clock_round)) 
        if m != self.val: assert False; return # TODO remove assert
        self.echoreceived += 1
        n = len(self.parties)
        if self.echoreceived == (ceil(n + (n/3))/2):
            self.todo = []
            for pid in self.except_me():
                self.send_in_o1(pid, ('READY',self.val))
            self.readyreceived = 1

    def input_ready(self, m):
        print('\033[1m\t [{}] READY with val {}, round {}\033[0m'.format(self.pid, m, self.clock_round)); 
        if m != self.val: assert False; return # TODO remove assert
        self.readyreceived += 1
        n = len(self.parties)
        if self.readyreceived == int(2 * (n/3) + 1):
            print(P2 + '[{}] Received {} READY and ACCEPTED {}'.format(self.pid,self.readyreceived,m) + ENDC)
            self.todo = []
            for _ in self.parties:
                self.todo.append( (None, None) ) 
            self.outputset = True

    def p2p_handler(self, fro, msg):
        tag,m = msg
        sid,pid = fro
        # check message type and round and that VAL comes from delaer
        if self.clock_round == 2 and tag == 'VAL' and not self.valaccepted and pid == 1:
            self.input_val(m)
        elif self.clock_round == 3 and tag == 'ECHO':
            self.input_echo(m)
        elif self.clock_round == 4 and tag == 'READY':
            self.input_ready(m)


    def read_messages(self):
        # Read even from myself so that the dealer
        # sees his own VAL message, no one will ever send to themselves (except dealer)
        # so it's okay
        # If i'm the dealer, i know in round 2 i have to send ECHO messages
        # to the other parties, so I call input_val in clock_round = 2 to 
        # simulate a VAL message to myself
        if self.clock_round == 2 and not self.valaccepted and self.pid == 1:
            self.input_val(self.val)
            return
        for p in self.except_me():
            fbdsid = (self.ssid, (self.sid,p), (self.sid,self.pid), self.clock_round-1)
            self.fetch( fbdsid )


    def input_input(self, v):
        if self.clock_round != 1: dump.dump(); return
        self.newtodo = []
        for p in self.except_me():
            fbdsid = (self.ssid, (self.sid,self.pid), (self.sid,p), self.clock_round) 
            self.newtodo.append( (self.send_message, (fbdsid, ('send', ('VAL',v)))) )
            print('Sending VAL for', self.clock_round)
        self.val = v    # dealer won't deliver to himself, so just set it now
        self.todo = self.newtodo
        dump.dump()

    def input_msg(self, msg):
        if msg[0] == 'input' and self.leader:
            self.input_input(msg[1])
        # TODO change this to be automatically handled in base class
        elif msg[0] == 'output':
            self.check_round_ok()
        else: dump.dump()

from itertools import combinations,permutations
from comm import setAdversary
from itm import FunctionalityWrapper, PartyWrapper, ProtocolWrapper, GenChannel
from utils import z_inputs, z_ainputs, wait_for, z_get_leaks, waits
from syn_katz import Clock_Functionality, BD_SEC_Functionality, KatzDummyAdversary

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
    f.newcls('F_clock', Clock_Functionality)
    f.newcls('F_bd', BD_SEC_Functionality)

    advitm = KatzDummyAdversary('adv',-1, z2a,a2z, p2a,a2p, a2f,f2a)
    setAdversary(advitm)
    gevent.spawn(advitm.run)

    p = ProtocolWrapper(sid, z2p,p2z, f2p,p2f, a2p,p2a, Bracha_Protocol)
    gevent.spawn(p.run)

    # Start synchronization requires roundOK first to determine honest parties
    # giving input to a party before all have done this will result in Exception
    p.spawn(1); wait_for(a2z)
    p.spawn(2); wait_for(a2z)
    p.spawn(3); wait_for(a2z)

    ## DEALER INPUT
    z2p.write( (1, ('input',10)) )
    wait_for(a2z)

    # N=3 ACTIVATIONS FOR ROUND=1     (Dealer sends VAL)
    for i in range(3):
        z2p.write( (1, ('output',)))
        wait_for(a2z)
        z2p.write( (2, ('output',)))
        wait_for(a2z)
        z2p.write( (3, ('output',)))
        wait_for(a2z)

    # N=3 ACTIVATIONS FOR ROUND=2   (get VAL, send ECHO)
    for i in range(3):
        z2p.write( (1,('output',)) )
        wait_for(a2z)
        z2p.write( (2, ('output',)) )
        wait_for(a2z)
        z2p.write( (3, ('output',)))
        wait_for(a2z)

    # N=3 ACTIVATIONS FOR ROUND=3   (get ECHO, send READY)
    for _ in range(2): 
        z2p.write( (1, ('output',)) )
        wait_for(a2z)
        z2p.write( (2, ('output',)) )
        wait_for(a2z)
        z2p.write( (3, ('output',)) )
        wait_for(a2z)
    
    z2p.write( (1, ('output',)) )
    wait_for(a2z)
    z2p.write( (1, ('output',)) )
    fro,msg = wait_for(p2z)
    assert msg[0] == 'early'
    z2p.write( (2, ('output',)) )
    wait_for(a2z)
    z2p.write( (3, ('output',)) )
    wait_for(a2z)

    # First activation should get READY and ACCEPT  (get READY, wait n activations to output)
    for i in range(3):
        z2p.write( (3, ('output',)) )
        wait_for(a2z)
        z2p.write( (1, ('output',)) )
        wait_for(a2z)
        z2p.write( (2, ('output',)) )
        wait_for(a2z)

    z2p.write( (1, ('output',)) )
    fro,msg = wait_for(p2z)
    print("P1 output", msg)
    z2p.write( (2, ('output',)) )
    fro,msg = wait_for(p2z)
    print("P2 output", msg)
    z2p.write( (3, ('output',)) )
    fro,msg = wait_for(p2z)
    print("P3 output", msg)


# In n=3 this protocol fails, by changing either of the two lines (*)
# environment can make one party accept and not the other if the dealer
# is corrupt.
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
    f.newcls('F_clock', Clock_Functionality)
    f.newcls('F_bd', BD_SEC_Functionality)

    advitm = KatzDummyAdversary('adv',-1, z2a,a2z, p2a,a2p, a2f,f2a)
    setAdversary(advitm)
    gevent.spawn(advitm.run)

    p = ProtocolWrapper(sid, z2p,p2z, f2p,p2f, a2p,p2a, Bracha_Protocol)
    gevent.spawn(p.run)
   
    # Start synchronization requires roundOK first to determine honest parties
    # giving input to a party before all have done this will result in Exception
    p.spawn(1); wait_for(a2z)
    p.spawn(2); wait_for(a2z)
    p.spawn(3); wait_for(a2z)

    # corrupt the dealer
    # change protocol itm to a passthrough itm
    # register corruption with F_clock
    z2a.write( ('A2P', (1, ( (('one',1,2,1),'F_bd'), ('send',('VAL',3))))) )
    wait_for(a2z)
    z2a.write( ('A2P', (1, ( (('one',1,3,1),'F_bd'), ('send',('VAL',3))))) )
    wait_for(a2z)
    z2a.write( ('A2P', (1, ( ((sid, 'F_clock'), ('RoundOK',))))) )
    wait_for(a2z)

    for _ in range(3):
        z2p.write( (2, ('output',)) )
        wait_for(a2z)
        z2p.write( (3, ('output',)) )
        wait_for(a2z)

    for _ in range(3):
        z2p.write( (2, ('output',)) )
        wait_for(a2z)
        z2p.write( (3, ('output',)) )
        wait_for(a2z)

    z2a.write( ('A2P', (1, ( (('one',1,2,2),'F_bd'), ('send',('ECHO',3))))) )
    wait_for(a2z)
    z2a.write( ('A2P', (1, ( (('one',1,3,2),'F_bd'), ('send',('ECHO',3))))) )
    wait_for(a2z)
    z2a.write( ('A2P', (1, ( ((sid, 'F_clock'), ('RoundOK',))))) )
    wait_for(a2z)
    
    for _ in range(3):
        z2p.write( (2, ('output',)) )
        wait_for(a2z)

    # (*)
    z2a.write( ('A2P', (1, ( (('one',1,2,3),'F_bd'), ('send',('READY',3))))) )
    wait_for(a2z)
    # (*)
    z2a.write( ('A2P', (1, ( (('one',1,3,3),'F_bd'), ('send',('READY',3))))) )
    wait_for(a2z)
    z2a.write( ('A2P', (1, ( ((sid, 'F_clock'), ('RoundOK',))))) )
    wait_for(a2z)

    for _ in range(3):
        z2p.write( (3, ('output',)) )
        wait_for(a2z)

    z2p.write( (2, ('output',)) )
    wait_for(a2z)
    z2p.write( (3, ('output',)) )
    wait_for(a2z)


# TODO: should not be possible because t = n/3
def test_crupt_dealer_1_accept_1_not():
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
    f.newcls('F_clock', Clock_Functionality)
    f.newcls('F_bd', BD_SEC_Functionality)

    advitm = KatzDummyAdversary('adv',-1, z2a,a2z, p2a,a2p, a2f,f2a)
    setAdversary(advitm)
    gevent.spawn(advitm.run)

    p = ProtocolWrapper(sid, z2p,p2z, f2p,p2f, a2p,p2a, Bracha_Protocol)
    gevent.spawn(p.run)
   
    # Start synchronization requires roundOK first to determine honest parties
    # giving input to a party before all have done this will result in Exception
    p.spawn(1); wait_for(a2z)
    p.spawn(2); wait_for(a2z)
    p.spawn(3); wait_for(a2z)

    # corrupt the dealer
    # change protocol itm to a passthrough itm
    # register corruption with F_clock
    z2a.write( ('A2P', (1, ( (('one',1,2,1),'F_bd'), ('send',('VAL',3))))) )
    wait_for(a2z)
    z2a.write( ('A2P', (1, ( (('one',1,3,1),'F_bd'), ('send',('VAL',3))))) )
    wait_for(a2z)
    z2a.write( ('A2P', (1, ( ((sid, 'F_clock'), ('RoundOK',))))) )
    wait_for(a2z)

    for _ in range(3):
        z2p.write( (2, ('output',)) )
        wait_for(a2z)
        z2p.write( (3, ('output',)) )
        wait_for(a2z)

    for _ in range(3):
        z2p.write( (2, ('output',)) )
        wait_for(a2z)
        z2p.write( (3, ('output',)) )
        wait_for(a2z)

    z2a.write( ('A2P', (1, ( ((sid, 'F_clock'), ('RoundOK',))))) )
    wait_for(a2z)
    
    for _ in range(3):
        z2p.write( (2, ('output',)) )
        wait_for(a2z)

    z2a.write( ('A2P', (1, ( (('one',1,2,3),'F_bd'), ('send',('READY',3))))) )
    wait_for(a2z)
    z2a.write( ('A2P', (1, ( (('one',1,3,3),'F_bd'), ('send',('READY',3))))) )
    wait_for(a2z)
    z2a.write( ('A2P', (1, ( ((sid, 'F_clock'), ('RoundOK',))))) )
    wait_for(a2z)

    for _ in range(3):
        z2p.write( (3, ('output',)) )
        wait_for(a2z)

    z2p.write( (2, ('output',)) )
    wait_for(a2z)
    z2p.write( (3, ('output',)) )
    wait_for(a2z)

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
    f.newcls('F_clock', Clock_Functionality)
    f.newcls('F_bd', BD_SEC_Functionality)

    advitm = KatzDummyAdversary(sid,-1, z2a,a2z, p2a,a2p, a2f,f2a)
    setAdversary(advitm)
    gevent.spawn(advitm.run)

    p = ProtocolWrapper(z2p,p2z, f2p,p2f, a2p,p2a, Bracha_Protocol)
    gevent.spawn(p.run)
    
    #z2a.write( ('A2F', ('corrupt',4)) )
    #z2a.write( ('corrupt',(sid,4)) )
    z2a.write( ('corrupt', 4) )
    wait_for(a2z)
   
    # Start synchronization requires roundOK first to determine honest parties
    # giving input to a party before all have done this will result in Exception
    p.spawn(sid, 1); wait_for(a2z)
    p.spawn(sid, 2); wait_for(a2z)
    p.spawn(sid, 3); wait_for(a2z)
    p.spawn(sid, 4); wait_for(a2z)
   
    ## DEALER INPUT
    z2p.write( ((sid,1), ('input',10)) )
    wait_for(a2z)

    # N=3 ACTIVATIONS FOR ROUND=1     (Dealer sends VAL)
    for i in range(4):
        z2p.write( ((sid,1), ('output',)))
        wait_for(a2z)
        z2p.write( ((sid,2), ('output',)))
        wait_for(a2z)
        z2p.write( ((sid,3), ('output',)))
        wait_for(a2z)
#
#    z2a.write( ('A2P', ((sid,4), ( ((sid, 'F_clock'), ('RoundOK',))))) )
#    wait_for(a2z)
#
#    # N=3 ACTIVATIONS FOR ROUND=2   (get VAL, send ECHO)
    for i in range(4):
        z2p.write( ((sid,1),('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,2), ('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,3), ('output',)))
        wait_for(a2z)

    # N=3 ACTIVATIONS FOR ROUND=3   (get ECHO, send READY)
    for _ in range(3): 
        z2p.write( ((sid,1), ('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,2), ('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,3), ('output',)) )
        wait_for(a2z)
    
    z2p.write( ((sid,1), ('output',)) )
    wait_for(a2z)
    z2p.write( ((sid,1), ('output',)) )
    fro,msg = wait_for(p2z)
    assert msg[0] == 'early'
    z2p.write( ((sid,2), ('output',)) )
    wait_for(a2z)
    z2p.write( ((sid,3), ('output',)) )
    wait_for(a2z)

    # First activation should get READY and ACCEPT  (get READY, wait n activations to output)
    for i in range(4):
        z2p.write( ((sid,3), ('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,1), ('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,2), ('output',)) )
        wait_for(a2z)

    z2p.write( ((sid,1), ('output',)) )
    fro,msg = wait_for(p2z)
    print("P1 output", msg)
    z2p.write( ((sid,2), ('output',)) )
    fro,msg = wait_for(p2z)
    print("P2 output", msg)
    z2p.write( ((sid,3), ('output',)) )
    fro,msg = wait_for(p2z)
    print("P3 output", msg)
    

if __name__=='__main__':
    #test_all_honest()
    #test_crupt_dealer_no_accept()
    #test_crupt_dealer_1_accept_1_not()
    test_one_crupt_party()
    
