import dump
import gevent
from comm import ishonest, isdishonest, isadversary, setFunctionality
from utils import gwrite, print
from queue import Queue as qqueue
from hashlib import sha256
from collections import defaultdict
from gevent.event import AsyncResult
from gevent.queue import Queue, Channel

class BD_SEC_Functionality(object):
    def __init__(self, sid, pid, f2p, p2f, f2a, a2f, f2z, z2f):
        self.sid = sid
        self.ssid, self.sender, self.receiver, self.round = sid
        #print('\tSender={}, receiver={}'.format(self.sender,self.receiver))
        self.pid = pid
        self.M = None; self.D = 1; self.Dhat = 1
        self.delta = 1
        self.f2p=f2p; self.p2f=p2f
        self.f2a=f2a; self.a2f=a2f
        self.f2z=f2z; self.z2f=z2f
       
        #print('\033[1m[{}]\033[0m new bd_sec with M:{}'.format( self.sid, self.M ))
        self.leaks = []

    def leak(self, msg):
        self.leaks.append( msg )

    def input_send(self, msg):
        #if self.M is not None: assert False
        self.D = 1; self.M = msg
        self.leak( ('send', self.M) )
        #print('\033[1m[Leak]\033[0m', 'message: {}'.format(self.M))
        self.f2a.write( (self.sender, ('sent',self.M)) )   # change sender to id of functionality

    def input_fetch(self):
        self.D -= 1
        if self.D == 0:
            self.f2p.write( (self.receiver, ('sent',self.M)) )
        else: dump.dump()

    def input_msg(self, sender, msg):
        sid,pid = sender
        if msg[0] == 'send' and sender  == self.sender and ishonest(self.sid, self.sender):
            self.input_send(msg[1])
        elif msg[0] == 'fetch' and sender == self.receiver and ishonest(self.sid, self.receiver):
            self.input_fetch()
        else: dump.dump()

    def adv_delay(self, T):
        if self.Dhat+T <= self.delta:
            self.D += T; self.Dhat += T
            self.f2a.write( ('delay-set',) )
            dump.dump()
        else: print('Delay failed with T=', T, 'Dhat=',self.Dhat, 'delta=', self.delta); dump.dump()

    def adv_get_leaks(self):
        self.f2a.write( ('leaks', self.leaks) )
        self.leaks = []

    def adversary_msg(self, msg):
        if msg[0] == 'delay':
            self.adv_delay(msg[1])
        elif msg[0] == 'get-leaks':
            self.adv_get_leaks()
        elif msg[0] == 'send' and isdishonest(self.sid, self.sender):
            self.input_send(msg[1])
        elif msg[0] == 'fetch' and isdishonest(self.sid, self.receiver):
            self.input_fetch()
        else: dump.dump()

    def run(self):
        while True:
            ready = gevent.wait(
                objects=[self.p2f,self.a2f,self.z2f],
                count=1
            )
            assert len(ready)==1
            r = ready[0]

            if r == self.a2f:
                msg = r.read()
                self.a2f.reset()
                self.adversary_msg(msg)
            elif r == self.p2f:
                msg = r.read()
                sender,msg = msg
                self.p2f.reset()
                self.input_msg(sender,msg)
            elif r == self.z2f:
                self.z2f.reset()
                dump.dump()
            else: dump.dump()

import dump
from comm import setAdversary
from itm import FunctionalityWrapper, PartyWrapper, GenChannel
from syn_katz.adv import KatzDummyAdversary
from utils import z_inputs, z_ainputs, wait_for

def test():
    sid = ('one',1,2)
    f2p,p2f = GenChannel(),GenChannel()
    f2a,a2f = GenChannel(),GenChannel()
    f2z,z2f = GenChannel(),GenChannel()

    p2a,a2p = GenChannel(),GenChannel()
    p2z,z2p = GenChannel(),GenChannel()

    z2a,a2z = GenChannel(),GenChannel()
    
    p = PartyWrapper(sid, z2p,p2z, f2p,p2f, a2p,p2a)
    gevent.spawn(p.run)

    f = FunctionalityWrapper(p2f,f2p, a2f,f2a, z2f,f2z)
    gevent.spawn(f.run)
    f.newFID(sid,'F_bd',BD_SEC_Functionality)

    advitm = KatzDummyAdversary('adv',-1, z2a,a2z, p2a,a2p, a2f,f2a)
    setAdversary(advitm)
    gevent.spawn(advitm.run)

    z2p.write( (1, ((sid,'F_bd'),('send','hello'))) )
    msg = wait_for(p2z)
    print('Party back from f_bd', msg)
    z2a.write( ('A2F', ((sid,'F_bd'),('get-leaks',))) )
    msg = wait_for(a2z)
    print('Leaks the right way', msg)

    z2a.write( ('A2F', ((sid,'F_bd'), ('delay',0))) )
    msg = wait_for(a2z)
    print('adv message', msg)

    z2p.write( (2, ((sid,'F_bd'), ('fetch',))))
    fro,(receiver,msg) = wait_for(p2z)
    print('p2z message', msg)

if __name__=='__main__':
    test()
