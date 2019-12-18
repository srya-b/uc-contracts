import dump
import gevent
from itm import ITMFunctionality
from comm import ishonest, isdishonest, isadversary, isf, isparty
from math import ceil
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
        self.leaderpid = 11
        self.p2f = _p2f; self.f2p = _f2p
        self.p2a = _p2a; self.a2p = _a2p
        self.p2z = _p2z; self.z2p = _z2p

        self.clock_round = 1
        self.roundok = False
        self.valaccepted = False; self.val = None
        self.echoreceived = 0
        self.readyreceived = 0
        self.todo = [ (lambda x: print('lul'),(p,)) for p in self.parties]

    def wait_for(self, chan):
        r = gevent.wait(objects=[chan],count=1)
        r = r[0]
        fro,msg = r.read()
        chan.reset()
        return fro,msg

    def input_val(self, m):
        print('\033[1m\n\t [{}] VAL with val {}\n\033[0m'.format(self.pid, m)) 
        self.val = m
        for p in self.parties:
            fbdsid = (self.ssid, self.pid, p)
            self.p2f.write( ((fbdsid,'F_bd'),('send', ('ECHO', self.val))) )
            fro,msg = self.wait_for(self.f2p); assert msg == ('sent',)

    def input_echo(self, m):
        print('\033[1m\n\t [{}] ECHO with val {}\n\033[0m'.format(self.pid, m)) 
        if m != self.val: assert False; return # TODO remove assert
        self.echoreceived += 1
        n = len(self.parties)
        if self.echoreceived == (ceil(n + (n/3))/2):
            for p in self.parties:
                fbdsid = (self.ssid, self.pid, p)
                self.p2f.write( ((fbdsid,'F_bd'),('send',('READY',self.val))) )
                fro,msg = self.wait_for(self.p2f); assert msg == ('send',)

    def input_ready(self, m):
        print('\033[1,\n\t [{}] READY with val {}\n\033[0m'.format(self.pid, m)); 
        if m != self.val: assert False; return # TODO remove assert

        self.readyreceived += 1
        n = len(self.parties)
        assert False 

    def fetch(self, fro):
        fbdsid = (self.ssid, fro, self.pid)
        self.p2f.write( ((fbdsid,'F_bd'), ('fetch',)) )
        _fro,_msg = self.wait_for(self.f2p)
        print("Fetched this message", _fro, _msg, self.clock_round, fro)
        _,msg = _msg
        if msg is None: return
        tag,m = msg
       
        # check message type and round and that VAL comes from delaer
        if self.clock_round == 2 and tag == 'VAL' and not self.valaccepted and fro == 1:
            self.input_val(m)
        elif self.clock_round == 3 and tag == 'ECHO':
            self.input_echo(m)
        elif self.clock_round == 4 and tag == 'READY':
            self.input_ready(m)
        #dump.dump()
    
    def reload_todo(self):
        self.todo = [ (self.fetch,(fro,)) for fro in self.parties]

    def check_round_ok(self):
        #print('Checking round, todo=', self.todo)
        if self.roundok:
            print('\033[1mround ok already set\033[0m')
            self.p2f.write( ((self.sid,'F_clock'),('RequestRound',)) )
            fro,di = self.wait_for(self.f2p)
            if di == 0:     # this means the round has ended
                self.clock_round += 1
            else: return #TODO change to check

        if len(self.todo) > 0:
            print('\033[1mstill todo\033[0m')
            # pop off todo and do it
            f,args = self.todo.pop(0)
            f(*args)
            # TODO done?
            if len(self.todo) == 0:
                print('\n\t\t all gone! \n\t\t')
                self.p2f.write( ((self.sid,'F_clock'),('RoundOK',)) )
                fro,msg = self.wait_for(self.f2p); assert msg == ('OK',)
                self.roundok = True
                self.reload_todo()
                dump.dump() #TODO clock todo 1 
            else: dump.dump()
        elif len(self.todo) == 0:      
            print('\033[1m no todo give round ok \033[0m')
            self.reload_todo()
            self.p2f.write( ((self.sid,'F_clock'),('RoundOK',)) )
            self.roundok = True
        #print('TODO after=', self.todo)

    def send_input(self, inp, pid):
        fbdsid = (self.ssid, self.leaderpid, pid)
        self.p2f.write( ((fbdsid,'F_bd'), ('send',('VAL',inp))) )
        fro,msg = self.wait_for(self.f2p)
        print('OK from F_bd', msg); assert msg == ('sent',), "msg={}".format(msg)

    def input_input(self, v):
        self.newtodo = []
        for p in self.parties:
            self.newtodo.append( (self.send_input, (v,p)) )
         

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
    f.newcls('F_clock', Clock_Functionality)
    f.newcls('F_bd', BD_SEC_Functionality)
    #f.newFID(sid,'F_clock',Clock_Functionality)
    #for x,y in permutations((1,2,3),2): 
    #    f.newFID( ('one',x,y), 'F_bd', BD_SEC_Functionality)
    #for x in (1,2,3):
    #    f.newFID( ('one',x,x), 'F_bd', BD_SEC_Functionality)
    #    f.newFID( ('one',11,x), 'F_bd', BD_SEC_Functionality)

    advitm = DummyAdversary('adv',-1, z2a,a2z, p2a,a2p, a2f,f2a)
    setAdversary(advitm)
    gevent.spawn(advitm.run)

    p = ProtocolWrapper2(sid, z2p,p2z, f2p,p2f, a2p,p2a, Bracha_Protocol)
    gevent.spawn(p.run)
   
    z2p.write( (1, ('input',1)) )
    dump.dump_wait()
    #fro,(_,msg) = z_get_leaks(z2a, a2z, 'A2F', ((('one',11,1),'F_bd')))
    #print('Adversary leak after input 1', msg)
    #
    #z2p.write( (1, ('output',)) )
    #dump.dump_wait()
    #fro,(_,msg) = z_get_leaks(z2a, a2z, 'A2F', ((('one',1,2),'F_bd')))
    #print('Adversary leak after activation of 1', msg)
    #
    #z2p.write( (1, ('output',)) )
    #dump.dump_wait()
    #fro,(_,msg) = z_get_leaks(z2a, a2z, 'A2F', ((('one',1,3),'F_bd')))
    #print('Adversary leak after third activation of 1', msg)
    #
    ## Parties get VAL and respond with ECHO
    #for i in range(3):
    #    z2p.write( (2, ('output',)))
    #    dump.dump_wait()
    #    z2p.write( (3, ('output',)))
    #    dump.dump_wait()

    #fro,(_,msg) = z_get_leaks(z2a, a2z, 'A2F', ((sid,'F_clock')))
    #print('Clock leaks', msg)

    #print('\n\n\033[1m next round \033[0m \n\n')


    #for i in range(1):
    #    z2p.write( (1, ('output',)))
    #    dump.dump_wait()
    #    z2p.write( (2, ('output',)))
    #    dump.dump_wait()
    #    z2p.write( (3, ('output',)))
    #    dump.dump_wait()

if __name__=='__main__':
    test()
    
