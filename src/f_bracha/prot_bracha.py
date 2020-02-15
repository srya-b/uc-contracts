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

BOLD = '\033[1m'
ENDC = '\033[0m'
P1 = '\033[94m'
P2 = '\033[92m'
P3 = '\033[93m'

class Bracha_Protocol(object):
    def __init__(self, sid, pid, _p2f, _f2p, _p2a, _a2p, _p2z, _z2p):
        self.sid = sid
        self.ssid = self.sid[0]
        # ignore sid[1] = Rnd
        self.parties = self.sid[2]
        self.pid = pid
        if self.pid == 1: self.leader = True
        else: self.leader = False
        self.leaderpid = 11
        self.p2f = _p2f; self.f2p = _f2p
        self.p2a = _p2a; self.a2p = _a2p
        self.p2z = _p2z; self.z2p = _z2p

        self.clock_round = 1
        self.roundok = False
        self.valaccepted = False; self.val = None
        self.echoreceived = 0
        self.readyreceived = 0
        self.todo = [ (lambda: dump.dump(),()) for p in self.parties if p != self.pid ]   # only contains n-1 items (party never sends to itself), so the last round will send RoundOK to F_clock
        self.startsync = True
        self.broadcastcomplete = False

        # Sent roundok first
        print('[{}] Sending start synchronization...'.format(self.pid))
        self.p2f.write( ((self.sid,'F_clock'), ('RoundOK',)) )
        self.roundok = True

    def wait_for(self, chan):
        r = gevent.wait(objects=[chan],count=1)
        r = r[0]
        fro,msg = r.read()
        chan.reset()
        return fro,msg

    def except_me(self):
        return [p for p in self.parties if p != self.pid]

    def input_val(self, m):
        print('\033[1m\t [{}] VAL with val {}, round {}\033[0m'.format(self.pid, m, self.clock_round)) 
        self.val = m
        self.todo = []
        for pid in self.except_me():
            fbdsid = (self.ssid, self.pid, pid, self.clock_round)
            # Not sending to self, so increment counter now
            self.todo.append( (self.send_message, (fbdsid, ('send',('ECHO',self.val)))) )
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
                fbdsid = (self.ssid, self.pid, pid, self.clock_round)
                self.todo.append( (self.send_message, (fbdsid, ('send',('READY',self.val)))) )
            self.readyreceived = 1

    def input_ready(self, m):
        print('\033[1m\t [{}] READY with val {}, round {}\033[0m'.format(self.pid, m, self.clock_round)); 
        if m != self.val: assert False; return # TODO remove assert
        #print('Ready received', self.readyreceived)
        self.readyreceived += 1
        n = len(self.parties)
        if self.readyreceived == int(2 * (n/3) + 1):
            print(P2 + '[{}] Received {} READY and ACCEPTED {}'.format(self.pid,self.readyreceived,m) + ENDC)
            self.todo = []
            for _ in self.parties:
                self.todo.append( (None, None) ) 
            self.broadcastcomplete = True
        
    def fetch(self, fbdsid):
        #fbdsid = (self.ssid, fro, self.pid)
        fro = fbdsid[1]
        self.p2f.write( ((fbdsid,'F_bd'), ('fetch',)) )
        _fro,_msg = self.wait_for(self.f2p)
        #print('\033[1m[{}]\033[0m for message M:{} from sid:{}'.format(self.pid, _msg, fbdsid))
        _,msg = _msg
        if msg is None: return #dump.dump(); return
        tag,m = msg
      
        #print('\n\t\033[1m[{}]\033[0m fetching {}'.format(self.pid,fbdsid))
        # check message type and round and that VAL comes from delaer
        if self.clock_round == 2 and tag == 'VAL' and not self.valaccepted and fro == 1:
            self.input_val(m)
        elif self.clock_round == 3 and tag == 'ECHO':
            self.input_echo(m)
        elif self.clock_round == 4 and tag == 'READY':
            self.input_ready(m)
    
    def send_message(self, fbdsid, msg):
        _ssid,_fro,_to,_r = fbdsid
        #print('\033[1m[{}]'.format(_fro), 'Sending message\033[0m {} to F_bd (fro:{}, to:{}, round:{})'.format(msg, _fro, _to, _r))
        self.p2f.write( ((fbdsid,'F_bd'), msg) )

    def read_messages(self):
        # Read even from myself so that the dealer
        # sees his own VAL message, no one will ever send to themselves (except dealer)
        # so it's okay
        #for p in self.except_me():
        # If i'm the dealer, i know in round 2 i have to send ECHO messages
        # to the other parties, so I call input_val in clock_round = 2 to 
        # simulate a VAL message to myself
        if self.clock_round == 2 and not self.valaccepted and self.pid == 1:
            self.input_val(self.val)
            return
        for p in self.except_me():
            fbdsid = (self.ssid, p, self.pid, self.clock_round-1)
            self.fetch( fbdsid )


    # The way it's goint to work:
    # Regular Party: 
    #     At the start of every round, read all the incoming messages and
    #     load the `todo` queue with the messages that need to be sent to
    #     the other n-1 parties (don'nt need to send to yourself unless
    #     you're the dealer. You also pop off todo and send the first message
    #     in the first activation so that the last activation only does 
    #     RoundOK to F_clock
    # Dealer:
    #     On input from the dealer, the dealer needs to send himself the 
    #     input as well to trigger the sending of ECHO messages. This 
    #     means that all `n` activations must be used for sending the first
    #     VAL messages and leaving no activation for the RoundOK. Therefore
    #     the dealer must do something else to send ECHO messages in the next
    #     round. Perhaps a hardcoded behavior would be the best where the
    #     dealer will check in 1st activation of round2 whether a VAL was
    #     sent. If so initiate the subroutine as if a VAL messages had been
    #     received.
    def check_round_ok(self):
        if self.broadcastcomplete:
            if len(self.todo) > 0: self.todo.pop(0); dump.dump()
            else:
                self.p2z.write( self.val )
            return

        # If RoundOK has been sent, then wait until we have a new round
        if self.roundok:
            #print('\033[1m [{}] RoundOK already sent\033[0m'.format(self.pid))
            self.p2f.write( ((self.sid,'F_clock'),('RequestRound',)) )
            fro,di = self.wait_for(self.f2p)
            if di == 0:     # this means the round has ended
                #print('\033[1m ({}) new round {} \033[0m'.format(self.pid,self.clock_round+1))
                self.clock_round += 1
                self.read_messages()    # reads messagesna dn queues the messages to be sent
                #print('Done with round')
                self.roundok = False
            else: 
                #print('\033[1m [{}] early\033[0m'.format(self.pid))
                self.p2z.write( ('early',) )
                return #TODO change to check

        if len(self.todo) > 0:
            #print('[{}] Still todo'.format(self.pid))
            # pop off todo and do it
            f,args = self.todo.pop(0)
            if f: f(*args)
            else: dump.dump()
        elif len(self.todo) == 0 and not self.broadcastcomplete:      
            #print('[{}] RoundOK'.format(self.pid))
            self.p2f.write( ((self.sid,'F_clock'),('RoundOK',)) )
            self.roundok = True
        else: dump.dump()

    def send_input(self, inp, pid):
        fbdsid = (self.ssid, self.leaderpid, pid)
        self.p2f.write( ((fbdsid,'F_bd'), ('send',('VAL',inp))) )

    def input_input(self, v):
        if self.clock_round != 1: dump.dump(); return
        self.newtodo = []
        for p in self.except_me():
            fbdsid = (self.ssid, self.pid, p, self.clock_round) 
            self.newtodo.append( (self.send_message, (fbdsid, ('send', ('VAL',v)))) )
            print('Sending VAL for', self.clock_round)
        self.val = v    # dealer won't deliver to himself, so just set it now
        self.todo = self.newtodo
        dump.dump()

    def input_msg(self, sender, msg):
        sid,pid = sender
        if msg[0] == 'input' and self.leader:
            self.input_input(msg[1])
        elif msg[0] == 'output':
            self.check_round_ok()
        else: dump.dump()

    def run(self):
        while True:
            ready = gevent.wait(
                objects=[self.a2p, self.z2p, self.f2p],
                count=1
            )
            assert len(ready) == 1
            r = ready[0]
            if self.roundok and self.startsync:
                self.p2f.write( ((self.sid,'F_clock'),('RequestRound',)) )
                fro,di = self.wait_for(self.f2p)
                if di == 1: raise Exception('Start synchronization not done')
                self.roundok = False
                self.startsync = False
                 
            if r == self.z2p:
                msg = r.read()
                #print('\n\t \033[1m message to prot_bracha={}, msg={}\033[0m'.format(self.pid, msg))
                self.z2p.reset()
                self.input_msg((-1,-1),msg)
            else: dump.dump()


#import dump
from itertools import combinations,permutations
from comm import GenChannel, setAdversary
from itm2 import FunctionalityWrapper, PartyWrapper, DummyAdversary, ProtocolWrapper2
from utils2 import z_inputs, z_ainputs, wait_for, z_get_leaks, waits
from f_clock import Clock_Functionality
from f_bd_sec import BD_SEC_Functionality
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

    advitm = DummyAdversary('adv',-1, z2a,a2z, p2a,a2p, a2f,f2a)
    setAdversary(advitm)
    gevent.spawn(advitm.run)

    p = ProtocolWrapper2(sid, z2p,p2z, f2p,p2f, a2p,p2a, Bracha_Protocol)
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

    advitm = DummyAdversary('adv',-1, z2a,a2z, p2a,a2p, a2f,f2a)
    setAdversary(advitm)
    gevent.spawn(advitm.run)

    p = ProtocolWrapper2(sid, z2p,p2z, f2p,p2f, a2p,p2a, Bracha_Protocol)
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

    advitm = DummyAdversary('adv',-1, z2a,a2z, p2a,a2p, a2f,f2a)
    setAdversary(advitm)
    gevent.spawn(advitm.run)

    p = ProtocolWrapper2(sid, z2p,p2z, f2p,p2f, a2p,p2a, Bracha_Protocol)
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

    advitm = DummyAdversary(sid,-1, z2a,a2z, p2a,a2p, a2f,f2a)
    setAdversary(advitm)
    gevent.spawn(advitm.run)

    p = ProtocolWrapper2(sid, z2p,p2z, f2p,p2f, a2p,p2a, Bracha_Protocol)
    gevent.spawn(p.run)
    
    #z2a.write( ('A2F', ('corrupt',4)) )
    z2a.write( ('corrupt',4) )
    wait_for(a2z)
   
    # Start synchronization requires roundOK first to determine honest parties
    # giving input to a party before all have done this will result in Exception
    p.spawn(1); wait_for(a2z)
    p.spawn(2); wait_for(a2z)
    p.spawn(3); wait_for(a2z)
    p.spawn(4); wait_for(a2z)
   
    ## DEALER INPUT
    z2p.write( (1, ('input',10)) )
    wait_for(a2z)

    # N=3 ACTIVATIONS FOR ROUND=1     (Dealer sends VAL)
    for i in range(4):
        z2p.write( (1, ('output',)))
        wait_for(a2z)
        z2p.write( (2, ('output',)))
        wait_for(a2z)
        z2p.write( (3, ('output',)))
        wait_for(a2z)

    z2a.write( ('A2P', (4, ( ((sid, 'F_clock'), ('RoundOK',))))) )
    wait_for(a2z)

    # N=3 ACTIVATIONS FOR ROUND=2   (get VAL, send ECHO)
    for i in range(4):
        z2p.write( (1,('output',)) )
        wait_for(a2z)
        z2p.write( (2, ('output',)) )
        wait_for(a2z)
        z2p.write( (3, ('output',)))
        wait_for(a2z)

    # N=3 ACTIVATIONS FOR ROUND=3   (get ECHO, send READY)
    for _ in range(3): 
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
    for i in range(4):
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
    

if __name__=='__main__':
    #test_all_honest()
    #test_crupt_dealer_no_accept()
    #test_crupt_dealer_1_accept_1_not()
    test_one_crupt_party()
    
