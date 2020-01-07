import dump
import gevent
from itm import ITMFunctionality
from comm import ishonest, isdishonest, isadversary, setFunctionality
from utils import gwrite, print
from queue import Queue as qqueue
from hashlib import sha256
from collections import defaultdict
from gevent.event import AsyncResult
from gevent.queue import Queue, Channel

class Clock_Functionality(object):
    def __init__(self, sid, pid, f2p, p2f, f2a, a2f, f2z, z2f):
        self.sid = sid
        self.parties = self.sid[1]
        self.pid = pid
        self.f2p = f2p; self.p2f = p2f
        self.f2a = f2a; self.a2f = a2f
        self.f2z = f2z; self.z2f = z2f

        self.di = dict( (p,0) for p in self.parties)
        self.crupted = set()
        self.leaks = []

    def leak(self, msg):
        self.leaks.append(msg)

    def input_roundok(self, pid):
        self.di[pid] = 1
        if all(self.di[x]==1 for x in self.di):
            for p in self.di: self.di[p] = 0
        self.leak( ('switch',pid) ) #TODO do we need to return back? see clock todo 1 in bracha
        print('\033[1m \n\t di = {} \n\033[0m'.format(self.di))
        self.f2a.write( ('switch',pid) )

    def input_requestround(self, pid):
        self.f2p.write( (pid, self.di[pid]) )

    def input_msg(self, sender, msg):
        sid,pid = sender
        if msg[0] == 'RoundOK' and pid in self.parties:
            self.input_roundok(pid)
        elif msg[0] == 'RequestRound' and pid in self.parties:
            self.input_requestround(pid)
        else: dump.dump()

    def adv_corrupt(self, pid):
        self.crupted.add(pid)        
        dump.dump()

    def adv_get_leaks(self):
        self.f2a.write( ('leaks', self.leaks) )
        self.leaks = []
    
    def adversary_msg(self, msg):
        if msg[0] == 'corrupt':
            self.adv_corrupt(msg[1])
        elif msg[0] == 'get-leaks':
            self.adv_get_leaks()
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
from comm import GenChannel, setAdversary
from itm2 import FunctionalityWrapper, PartyWrapper, DummyAdversary
from utils2 import z_inputs, z_ainputs, wait_for
def test():
    sid = ('one', (1,2))
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
    f.newFID(sid,'F_clock',Clock_Functionality)

    advitm = DummyAdversary('adv',-1, z2a,a2z, p2a,a2p, a2f,f2a)
    setAdversary(advitm)
    gevent.spawn(advitm.run)
    
    z2p.write( (1, ((sid,'F_clock'), ('RequestRound',))) )
    fro,(to,msg) = wait_for(p2z)
    print('\033[1m\tRound from F_clock from 1\033[0m', msg)

    z2p.write( (2, ((sid,'F_clock'), ('RoundOK',))) )
    fro,msg = wait_for(p2z)
    print('\033[1mOK from f_clock after OK from 2\033[0m', msg)
    z2a.write( ('A2F', ((sid,'F_clock'),('get-leaks',))) )
    fro,msg = wait_for(a2z)
    print('\033[1m\tAdversary leak on OK from 2\033[0m', msg)

    z2p.write( (2, ((sid,'F_clock'), ('RequestRound',))) )
    fro,(to,msg) = wait_for(p2z)
    print('\033[1m\tRound from F_clock for 2\033[0m', msg)

    z2p.write( (1, ((sid,'F_clock'), ('RoundOK',))) )
    fro,msg = wait_for(p2z)
    print('\033[1mOK from f_clock after OK from 1\033[0m', msg)
    z2a.write( ('A2F', ((sid,'F_clock'),('get-leaks',))) )
    fro,msg = wait_for(a2z)
    print('\033[1m\tAdversary leak on OK from 1\033[0m', msg)

    z2p.write( (2, ((sid,'F_clock'), ('RequestRound',))) )
    fro,(to,msg) = wait_for(p2z)
    print('\033[1m\tRound from F_clock for 2\033[0m', msg)

if __name__=='__main__':
    test()
