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
                objects=[self.input, self.backdoor],
                count=1
            )
            
            assert len(ready) == 1
            r = ready[0]
            sender,reveal,msg = r.get()
            #print('Ready before, input={}, backdoor={}'.format(self.input.ready(),self.backdoor.ready()))
            if r == self.input:
                self.F.input_msg(None if not reveal else sender, msg)
                self.input = AsyncResult()
            elif r == self.backdoor:
                self.F.adversary_msg(None if not reveal else sender, msg)
                self.backdoor = AsyncResult()
            else:
                dump.dump()
            #print('DEFINITELY ABOUT TO RESET THE INOUT')
            #print('Ready right before, input={}, backdoor={}'.format(self.input.ready(),self.backdoor.ready()))
            #print('Equal, (self.input==r)={}, (self.backdoor==r)={}'.format(self.input==r, self.backdoor==r))
            #r = AsyncResult()
            #print('Ready after, input={}, backdoor={}, r={}'.format(self.input.ready(),self.backdoor.ready(), r.ready()))

class ITMPassthrough(object):

    def __init__(self, sid, pid):
        self.sid = sid
        self.pid = pid
        
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
            ready = gevent.wait(
                objects=[self.input, self.backdoor],
                count=1
            )
            assert len(ready) == 1
            r = ready[0]
            msg = r.get()
            
            if r == self.input:
                self.write(self.F, msg)
                self.F.input.set(
                    ((self.sid,self.pid), True, msg)
                )
                self.input = AsyncResult()
            elif r == self.backdoor:
                comm.corrupt(self.sid, self.pid)
                self.write(self.F, msg)
                self.F.input.set(
                    ((self.sid, self.pid), True, msg)
                )
                self.backdoor = AsyncResult()
            else:
                dump.dump() 

            #r = AsyncResult()

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
        self.leakbuffer = []
    
    def __str__(self):
        return str(self.F)

    def read(self, fro, msg):
        print(u'{:>20} -----> {}, msg={}'.format(str(fro), str(self), msg))

    def init(self, functionality):
        self.F = functionality
#        self.outputs = self.F.outputs

    def addParty(self, itm):
        if (itm.sid,itm.pid) not in self.parties:
            self.parties[itm.sid,itm.pid] = itm

    def addParties(self, itms):
        for itm in itms:
            self.addParty(itm)

    def partyInput(self, sid, pid, msg):
        if (sid,pid) in self.parties:
            print('sending to party....')
            party = self.parties[sid,pid]
            party.backdoor.set(msg)
        else:
            dump.dump()

    def getLeaks(self, sid, pid):
        assert comm.isf(sid,pid)
        itm = comm.getitm(sid,pid)
        msg = ('get-leaks',)
        self.F.write(itm, msg)
        itm.backdoor.set((
            (self.sid,self.pid),
            True,
            (True, msg)
        ))

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
                elif msg[0] == 'get-leaks':
                    sid,pid = msg[1]
                    self.getLeaks(sid, pid)
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
                print('processing leaks')
                sender,msg = msg
                sid,pid = sender
                assert comm.isf(sid,pid)
                print('leak leaks', self.leakbuffer)
                self.leakbuffer.append(msg)
                print('leak leaks', self.leakbuffer)
                dump.dump()
                self.leak = AsyncResult()
            else:
                dump.dump()

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

