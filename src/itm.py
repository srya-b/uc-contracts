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

    def __init__(self, sid, pid):
        self.sid = sid
        self.pid = pid

        self.input = AsyncResult()
        self.subroutine = AsyncResult()
        self.backdoor = AsyncResult()
        
    def init(self, functionality):
        self.F = functionality
        self.outputs = self.F.outputs

    def subroutine_call(self, inp):
        sender,reveal,msg = inp
        return self.F.subroutine_msg(sender if reveal else None, msg)


    def run(self):
        while True:
            ready = gevent.wait(
                objects=[self.input, self.backdoor],
                count=1
            )
            
            assert len(ready) == 1
            r = ready[0]
            sender,reveal,msg = r.get()
            if r == self.input:
                #print('MSG', msg)
                self.F.input_msg(None if not reveal else sender, msg)
            elif r == self.backdoor:
                self.F.adversary_msg(None if not reveal else sender, msg)
            else:
                dump.dump()

            r = AsyncResult()

class ITMPassthrough(object):

    def __init__(self, sid, pid):
        self.sid = sid
        self.pid = pid
        
        self.input = AsyncResult()
        self.subroutine = AsyncResult()
        self.backdoor = AsyncResult()
        
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
            ready = gevent.wait(
                objects=[self.input, self.backdoor],
                count=1
            )
            assert len(ready) == 1
            r = ready[0]
            msg = r.get()
            
            if r == self.input:
                self.F.input.set(
                    ((self.sid,self.pid), True, msg)
                )
            elif r == self.backdoor:
                print('adversary gave input, guess im evil now')
                comm.corrupt(self.sid, self.pid)
                self.F.input.set(
                    ((self.sid, self.pid), True, msg)
                )
            else:
                dump.dump() 

            r = AsyncResult()

def createParties(sid, r, f):
    parties = []
    for i in r:
        p = ITMPassthrough(sid,i)
        p.init(f)
        parties.append(p)
    return parties

class ITMAdversary(object):
    def __init__(self, sid, pid):
        self.sid = sid
        self.pid = pid
        #self.input = Channel()
        self.input = AsyncResult()
        self.leak = AsyncResult()
        self.parties = {}
        
    def init(self, functionality):
        self.F = functionality
        self.outputs = self.F.outputs

    def addParty(self, itm):
        if (itm.sid,itm.pid) not in self.parties:
            self.parties[itm.sid,itm.pid] = itm

    def partyInput(self, sid, pid, msg):
        print(sid, pid, msg)
        if (sid,pid) in self.parties:
            print('sending to party....')
            party = self.parties[sid,pid]
            party.backdoor.set(msg)
        else:
            dump.dump()

    def run(self):
        while True:
            ready = gevent.wait(
                objects=[self.input, self.leak],
                count=1
            )

            assert len(ready) == 1
            r = ready[0]
            msg = r.get()

            if r == self.input:
                if msg[0] == 'party-input':
                    #msg = r.get()
                    sid,pid = msg[1]
                    self.partyInput(sid, pid, msg[2])
                    #dump.dump()
                else:
                    sender,reveal,msg = msg
                    print('[ADVERSARY]', sender, reveal, msg)
                    self.F.backdoor_msg(None if not reveal else sender, msg)
            elif r == self.leak:
                sender,reveal,msg = msg
                print('[LEAK]', sender, msg)
                dump.dump()
            else:
                dump.dump()

            r = AsyncResult()

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

