import os
import sys
from gevent.queue import Queue, Channel, Empty
from gevent.event import AsyncResult
import identity
import dump
import gevent
import comm
from utils import print

class ITMFunctionality(object):

    def __init__(self, sid, pid, a2f, f2f, p2f):
        self.sid = sid
        self.pid = pid
        self.sender = (sid,pid)
        self.a2f = a2f; self.p2f = p2f; self.f2f = f2f

        self.input = AsyncResult()
        self.subroutine = AsyncResult()
        self.backdoor = AsyncResult()
       
    def __str__(self):
        return str(self.F)

    def init(self, functionality):
        self.F = functionality
        self.outputs = self.F.outputs

    def subroutine_call(self, inp):
        sender,reveal,msg = inp
        return self.F.subroutine_msg(sender if reveal else None, msg)

    def run(self):
        while True:
            ready = gevent.wait(
                objects=[self.f2f, self.p2f, self.a2f],
                count=1
            )
            assert len(ready) == 1
            r = ready[0]
            sender,reveal,msg = r.read()
            if r == self.f2f:
                self.F.input_msg(None if not reveal else sender, msg)
                self.f2f.reset()
            elif r == self.a2f:
                self.F.adversary_msg(msg)
                self.a2f.reset()
            elif r == self.p2f:
                self.F.input_msg(None if not reveal else sender, msg)
                self.p2f.reset()
            else: print('eLsE dUmPiNg LiKe A rEtArD'); dump.dump()


class ITMProtocol(object):

    def __init__(self, sid, pid, a2p, p2f, z2p):
        self.sid = sid
        self.pid = pid
        self.a2p = a2p; self.p2f = p2f; self.z2p = z2p
        self.sender = (sid,pid)
        self.input = AsyncResult()
        self.subroutine = AsyncResult()
        self.backdoor = AsyncResult()
       
    def __str__(self):
        return str(self.F)
    
    def init(self, functionality):
        self.F = functionality
        self.outputs = self.F.outputs

    def subroutine_call(self, inp):
        sender,reveal,msg = inp
        return self.F.subroutine_msg(sender if reveal else None, msg)

    def run(self):
        while True:
            #ready = gevent.wait(
            #    objects=[self.input, self.backdoor],
            #    count=1
            #)
            ready = gevent.wait(
                objects=[self.a2p, self.z2p],
                count=1
            )
            assert len(ready) == 1
            r = ready[0]
            msg = r.read()
            if r == self.a2p:
                self.F.adversary_msg( msg )
                self.a2p.reset()
            elif r == self.z2p:
                print('ENVIRONMENT INPUT', msg)
                self.F.input_msg(self.sender, msg)
                self.z2p.reset()
            else: print('else dumping at itmprotocol'); dump.dump()


            #sender,reveal,msg = r.get()
            #if r == self.input:
            #    self.F.input_msg(None if not reveal else sender, msg)
            #    self.input = AsyncResult()
            #elif r == self.backdoor:
            #    self.F.adversary_msg(None if not reveal else sender, msg)
            #    self.backdoor = AsyncResult()
            #else:
            #    dump.dump()

class ITMPassthrough(object):

    def __init__(self, sid, pid, a2p, p2f, z2p):
        self.sid = sid
        self.pid = pid
        self.sender = (sid,pid)

        self.a2p = a2p; self.p2f = p2f; self.z2p = z2p 

        self.input = AsyncResult()
        self.subroutine = AsyncResult()
        self.backdoor = AsyncResult()
       
    def __str__(self):
        return '\033[1mITM(%s, %s)\033[0m' % (self.sid, self.pid)

    def write(self, to, msg):
        print('\033[1m{:>20}\033[0m -----> {}, msg={}'.format('ITM(%s, %s)' % (self.sid,self.pid), str(to), msg))
        #print('%s:<15 -----> %s\tmsg=%s' % (str(self), str(to), msg))

    def init(self, functionality):
        self.F = functionality
        self.outputs = self.F.outputs

    def subroutine_call(self, inp):
        return self.F.subroutine_call((
            (self.sid, self.pid),
            True,
            inp
        ))
    
    def run(self):
        while True:
            #ready = gevent.wait(
            #    objects=[self.input, self.backdoor],
            #    count=1
            #)
            ready = gevent.wait(
                objects=[self.a2p, self.z2p],
                count=1
            )

            assert len(ready) == 1
            r = ready[0]
            msg = r.read()
            if r == self.z2p:
                #print('PASSTHROUGH MESSAGE', msg) 
                self.write(self.F, msg)
                self.p2f.write( msg )
                #dump.dump(); continue
                self.z2p.reset()
            elif r == self.a2p:
                comm.corrupt(self.sid, self.pid)
                self.write(self.F, msg)
                self.p2f.write( msg )
                self.a2p.reset()
            else:
                print('else dumping somewhere ive never been'); dump.dump()

            #if r == self.input:
            #    self.write(self.F, msg)
            #    self.F.input.set(
            #        ((self.sid,self.pid), True, msg)
            #    )
            #    self.input = AsyncResult()
            #elif r == self.backdoor:
            #    comm.corrupt(self.sid, self.pid)
            #    self.write(self.F, msg)
            #    self.F.input.set(
            #        ((self.sid, self.pid), True, msg)
            #    )
            #    self.backdoor = AsyncResult()
            #else:
            #    dump.dump() 

            #r = AsyncResult()

def createParties(sid, r, f, a2ps, p2fs, z2ps):
    parties = []
    for i,a2p,p2f,z2p in zip(r, a2ps, p2fs, z2ps):
        p = ITMPassthrough(sid,i,a2p,p2f,z2p)
        p.init(f)
        parties.append(p)
    return parties

class ITMAdversary(object):
    def __init__(self, sid, pid, z2a, z2p, a2f, a2g):
        self.sid = sid
        self.pid = pid
        self.sender = (sid,pid)
        self.z2a = z2a
        self.z2p = z2p
        self.a2f = a2f
        self.a2g = a2g
        #self.input = Channel()
        self.input = AsyncResult()
        self.leak = AsyncResult()
        self.parties = {}
        self.leakbuffer = []
    
    def __str__(self):
        return str(self.F)

    def read(self, fro, msg):
        print(u'{:>20} -----> {}, msg={}'.format(str(fro), str(self), msg))

    def write(self, to, msg):
        self.F.write(to, msg)

    def init(self, functionality):
        self.F = functionality
#        self.outputs = self.F.outputs

    def addParty(self, itm):
        if (itm.sid,itm.pid) not in self.parties:
            self.parties[itm.sid,itm.pid] = itm

    def addParties(self, itms):
        for itm in itms:
            self.addParty(itm)

    def partyInput(self, to, msg):
        self.F.input_msg(('party-input', to, msg))
        #if (sid,pid) in self.parties:
        #    print('sending to party....')
        #    party = self.parties[sid,pid]
        #    party.backdoor.set(msg)
        #else:
        #    dump.dump()

    def input_delay_tx(self, fro, nonce, rounds):
        msg = ('delay-tx', fro, nonce, rounds)
        self.write(self.F.G, msg)
        self.a2g.write((
            (False, msg)
        ))
        #self.F.G.backdoor.set((
        #    self.sender, True, (False, msg)
        #))

    def input_ping(self):
        self.write(self.F.F, ('ping',))
        self.F.F.backdoor.set(( self.sender, True, ('ping,') ))

    def getLeaks(self, sid, pid):
        assert comm.isf(sid,pid)
        itm = comm.getitm(sid,pid)
        msg = ('get-leaks',)
        self.F.write(itm, msg)
        #print('GET LEAKS', msg)
        #itm.backdoor.set((
        self.a2g.write((
            (True, msg)
        ))
        #    (self.sid,self.pid),
        #    True,
        #    (True, msg)
        #))

        #self.read(itm, leaks[0]) 

        #print('Leaks from (%s,%s):' % (sid,pid))
        #print(leaks, sep='\n')

    '''
        Instead of waiting for a party to write to the adversary
        the adversary checks leak queues of all the parties in 
        a loop and acts on the first message that is seen. The
        environment can also tell the adversary to get all of the
        messages from a particular ITM.
    '''
    def run(self):
        while True:
            #ready = gevent.wait(
            #    objects=[self.input, self.leak],
            #    count=1
            #)

            ready = gevent.wait(
                objects=[self.z2a, self.leak],
                count=1
            )

            assert len(ready) == 1
            r = ready[0]
            #msg = r.get()

            #if r == self.input:
            if r == self.z2a:
                msg = r.read()
                if msg[0] == 'party-input':
                    #msg = r.get()
                    #sid,pid = msg[1]
                    self.partyInput(msg[1], msg[2])
                    #dump.dump()
                elif msg[0] == 'get-leaks':
                    sid,pid = msg[1]
                    self.getLeaks(sid, pid)
                elif msg[0] == 'delay-tx':
                    self.input_delay_tx(msg[1], msg[2], msg[3])
                elif msg[0] == 'ping':
                    print('Ping at ITM level')
                    self.input_ping(msg[1], msg[2])
                else:
                    #sender,reveal,msg = msg
                    #print('[ADVERSARY]', sender, reveal, msg)
                    #self.F.backdoor_msg(None if not reveal else sender, msg)
                    #self.F.input.set((
                    #    (self.sid,self.pid),
                    #    True,
                    #    msg
                    #))
                    self.F.input_msg(msg)
                    #dump.dump()
                self.input = AsyncResult()
            elif r == self.leak:
                msg = r.get()
                #print('processing leaks')
                sender,msg = msg
                sid,pid = sender
                assert comm.isf(sid,pid)
                #print('leak leaks', self.leakbuffer)
                self.leakbuffer.append(msg)
                #print('leak leaks', self.leakbuffer)
                print('elif r == self.leak'); dump.dump()
                self.leak = AsyncResult()
            else:
                print('else dumping right after leak'); dump.dump()

            #r = AsyncResult()

def createAdversary(sid,pid,f):
    a = ITMAdversary(sid,pid)
    a.init(f)
    return a
    
class ITMPrinterAdversary(object):
    def __init__(self, sid, pid):
        self.sid = sid
        self.pid = pid
        #self.input = Channel()
        self.input = AsyncResult()
        self.leak = AsyncResult()
        self.corrupted = set()
        
    def init(self, functionality):
        self.F = functionality
        self.outputs = self.F.outputs

    def corrupt(self, pid):
        self.corrupted.add(pid)
        comm.corrupt(self.sid, pid)
        dump.dump()

    def run(self):
        while True:
            ready = gevent.wait(
                objects=[self.input, self.leak],
                count=1
            )

            assert len(ready) == 1
            r = ready[0]
            sender,reveal,msg = r.get()
            print('[ADVERSARY]', sender, reveal, msg)

            if r == self.input:
                if msg[0] == 'corrupt':
                    self.corrupt(msg[1])
                else:
                    dump.dump()
            else:
                dump.dump()

            #if r == self.input:
            #    self.F.backdoor_msg(None if not reveal else sender, msg)
            #elif r == self.leak:
            #    print('[LEAK]', sender, msg)
            #    dump.dump()
            #else:
            #    dump.dump()

            r = AsyncResult()

