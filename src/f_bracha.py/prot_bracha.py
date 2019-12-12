import dump
import gevent
from itm import ITMFunctionality
from comm import ishonest, isdishonest, isadversary, isf, isparty
from queue import Queue as qqueue
from utils import print, gwrite, z_write
from hashlib import sha256
from collections import defaultdict
from gevent.queue import Queue, Channel

class Bracha_Protocol(object):
    def __init__(self, sid, pid, _p2f, _f2p, _p2a, _a2p, _p2z, _z2p):
        self.sid = sid
        self.ssid = self.sid[0]
        self.parties = self.sid[1]
        self.pid = pid
        if self.pid == 1: self.leader = True
        else: self.leader = False
        self.p2f = _p2f; self.f2p = _f2p
        self.p2a = _p2a; self.a2p = _a2p
        self.p2z = _p2z; self.z2p = _z2p

        self.clock_round = 1
        self.roundok = False
        self.todo = [ (lambda x: print('lul'),p) for p in self.parties]

    def wait_for(self, chan):
        r = gevent.wait(objects=[chan],count=1)
        r = r[0]
        fro,msg = r.read()
        chan.reset()
        return fro,msg

    def fetch(self, fro):
        fbdsid = (self.ssid, fro, self.pid)
        self.p2f.write( ((fbdsid,'F_bd'), ('fetch',)) )
        fro,msg = self.wait_for(self.f2p)
        print("Fetched this message", fro, msg)
        #dump.dump()

    def check_round_ok(self):
        print('Checking round, todo=', self.todo)
        if self.roundok:
            return #TODO change to check

        if len(self.todo) > 0:
            # pop off todo and do it
            f,args = self.todo.pop(0)
            f(*args)
            # TODO done?
            if len(self.todo) == 0:
                print('\n\t\t all gone! \n\t\t')
                self.p2f.write( ((self.sid,'F_clock'),('RoundOK',)) )
                fro,msg = self.wait_for(self.f2p); assert msg == ('OK',)
                dump.dump() #TODO clock todo 1 
            else: dump.dump()
        elif len(self.todo) == 0:      
            self.p2f.write( ((self.sid,'F_clock'),('RoundOK',)) )
        print('TODO after=', self.todo)

    def send_input(self, inp, pid):
        fbdsid = (self.ssid, self.pid, pid)
        self.p2f.write( ((fbdsid,'F_bd'), ('send',('VAL',inp))) )
        fro,msg = self.wait_for(self.f2p)
        print('OK from F_bd', msg); assert msg == ('sent',), "msg={}".format(msg)

    def input_input(self, v):
        _newtodo = []
        for x in self.parties:
            _newtodo.append( (self.send_input,(v,x)) )
        self.todo = _newtodo

    def input_msg(self, sender, msg):
        sid,pid = sender
        if msg[0] == 'input' and self.leader:
            self.input_input(msg[1])
            self.check_round_ok()
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

            if r == self.z2p:
                msg = r.read()
                self.z2p.reset()
                self.input_msg((-1,-1),msg)
            else: dump.dump()


import dump
from itertools import combinations,permutations
from comm import GenChannel, setAdversary
from itm2 import FunctionalityWrapper, PartyWrapper, DummyAdversary, ProtocolWrapper2
from utils2 import z_inputs, z_ainputs, wait_for, z_get_leaks
from f_clock import Clock_Functionality
from f_bd_sec import BD_SEC_Functionality
def test():
    sid = ('one',(1,2,3))
    f2p,p2f = GenChannel(),GenChannel()
    f2a,a2f = GenChannel(),GenChannel()
    f2z,z2f = GenChannel(),GenChannel()
    p2a,a2p = GenChannel(),GenChannel()
    p2z,z2p = GenChannel(),GenChannel()
    z2a,a2z = GenChannel(),GenChannel()
    
    f = FunctionalityWrapper(p2f,f2p, a2f,f2a, z2f,f2z)
    gevent.spawn(f.run)
    f.newFID(sid,'F_clock',Clock_Functionality)
    for x,y in permutations((1,2,3),2): 
        f.newFID( ('one',x,y), 'F_bd', BD_SEC_Functionality)
    for x in (1,2,3):
        f.newFID( ('one',x,x), 'F_bd', BD_SEC_Functionality)

    advitm = DummyAdversary('adv',-1, z2a,a2z, p2a,a2p, a2f,f2a)
    setAdversary(advitm)
    gevent.spawn(advitm.run)

    p = ProtocolWrapper2(sid, z2p,p2z, f2p,p2f, a2p,p2a, Bracha_Protocol)
    gevent.spawn(p.run)
   
    z2p.write( (1, ('input',1)) )
    dump.dump_wait()
    fro,(_,msg) = z_get_leaks(z2a, a2z, 'A2F', ((('one',1,1),'F_bd')))
    print('Adversary leak after input 1', msg)
    
    z2p.write( (1, ('output',)) )
    dump.dump_wait()
    fro,(_,msg) = z_get_leaks(z2a, a2z, 'A2F', ((('one',1,2),'F_bd')))
    print('Adversary leak after activation of 1', msg)
    
    #z2p.write( (1, ('output',)) )
    #dump.dump_wait()
    #fro,(_,msg) = z_get_leaks(z2a, a2z, 'A2F', ((('one',1,3),'F_bd')))
    #print('Adversary leak after third activation of 1', msg)

    #fro,(_,msg) = z_get_leaks(z2a, a2z, 'A2F', ((sid,'F_clock')))
    #print('Clock leaks', msg)

if __name__=='__main__':
    test()
    
