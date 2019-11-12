import os
import sys
from gevent.queue import Queue, Channel, Empty
from gevent.event import AsyncResult
import dump
import gevent
import comm
from utils import gwrite, z_write

class ITMFunctionality(object):

    def __init__(self, sid, pid, a2f, f2f, p2f):
        self.sid = sid
        self.pid = pid
        self.sender = (sid,pid)
        self.a2f = a2f; self.p2f = p2f; self.f2f = f2f

        self.input = AsyncResult()
        self.subroutine = AsyncResult()
        self.backdoor = AsyncResult()
        self.f2c = None; self.clock = None
       
    def __str__(self):
        return str(self.F)

    def init(self, functionality):
        self.F = functionality
        self.outputs = self.F.outputs

    def set_clock(self, f2c, clock):
        self.f2c = f2c; self.clock = clock
        self.F.set_clock(f2c, clock)

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
                self.F.input_msg(sender, msg)   
                self.p2f.reset()
            else: print('eLsE dUmPiNg LiKe A rEtArD'); dump.dump()

class ITMFunctionality2(object):

    def __init__(self, sid, pid, a2f, f2a, z2f, f2z, p2f, f2p, f2f):
        self.sid = sid
        self.pid = pid
        self.sender = (sid,pid)

        self.input = AsyncResult()
        self.subroutine = AsyncResult()
        self.backdoor = AsyncResult()
        self.f2c = None; self.clock = None
       
    def __str__(self):
        return str(self.F)

    def init(self, functionality):
        self.F = functionality
        self.outputs = self.F.outputs

    def set_clock(self, f2c, clock):
        self.f2c = f2c; self.clock = clock
        self.F.set_clock(f2c, clock)

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
                self.F.input_msg(sender, msg)   
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
        self.extras = []
        self.p2c = None; self.clock = None

    def __str__(self):
        return str(self.F)
    
    def init(self, functionality):
        self.F = functionality
        self.outputs = self.F.outputs

    def set_clock(self, p2c, clock):
        self.p2c = p2c; self.clock = clock
        self.F.set_clock(p2c, clock)

    def clock_update(self):
        self.p2c.write(('clock-update',))

    def clock_register(self):
        self.p2c.write(('register',))

    def clock_read(self):
        return self.clock.subroutine_msg( self.sender, ('clock-read',))

    def subroutine_call(self, inp):
        sender,reveal,msg = inp
        return self.F.subroutine_msg(sender if reveal else None, msg)

    def add_channels(self, *channels):
        for channel in channels:
            self.extras.append(channel)

    def input_write(self, p2_, msg):
        p2_.write( msg )

    def run(self):
        while True:
            ready = gevent.wait(
                objects=[self.a2p, self.z2p, *self.extras],
                count=1
            )
            assert len(ready) == 1
            r = ready[0]
            msg = r.read()
            if r == self.a2p:
                self.F.adversary_msg( msg )
                self.a2p.reset()
            elif r == self.z2p:
                if msg[0] == 'clock-update':
                    self.clock_update()
                elif msg[0] == 'register':
                    self.clock_register()
                elif msg[0] == 'write':
                    self.input_write(msg[1], msg[2])
                else:
                    self.F.input_msg((-1,-1), msg)
                    self.z2p.reset()
            elif r in self.extras:
                sender,_,_msg = msg
                self.F.input_msg(sender,_msg)
                for _r in self.extras: _r.reset()
            else: print('else dumping at itmprotocol'); dump.dump()


class ITMPassthrough(object):

    def __init__(self, sid, pid, a2p, p2f, z2p):
        self.sid = sid
        self.pid = pid
        self.sender = (sid,pid)

        self.a2p = a2p; self.p2f = p2f; self.z2p = z2p 
        self.p2c = None; self.clock = None

        self.input = AsyncResult()
        self.subroutine = AsyncResult()
        self.backdoor = AsyncResult()
        self.outputidx = 0
       
    def __str__(self):
        return '\033[1mITM(%s, %s)\033[0m' % (self.sid, self.pid)

    def write(self, to, msg):
        gwrite(u'1m', 'ITM(%s, %s)'%(self.sid,self.pid), to, msg)

    def init(self, functionality):
        self.F = functionality
        self.outputs = self.F.outputs

    def set_clock(self, p2c, clock):
        self.p2c = p2c; self.clock = clock

    def clock_update(self):
        self.p2c.write(('clock-update',))

    def clock_register(self):
        self.p2c.write(('register',))

    def clock_read(self):
        return self.clock.subroutine_msg( self.sender, ('clock-read',))

    def subroutine_call(self, inp):
        sender,reveal,msg = inp
        if msg[0] == 'read':
            return self.subroutine_read()
        else:
            return self.F.subroutine_call((
                (self.sid, self.pid),
                True,
                msg
            ))
   
    def ping(self):
        o = self.F.subroutine_call((
            (self.sid, self.pid),
            True,
            ('read',)
        ))
        if o:
            z_write((self.sid,self.pid), o)
        dump.dump()

    def subroutine_read(self):
        outputs = self.F.subroutine_call( (self.sender, True, ('read',)))
        for o in outputs[self.outputidx:]:
            z_write( (self.sid,self.pid), o )
        self.outputidx = len(outputs)
    
    def input_write(self, p2_, msg):
        p2_.write( msg )

    def run(self):
        while True:
            ready = gevent.wait(
                objects=[self.a2p, self.z2p],
                count=1
            )

            assert len(ready) == 1
            r = ready[0]
            msg = r.read()
            if r == self.z2p:
                #print('PASSTHROUGH MESSAGE', msg) 
                if msg[0] == 'ping':
                    self.ping()
                elif msg[0] == 'write':
                    self.input_write(msg[1], msg[2])
                elif msg[0] == 'clock-update':
                    self.clock_update()
                elif msg[0] == 'register':
                    self.clock_register()
                else:
                    self.write(self.F, msg)
                    self.p2f.write( msg )
                self.z2p.reset()
            elif r == self.a2p:
                comm.corrupt(self.sid, self.pid)
                self.write(self.F, msg)
                self.p2f.write( msg )
                self.a2p.reset()
            else:
                print('else dumping somewhere ive never been'); dump.dump()


def createParties(sid, r, f, a2ps, p2fs, z2ps):
    parties = []
    for i,a2p,p2f,z2p in zip(r, a2ps, p2fs, z2ps):
        p = ITMPassthrough(sid,i,a2p,p2f,z2p)
        p.init(f)
        parties.append(p)
    return parties

class ITMPassthrough2(object):

    def __init__(self, sid, pid, z2p, p2z, f2p, p2f):
        self.sid = sid
        self.pid = pid
        self.sender = (sid,pid)

        self.z2p = z2p; self.p2z = p2z
        self.f2p = f2p; self.p2f = p2f
        #self.a2p = a2p; self.p2f = p2f; self.z2p = z2p 
        #self.p2c = None; self.clock = None

        self.input = AsyncResult()
        self.subroutine = AsyncResult()
        self.backdoor = AsyncResult()
        self.outputidx = 0
       
    def __str__(self):
        return '\033[1mITM(%s, %s)\033[0m' % (self.sid, self.pid)

    def write(self, to, msg):
        gwrite(u'1m', 'ITM(%s, %s)'%(self.sid,self.pid), to, msg)

    def init(self, functionality):
        self.F = functionality
        self.outputs = self.F.outputs

    def set_clock(self, p2c, clock):
        self.p2c = p2c; self.clock = clock

    def clock_update(self):
        self.p2c.write(('clock-update',))

    def clock_register(self):
        self.p2c.write(('register',))

    def clock_read(self):
        return self.clock.subroutine_msg( self.sender, ('clock-read',))

    def subroutine_call(self, inp):
        sender,reveal,msg = inp
        if msg[0] == 'read':
            return self.subroutine_read()
        else:
            return self.F.subroutine_call((
                (self.sid, self.pid),
                True,
                msg
            ))
   
    def ping(self):
        o = self.F.subroutine_call((
            (self.sid, self.pid),
            True,
            ('read',)
        ))
        if o:
            z_write((self.sid,self.pid), o)
        dump.dump()

    def subroutine_read(self):
        outputs = self.F.subroutine_call( (self.sender, True, ('read',)))
        for o in outputs[self.outputidx:]:
            z_write( (self.sid,self.pid), o )
        self.outputidx = len(outputs)
    
    def input_write(self, p2_, msg):
        p2_.write( msg )

    def run(self):
        while True:
            ready = gevent.wait(
                objects=[self.a2p, self.z2p],
                count=1
            )

            assert len(ready) == 1
            r = ready[0]
            msg = r.read()
            if r == self.z2p:
                #print('PASSTHROUGH MESSAGE', msg) 
                if msg[0] == 'ping':
                    self.ping()
                elif msg[0] == 'write':
                    self.input_write(msg[1], msg[2])
                elif msg[0] == 'clock-update':
                    self.clock_update()
                elif msg[0] == 'register':
                    self.clock_register()
                else:
                    self.write(self.F, msg)
                    self.p2f.write( msg )
                self.z2p.reset()
            elif r == self.a2p:
                comm.corrupt(self.sid, self.pid)
                self.write(self.F, msg)
                self.p2f.write( msg )
                self.a2p.reset()
            else:
                print('else dumping somewhere ive never been'); dump.dump()

class PartyWrapper:
    def __init__(self, sid, z2p, p2z, f2p, p2f, a2p, p2a):
        self.sid = sid
        self.z2pid = {}
        self.f2pid = {}

    def _newPID(self, pid, _2pid, p2_, tag):
        pp2_ = comm.GenChannel() 
        _2pp = comm.GenChannel() # _ to 

        def _translate():
            while True:
                r = gevent.wait(objects=[pp2_],count=1)
                r = r[0]
                msg = r.read()
                p2_.write( (pid, msg) )

        _2pid[pid] = _2pp
        return (_2pp, pp2_) 


    def newPID(self, pid):
        print('[{}] Creating new party with pid: {}'.format(self.sid, pid))
        _z2p,_p2z = self._newPID(pid, self.z2pid, self.p2z, 'NA')
        _f2p,_p2f = self._newPID(pid, self.f2pid, self.p2f, 'NA')
        
        itm = ITMPassthrough(sid, pid, _z2p, _p2z, _f2p, _p2f) 
        gevent.spawn(itm.run)

    def getPID(self, _2pid, pid):
        if pid in _2pid: return _2pid[pid]
        else:
            self.newPID(pid)
            return _2pid[pid]

    def run(self):
        while True:
            ready = gevent.wait(objects=[self.z2p, self.f2p, self.a2p], count=1)
            assert len(ready) == 1
            r = ready[0]
            (pid, msg) = r.get() 
            if r == self.z2p:
                # TODO reject if corrupted party
                _pid = self.getPID(self.z2pid,pid)
                _pid.write(msg)
                self.z2p.reset()
            elif r == self.f2p:
                _pid = self.getPID(self.f2pid,pid)
                _pid.write(msg)
                self.f2p.reset()
            elif r == self.a2p:
                # TODO if not corrupt, crash
                self.p2f.write((pid,msg))
            else:
                dump.dump()

#class FunctionalityWrapper:
#    def __init__(self, p2f, f2p, a2f, f2a, z2f, f2z):
#        self.z2pid = {}
#        self.p2pid = {}
#
#    def _newFID(self, _2fid, f2_, sid, tag):
#        ff2_ = comm.GenChannel()
#        _2ff = comm.GenChannel()
#
#        def _translate():
#            while True:
#                r = gevent.wait(objects=[ff2_],count=1)
#                r = r[0]
#                msg = r.read()
#                f2_.write( ((sid,tag), msg) )
#
#        _2fid[pid] = _2ff
#        return (_2ff, ff2_) 
#
#
#    def newFID(self, sid, tag):
#        print('[{}] Creating new party with pid: {}'.format(sid, tag))
#        _z2f,_f2z = self._newFID(self.z2fid, self.f2z, sid, tag)
#        _p2f,_f2p = self._newFID(self.f2fid, self.f2p, sid, tag)
#       
#        if tag == 'G_ledger':
#            g_ledger, LedgerFuntionality(sid, -1)
#            pwrapper = ProtectedWrapper(g_ledger)
#            pitm = ITMFunctionality2(sid,-1,
#        elif tag == 'F_multicast':
#        elif tag == 'F_state':
#        itm = ITMFunctionality(sid, pid, _z2p, _p2z, _f2p, _p2f) 
#        gevent.spawn(itm.run)
#
#    def getPID(self, _2pid, sid,tag):
#        if (sid,tag) in _2pid return _2pid[sid,tag]:
#        else:
#            self.newPID(self, sid, tag)
#            return _2pid[sid,tag]
#
#    def run(self):
#        while True:
#            ready = gevent.wait(objects=[self.z2p, self.f2p, self.a2p], count=1)
#            assert len(ready) == 1
#            r = ready[0]
#            (pid, msg) = r.get() 
#            if r == self.z2p:
#                # TODO reject if corrupted party
#                _pid = self.getPID(self.z2pid,pid)
#                _pid.write(msg)
#                self.z2p.reset()
#            elif r == self.f2p:
#                _pid = self.getPID(self.f2pid,pid)
#                _pid.write(msg)
#                self.f2p.reset()
#            elif r == self.a2p:
#                # TODO if not corrupt, crash
#                self.p2f.write((pid,msg))
#            else:
#                dump.dump()

class DefaultSim(object):
    def __init__(self, sid, pid, G, a2g):
        self.sid = sid; self.pid = pid
        self.sender = (sid,pid)
        self.G = G
        self.a2g = a2g

    def __str__(self):
        return '\033[91mDefaultSim (%s, %s)\033[0m' % (self.sid,self.pid)

    def write(self, to, msg):
        gwrite(u'91m', 'DefaultSim (%s,%s)'%(self.sid,self.pid), to, msg)

    def input_tick(self, permutation):
        msg = (self.sender, True, (True, ('tick', perm)))
        self.write(self.G, msg)
        self.a2g.write( (True, ('tick', perm)) )


    def input_msg(self, msg):
        if msg[0] == 'tick':
            self.input_tick(msg[1])
        else:
            dump.dump()
    
class ITMAdversary(object):
    def __init__(self, sid, pid, z2a, z2p, a2f, a2g):
        self.sid = sid
        self.pid = pid
        self.sender = (sid,pid)
        self.z2a = z2a
        self.z2p = z2p
        self.a2f = a2f
        self.a2g = a2g
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

    def addParty(self, itm):
        if (itm.sid,itm.pid) not in self.parties:
            self.parties[itm.sid,itm.pid] = itm

    def addParties(self, itms):
        for itm in itms:
            self.addParty(itm)

    def partyInput(self, to, msg):
        self.F.input_msg(('party-input', to, msg))

    def input_delay_tx(self, fro, nonce, rounds):
        msg = ('delay-tx', fro, nonce, rounds)
        self.write(self.F.G, msg)
        self.a2g.write((
            (False, msg)
        ))

    def input_ping(self):
        self.write(self.F.F, ('ping',))
        self.F.F.backdoor.set(( self.sender, True, ('ping,') ))

    def getLeaks(self, sid, pid):
        assert comm.isf(sid,pid)
        itm = comm.getitm(sid,pid)
        msg = ('get-leaks',)
        self.F.write(itm, msg)
        self.a2g.write((
            (True, msg)
        ))

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
                objects=[self.z2a, self.leak],
                count=1
            )

            assert len(ready) == 1
            r = ready[0]
            if r == self.z2a:
                msg = r.read()
                if msg[0] == 'party-input':
                    self.partyInput(msg[1], msg[2])
                elif msg[0] == 'get-leaks':
                    sid,pid = msg[1]
                    self.getLeaks(sid, pid)
                elif msg[0] == 'delay-tx':
                    self.input_delay_tx(msg[1], msg[2], msg[3])
                elif msg[0] == 'ping':
                    self.input_ping(msg[1], msg[2])
                else:
                    self.F.input_msg(msg)
                self.input = AsyncResult()
            elif r == self.leak:
                msg = r.get()
                sender,msg = msg
                sid,pid = sender
                assert comm.isf(sid,pid)
                self.leakbuffer.append(msg)
                dump.dump()
                self.leak = AsyncResult()
            else:
                print('else dumping right after leak'); dump.dump()

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

            r = AsyncResult()

