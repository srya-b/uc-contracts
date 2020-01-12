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

    def __init__(self, sid, pid, a2f, f2a, z2f, f2z, p2f, f2p, _2f, f2_):
        self.sid = sid
        self.pid = pid
        self.sender = (sid,pid)
        self.a2f = a2f; self.f2a = f2a
        self.z2f = z2f; self.f2z = f2z
        self.p2f = p2f; self.f2p = f2p
        self._2f = _2f; self.f2_ = f2_

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
                objects=[self.p2f, self.a2f, self._2f],
                count=1
            )
            assert len(ready) == 1
            r = ready[0]
            #if r == self.f2f:
            #    self.F.input_msg(None if not reveal else sender, msg)
            #    self.f2f.reset()
            if r == self.a2f:
                if self.pid == 'F_state':
                    self.a2f.reset()
                    print('Shit'); dump.dump(); continue
                msg = r.read()
                self.a2f.reset()
                self.F.adversary_msg(msg)
            elif r == self.p2f: 
                sender,reveal,msg = r.read()    
                self.p2f.reset()
                self.F.input_msg(sender, msg)   
            elif r == self._2f:
                ((_sid,_tag), msg) = r.read()
                self._2f.reset()
                #print('HOLY SHIT GOT THIS MESSAGE', msg) 
                #self.f2_.write( ((_sid,_tag), 'MASSA COLONEL YOU A BITCH NIGGA') )
                self.F.input_msg((_sid,_tag), msg)
            else: print('eLsE dUmPiNg LiKe A rEtArD'); dump.dump()



class ITMProtocol(object):

    #def __init__(self, sid, pid, a2p, p2f, z2p):
    def __init__(self, sid, pid, a2p, p2a, z2p, p2z, f2p, p2f, _2p, p2_):
        self.sid = sid
        self.pid = pid
        self.a2p = a2p; self.p2a = p2a
        self.p2f = p2f; self.f2p = f2p
        self.z2p = z2p; self.p2z = p2z
        self._2p = _2p; self.p2_ = p2_
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
                objects=[self.a2p, self.z2p, self.f2p, self._2p, *self.extras],
                count=1
            )
            assert len(ready) == 1
            r = ready[0]
            if r == self.a2p:
                to,msg = r.read()
                self.a2p.reset()
                print('Adversary mesage', to, msg)
                if to == 'P':
                    #to,msg = msg
                    self.F.adversary_msg( msg )
                else:
                    sid,pid = to
                    #self.F.adversary_msg( msg )
                    if comm.isf(sid,pid):
                        self.p2f.write( (to, msg) )
                    elif comm.isparty(sid,pid):
                        self.p2_.write( (to, msg) )
                    else: raise Exception
                #self.F.input_msg( msg )
            elif r == self.z2p:
                t,msg = r.read()
                self.z2p.reset()
                if t == 'P2F':
                    to,msg = msg
                    self.p2f.write( (to,msg) )
                else:
                    if msg[0] == 'clock-update':
                        self.clock_update()
                    elif msg[0] == 'register':
                        self.p2f.write( (t,msg) )
                        #self.clock_register()
                    elif msg[0] == 'write':
                        self.input_write(msg[1], msg[2])
                    else:
                        self.F.input_msg((-1,-1), msg)
                        #self.z2p.reset()
            elif r == self._2p:
                fro,msg = r.read()
                self._2p.reset()
                self.F.input_msg( fro, msg )
            elif r == self.f2p:
                m = r.read()
                #print('Some f2p for that ass')
                #print('f2p message', m)
                fro,msg = m
                self.f2p.reset()
                self.F.input_msg( fro, msg )
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
    def __init__(self, sid, pid, a2p, p2a, z2p, p2z, f2p, p2f):
        self.sid = sid
        self.pid = pid
        self.sender = (sid,pid)

        self.z2p = z2p; self.p2z = p2z
        self.f2p = f2p; self.p2f = p2f###
        self.a2p = a2p; self.p2a = p2a
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
                #objects=[self.a2p, self.z2p],
                objects=[self.z2p, self.a2p, self.f2p],
                count=1
            )
            assert len(ready) == 1
            r = ready[0]
            msg = r.read()
            if r == self.z2p:
                if comm.isdishonest(self.sid, self.pid):
                    self.z2p.reset()
                    assert False
                print('PASSTHROUGH MESSAGE', msg) 
                if msg[0] == 'ping':
                    self.ping()
                elif msg[0] == 'write':
                    self.input_write(msg[1], msg[2])
                elif msg[0] == 'clock-update':
                    self.clock_update()
                elif msg[0] == 'register':
                    self.clock_register()
                else:
                    self.p2f.write( msg )
                self.z2p.reset('z2p in itm')
            elif r == self.a2p:
                self.a2p.reset()
                if comm.ishonest(self.sid, self.pid):
                    assert False
                #print('\n\t alright then', msg)
                self.p2f.write( msg )
                #self.p2f.write( msg )
                #dump.dump()
            elif r == self.f2p:
                self.f2p.reset()
                print('F 2 P message in ITM', msg, self.sid, self.pid)
                if comm.ishonest(self.sid,self.pid):
                    self.p2z.write( msg )
                else:
                    self.p2a.write( msg )
            else:
                print('else dumping somewhere ive never been'); dump.dump()

from comm import setFunctionality2, setParty
class PartyWrapper:
    def __init__(self, sid, z2p, p2z, f2p, p2f, a2p, p2a ):
        self.sid = sid
        self.z2pid = {}
        self.f2pid = {}
        self.a2pid = {}
        self.z2p = z2p; self.p2z = p2z;
        self.f2p = f2p; self.p2f = p2f;
        self.a2p = a2p; self.p2a = p2a

    def _newPID(self, pid, _2pid, p2_, tag):
        pp2_ = comm.GenChannel(('write-translate',pid)) 
        _2pp = comm.GenChannel(('read',pid)) # _ to 

        def _translate():
            while True:
                r = gevent.wait(objects=[pp2_],count=1)
                r = r[0]
                msg = r.read()
                pp2_.reset('pp2_ translate reset')
                #print('\n\t Translating: {} --> {}'.format(msg, ((self.sid,pid),msg)))
                print('\t\t\033[96m {} --> {}, msg={}\033[0m'.format((self.sid,pid), msg[0], msg[1]))
                p2_.write( ((self.sid,pid), msg) )
        gevent.spawn(_translate)

        _2pid[pid] = _2pp
        return (_2pp, pp2_) 


    def newPID(self, pid):
        print('[{}] Creating new party with pid: {}'.format(self.sid, pid))
        _z2p,_p2z = self._newPID(pid, self.z2pid, self.p2z, 'NA')
        _f2p,_p2f = self._newPID(pid, self.f2pid, self.p2f, 'NA')
        _a2p,_p2a = self._newPID(pid, self.a2pid, self.p2a, 'NA')
        
        itm = ITMPassthrough2(self.sid, pid, _a2p, _p2a, _z2p, _p2z, _f2p, _p2f) 
        setParty(itm)
        gevent.spawn(itm.run)

    def getPID(self, _2pid, pid):
        if pid in _2pid: return _2pid[pid]
        else:
            self.newPID(pid)
            return _2pid[pid]

    def run(self):
        while True:
            print('\t\033[94mStatus: z2p={}, f2p={}, a2p={}\033[0m'.format(self.z2p.is_set(),self.f2p.is_set(),self.a2p.is_set()))
            ready = gevent.wait(objects=[self.z2p, self.f2p, self.a2p], count=1)
            #assert len(ready) == 1
            r = ready[0]
            (pid, msg) = r.read() 
            print('[{}] Message for ({}): {}'.format(self.sid, pid, msg))
            if r == self.z2p:
                self.z2p.reset('z2p party reset')
                if not comm.ishonest(self.sid,pid):
                    raise Exception
                # TODO reject if corrupted party
                # pass onto the functionality
                _pid = self.getPID(self.z2pid,pid)
                print('Part message', msg)
                _pid.write(msg)
                # TODO need to wait and try 
                r = gevent.wait(objects=[self.f2p],count=1,timeout=0.2)
                if r:
                    r = r[0]
                    #print('\n\nready early\n\n')
                    msg = r.read()
                    self.p2z.write(msg)
                    #print('SOME RESPONS', r.read())
                    # send response to z
                    self.f2p.reset('reset f2p in z2p')
            elif r == self.f2p:
                self.f2p.reset('f2p in party')
                _pid = self.getPID(self.f2pid,pid)
                _pid.write(msg)
            elif r == self.a2p:
                if comm.ishonest(self.sid,pid):
                    raise Exception
                self.a2p.reset('a2p in party')
                _pid = self.getPID(self.a2pid, pid)
                _pid.write( msg )
                r = gevent.wait(objects=[self.f2p], count=1, timeout=0.1)
                if r:
                    r = r[0]
                    msg = r.read()
                    self.p2a.write( msg )
                # TODO if not corrupt, crash
                #self.p2f.write((pid,msg))
            else:
                dump.dump()
        print('Its over??')

from collections import defaultdict

class ProtocolWrapper:
    def __init__(self, sid, z2p, p2z, f2p, p2f, a2p, p2a, prot):
        self.sid = sid
        self.z2pid = {}
        self.f2pid = {}
        self.a2pid = {}
        self.p2pid = {}
        self.z2p = z2p; self.p2z = p2z;
        self.f2p = f2p; self.p2f = p2f;
        self.a2p = a2p; self.p2a = p2a
        self.p2_ = comm.GenChannel()
        self.prot = prot
        self.leaks = defaultdict(list)

        # eventually_queue[x] = (msg, round, p2_)
        self.eventually_queue = defaultdict(tuple)
    
    def deliver(self, pid, msg):
        try:
            m,rnd,c = self.eventually_queue[pid]
            if msg == m:
                c.write( m )
        except ValueError:
            print('\n\t aint nothing to deliver! \n')
    
    def async(self, pid, _2pid, p2_):
        pp2_ = comm.GenChannel(('write-async',pid))
        _2pp = comm.GenChannel(('read-async',pid))

        def _translate():
            while True:
                r = gevent.wait(objects=[pp2_],count=1)
                r = r[0]
                msg = r.read()
                pp2_.reset()
                msg = ((self.sid,pid),msg)
                rnd = self.util_clock_read(pid)
                #print('\033[1m Adding msg={} to q={}\033[0m'.format(msg,q))
                if self.eventually_queue[pid] != (): raise Exception("theres a {} eventually that never got processed {}".format(pid, self.eventually_queue))
                self.leaks[pid].append( msg )
                self.eventually_queue.append( (msg,rnd,p2_) )


    def _newPID(self, sid, pid, _2pid, p2_, tag):
        pp2_ = comm.GenChannel(('write-translate',pid)) 
        _2pp = comm.GenChannel(('read',pid)) # _ to 

        def _translate():
            while True:
                r = gevent.wait(objects=[pp2_],count=1)
                r = r[0]
                msg = r.read()
                pp2_.reset('pp2_ translate reset')
                #print('\n\t Translating: {} --> {}'.format(msg, ((sid,pid),msg)))
                print('\t\t\033[93m {} --> {}, msg={}\033[0m'.format((self.sid,pid), msg[0], msg[1]))
                self.leaks[pid].append( msg )
                p2_.write( ((sid,pid), msg) )
        gevent.spawn(_translate)

        _2pid[pid] = _2pp
        return (_2pp, pp2_) 

    def util_read_clock(self,pid):
        self.p2f.write( ((self.sid,pid), ((420,'G_clock'),('clock-read',))) )
        r = gevent.wait(objects=[self.f2p],count=1)
        r = r[0]
        to,(fro,rnd) = r.read()
        self.f2p.reset()
        assert to == (self.sid,pid), "To={}, pid={}".format(to,pid)
        return rnd

    def newPID(self, pid, params=()):
        print('[{}] Creating new party with pid: {}'.format(self.sid, pid))
        _z2p,_p2z = self._newPID(self.sid, pid, self.z2pid, self.p2z, 'NA')
        _f2p,_p2f = self._newPID(self.sid, pid, self.f2pid, self.p2f, 'NA')
        _a2p,_p2a = self._newPID(self.sid, pid, self.a2pid, self.p2a, 'NA')
        _2p, p2_ = self._newPID(self.sid, pid, self.p2pid, self.p2_, 'NA')
        
        #itm = ITMPassthrough2(self.sid, pid, _a2p, _p2a, _z2p, _p2z, _f2p, _p2f) 
        p = self.prot(self.sid, pid, _p2f, _f2p, _p2a, _p2z, p2_, _2p, *params)
        itm = ITMProtocol(self.sid, pid, _a2p, _p2a, _z2p, _p2z, _f2p, _p2f, _2p, p2_)
        itm.init(p)
        setParty(itm)
        gevent.spawn(itm.run)

    def newPassthroughPID(self, pid, params=()):
        print('[{}] Creating simulated passthrough party with pid: {}'.format(self.sid,pid))
        _z2p,_p2z = self._newPID(self.sid, pid, self.z2pid, self.p2z, 'NA')
        _f2p,_p2f = self._newPID(self.sid, pid, self.f2pid, self.p2f, 'NA')
        _a2p,_p2a = self._newPID(self.sid, pid, self.a2pid, self.p2a, 'NA')
        
        itm = ITMPassthrough2(self.sid,pid, _a2p, _p2a, _z2p, _p2z, _f2p, _p2f)
        setParty(itm)
        gevent.spawn(itm.run)

    def getPID(self, _2pid, pid):
        if pid in _2pid: return _2pid[pid]
        else:
            self.newPID(pid)
            return _2pid[pid]

    def run(self):
        while True:
            #print('\t\033[94mStatus: z2p={}, f2p={}, a2p={}\033[0m'.format(self.z2p.is_set(),self.f2p.is_set(),self.a2p.is_set()))
            ready = gevent.wait(objects=[self.z2p, self.f2p, self.a2p, self.p2_], count=1)
            r = ready[0]
            if r == self.z2p:
                (pid, msg) = r.read() 
                #print('\033[92m[sid={}] Message for ({}): {}\033[0m'.format(self.sid, pid, msg))
                self.z2p.reset('z2p party reset')
                if not comm.ishonest(self.sid,pid):
                    raise Exception
                # pass onto the functionality
                _pid = self.getPID(self.z2pid,pid)
                _pid.write(msg)
            elif r == self.f2p:
                #(pid, msg) = r.read() 
                m = r.read()
                #print('\033[92m[{}] F2P Message for: {}\033[0m'.format(self.sid,m))
                (fro,(to,msg)) = m
                #print('fro', fro, 'to', to, 'msg', msg)
                _s,_p = to
                self.f2p.reset('f2p in party')
                #_pid = self.getPID(self.f2pid,pid)
                if comm.ishonest(_s,_p):
                    _pid = self.getPID(self.f2pid, _p)
                    _pid.write( (fro,msg) )
                else:
                    self.p2a.write( (fro,msg) )
            elif r == self.a2p:
                (pid, msg) = r.read() 
                print('\033[92m[{}] A2P Message for ({}): {}\033[0m'.format(self.sid, pid, msg))
                self.a2p.reset('a2p in party')
                if msg == 'get-leaks':
                    r = list(self.leaks[pid])
                    self.leaks[pid] = []
                    self.p2a.write( ((self.sid,pid), r) )
                else:
                    if comm.ishonest(self.sid,pid):
                        raise Exception
                    _pid = self.getPID(self.a2pid, pid)
                    _pid.write( msg )
            elif r == self.p2_:
                (fro, msg) = r.read() 
                self.p2_.reset()
                _to,_m = msg
                _s,_p = _to
                print('[{}] Message for ({}): {}'.format(self.sid, _p, _m))
                #print('\nfro={}, msg={}, _to={}, _m={}, _s={}, _p={}'.format(fro,msg,_to,_m,_s,_p))
                assert _s == self.sid
                
                if comm.ishonest(_s,_p):
                    _pid = self.getPID(self.p2pid, _p)
                    _pid.write( (fro, _m)  )
                else:
                    self.p2a.write( (fro,_m) )
            else:
                dump.dump()
        print('Its over??')

class ProtocolWrapper2:
    def __init__(self, sid, z2p, p2z, f2p, p2f, a2p, p2a, prot):
        self.sid = sid
        self.z2pid = {}
        self.f2pid = {}
        self.a2pid = {}
        self.p2pid = {}
        self.z2p = z2p; self.p2z = p2z;
        self.f2p = f2p; self.p2f = p2f;
        self.a2p = a2p; self.p2a = p2a
        self.p2_ = comm.GenChannel()
        self.prot = prot
        self.leaks = defaultdict(list)

        # eventually_queue[x] = (msg, round, p2_)
        self.eventually_queue = defaultdict(tuple)
    
    def deliver(self, pid, msg):
        try:
            m,rnd,c = self.eventually_queue[pid]
            if msg == m:
                c.write( m )
        except ValueError:
            print('\n\t aint nothing to deliver! \n')
    
    def async(self, pid, _2pid, p2_):
        pp2_ = comm.GenChannel(('write-async',pid))
        _2pp = comm.GenChannel(('read-async',pid))

        def _translate():
            while True:
                r = gevent.wait(objects=[pp2_],count=1)
                r = r[0]
                msg = r.read()
                pp2_.reset()
                msg = ((self.sid,pid),msg)
                rnd = self.util_clock_read(pid)
                #print('\033[1m Adding msg={} to q={}\033[0m'.format(msg,q))
                if self.eventually_queue[pid] != (): raise Exception("theres a {} eventually that never got processed {}".format(pid, self.eventually_queue))
                self.leaks[pid].append( msg )
                self.eventually_queue.append( (msg,rnd,p2_) )


    def _newPID(self, sid, pid, _2pid, p2_, tag):
        pp2_ = comm.GenChannel(('write-translate',pid)) 
        _2pp = comm.GenChannel(('read',pid)) # _ to 

        def _translate():
            while True:
                r = gevent.wait(objects=[pp2_],count=1)
                r = r[0]
                msg = r.read()
                pp2_.reset('pp2_ translate reset')
                #print('\n\t Translating: {} --> {}'.format(msg, ((sid,pid),msg)))
                #print('\t\t\033[93m {} --> {}, msg={}\033[0m'.format((self.sid,pid), msg[0], msg[1]))
                self.leaks[pid].append( msg )
                #print('\n\t\033[1m Bitch im out here getting them leaks for yo ass\033[0m')
                p2_.write( ((sid,pid), msg) )
        gevent.spawn(_translate)

        _2pid[pid] = _2pp
        return (_2pp, pp2_) 

    def util_read_clock(self,pid):
        self.p2f.write( ((self.sid,pid), ((420,'G_clock'),('clock-read',))) )
        r = gevent.wait(objects=[self.f2p],count=1)
        r = r[0]
        to,(fro,rnd) = r.read()
        self.f2p.reset()
        assert to == (self.sid,pid), "To={}, pid={}".format(to,pid)
        return rnd

    def newPID(self, pid):
        print('\033[1m[{}]\033[0m Creating new party with pid: {}'.format('PWrapper', pid))
        _z2p,_p2z = self._newPID(self.sid, pid, self.z2pid, self.p2z, 'NA')
        _f2p,_p2f = self._newPID(self.sid, pid, self.f2pid, self.p2f, 'NA')
        _a2p,_p2a = self._newPID(self.sid, pid, self.a2pid, self.p2a, 'NA')
        _2p, p2_ = self._newPID(self.sid, pid, self.p2pid, self.p2_, 'NA')
        
        #itm = ITMPassthrough2(self.sid, pid, _a2p, _p2a, _z2p, _p2z, _f2p, _p2f) 
        if comm.isdishonest(self.sid, pid):
            p = ITMPassthrough2(self.sid, pid, _a2p, _p2a, _z2p, _p2z, _f2p, _p2f)
        else:
            p = self.prot(self.sid, pid, _p2f,_f2p, _p2a,_a2p, _p2z,_z2p)
        setParty(p)
        gevent.spawn(p.run)

    def newPassthroughPID(self, pid, params=()):
        print('[{}] Creating simulated passthrough party with pid: {}'.format(self.sid,pid))
        _z2p,_p2z = self._newPID(self.sid, pid, self.z2pid, self.p2z, 'NA')
        _f2p,_p2f = self._newPID(self.sid, pid, self.f2pid, self.p2f, 'NA')
        _a2p,_p2a = self._newPID(self.sid, pid, self.a2pid, self.p2a, 'NA')
        
        itm = ITMPassthrough2(self.sid,pid, _a2p, _p2a, _z2p, _p2z, _f2p, _p2f)
        setParty(itm)
        gevent.spawn(itm.run)

    def getPID(self, _2pid, pid):
        if pid in _2pid: return _2pid[pid]
        else:
            self.newPID(pid)
            return _2pid[pid]

    def run(self):
        while True:
            #print('\t\033[94mStatus: z2p={}, f2p={}, a2p={}\033[0m'.format(self.z2p.is_set(),self.f2p.is_set(),self.a2p.is_set()))
            ready = gevent.wait(objects=[self.z2p, self.f2p, self.a2p, self.p2_], count=1)
            r = ready[0]
            if r == self.z2p:
                (pid, msg) = r.read() 
                #print('\033[92m[sid={}] Message for ({}): {}\033[0m'.format(self.sid, pid, msg))
                self.z2p.reset('z2p party reset')
                if not comm.ishonest(self.sid,pid):
                    raise Exception
                # pass onto the functionality
                _pid = self.getPID(self.z2pid,pid)
                _pid.write(msg)
            elif r == self.f2p:
                #(pid, msg) = r.read() 
                m = r.read()
                #print('\033[92m[{}] F2P Message for: {}\033[0m'.format(self.sid,m))
                (fro,(to,msg)) = m
                #print('fro', fro, 'to', to, 'msg', msg)
                #_s,_p = to
                try:
                    _s,_p = to
                    assert self.sid == _s
                except TypeError:
                    _p = to
                self.f2p.reset('f2p in party')
                #_pid = self.getPID(self.f2pid,pid)
                #if comm.ishonest(_s,_p):
                if comm.ishonest(self.sid,_p):
                    _pid = self.getPID(self.f2pid, _p)
                    _pid.write( (fro,msg) )
                else:
                    self.p2a.write( (fro,msg) )
            elif r == self.a2p:
                (pid, msg) = r.read() 
                print('\033[92m[{}] A2P Message for ({}): {}\033[0m'.format(self.sid, pid, msg))
                self.a2p.reset('a2p in party')
                if msg == 'get-leaks':
                    r = list(self.leaks[pid])
                    self.leaks[pid] = []
                    self.p2a.write( ((self.sid,pid), r) )
                else:
                    if comm.ishonest(self.sid,pid):
                        raise Exception
                    _pid = self.getPID(self.a2pid, pid)
                    _pid.write( msg )
            elif r == self.p2_:
                (fro, msg) = r.read() 
                self.p2_.reset()
                _to,_m = msg
                _s,_p = _to
                print('[{}] Message for ({}): {}'.format(self.sid, _p, _m))
                #print('\nfro={}, msg={}, _to={}, _m={}, _s={}, _p={}'.format(fro,msg,_to,_m,_s,_p))
                assert _s == self.sid
                
                if comm.ishonest(_s,_p):
                    _pid = self.getPID(self.p2pid, _p)
                    _pid.write( (fro, _m)  )
                else:
                    self.p2a.write( (fro,_m) )
            else:
                dump.dump()
        print('Its over??')


#from g_ledger import Ledger_Functionality2
#from protected_wrapper import Protected_Wrapper2
#from g_clock import Clock_Functionality2
#from f_state import StateChannel_Functionality2
#from f_broadcast import Broadcast_Functionality2
#from f_bd_sec import BD_SEC_Functionality

class FunctionalityWrapper:
    def __init__(self, p2f, f2p, a2f, f2a, z2f, f2z):
        self.z2fid = {}
        self.p2fid = {}
        self.a2fid = {}
        self.f2fid = {}
        self.p2f = p2f; self.f2p = f2p;
        self.a2f = a2f; self.f2a = f2a;
        self.z2f = z2f; self.f2z = f2z;
        self.f2_ = comm.GenChannel('f2_')
        self.tagtocls = {}


    def newcls(self, tag, cls):
        self.tagtocls[tag] = cls

    def _newFID(self, _2fid, f2_, sid, tag):
        ff2_ = comm.GenChannel(('write-translate',sid,tag))
        _2ff = comm.GenChannel(('read',sid,tag))

        def _translate():
            while True:
                r = gevent.wait(objects=[ff2_],count=1)
                r = r[0]
                msg = r.read()
                ff2_.reset()
                f2_.write( ((sid,tag), msg) )
        gevent.spawn(_translate) 

        _2fid[sid,tag] = _2ff
        return (_2ff, ff2_) 


    #def newFID(self, sid, tag, params=()):
    def newFID(self, sid, tag, cls, params=()):
        print('\033[1m[{}]\033[0m Creating new Functionality with pid: {}'.format('FWrapper', tag))
        _z2f,_f2z = self._newFID(self.z2fid, self.f2z, sid, tag)
        _p2f,_f2p = self._newFID(self.p2fid, self.f2p, sid, tag)
        _a2f,_f2a = self._newFID(self.a2fid, self.f2a, sid, tag)
        _2f,_f2_ = self._newFID(self.f2fid, self.f2_, sid, tag)
       
        if tag == 'G_ledger':
            print('\033[94mG_ledger channel _2f={}, _f2_={}\033[0m'.format(_2f.i, _f2_.i))
            g_ledger = Ledger_Functionality2(sid, -1, _f2p, _f2a, _f2z, _2f, _f2_)
            pwrapper = Protected_Wrapper2(g_ledger)
            ledger_itm = ITMFunctionality2(sid,-1, _a2f, _f2a, _z2f, _f2z, _p2f, _f2p, _2f, _f2_)
            ledger_itm.init(pwrapper)
            gevent.spawn(ledger_itm.run) 
            setFunctionality2(sid,tag)
        elif tag == 'G_clock':
            print('\033[94mG_clock channel _2f={}, _f2_={}\033[0m'.format(_2f.i, _f2_.i))
            c = Clock_Functionality2(sid, -1, _f2p, _f2a, _f2z, _2f, _f2_)
            c_itm = ITMFunctionality2(sid,-1, _a2f, _f2a, _z2f, _f2z, _p2f, _f2p, _2f, _f2_)
            c_itm.init(c)
            gevent.spawn(c_itm.run)
            setFunctionality2(sid,tag)
        elif tag == 'F_state':
            print('\033[94mF_state channel _2f={}, _f2_={}\033[0m'.format(_2f.i, _f2_.i))
            f = StateChannel_Functionality2(sid, tag, self.f2p, self.f2a, self.f2z, _2f, _f2_, *params)
            itm = ITMFunctionality2(sid, -1, _a2f, _f2a, _z2f, _f2z, _p2f, _f2p, _2f, _f2_)
            itm.init(f)
            gevent.spawn(itm.run)
            setFunctionality2(sid,tag)
        elif tag == 'F_bcast':
            f = Broadcast_Functionality2(sid, tag, _f2p, _f2a, _f2z, _2f, _f2_, *params)
            itm = ITMFunctionality2(sid, tag, _a2f, _f2a, _z2f, _f2z, _p2f, _f2p, _2f, _f2_)
            itm.init(f)
            setFunctionality2(sid,tag)
            gevent.spawn(itm.run)
        elif tag == 'F_bd':
            f = cls(sid, -1, _f2p,_p2f, _f2a,_a2f, _f2z,_z2f)
            #print('f2p', _f2p, 'p2f', _p2f)
            #print('f2a', _f2a, 'a2f', _a2f)
            #print('f2z', _f2z, 'z2f', _z2f)
            setFunctionality2(sid,tag)
            gevent.spawn(f.run)
        elif tag == 'F_clock':
            f = cls(sid, -1, _f2p,_p2f, _f2a,_a2f, _f2z,_z2f)
            setFunctionality2(sid,tag)
            gevent.spawn(f.run)

    def getFID(self, _2pid, sid,tag):
        #return _2pid[sid,tag]
        if (sid,tag) in _2pid: return _2pid[sid,tag]
        else:
            cls = self.tagtocls[tag]
            self.newFID(sid, tag, cls)
            return _2pid[sid,tag]

    def run(self):
        while True:
            ready = gevent.wait(objects=[self.z2f, self.p2f, self.a2f, self.f2_], count=1)
            r = ready[0]
            if r == self.z2f:  # should never happen
                dump.dump()
                self.z2f.reset()
            elif r == self.p2f:
                ((_sid,_pid), msg) = r.read() 
                self.p2f.reset()
                #print('P2F message', msg)
                ((__sid,_tag), msg) = msg
                _fid = self.getFID(self.p2fid, __sid, _tag)
                _fid.write( ((_sid,_pid), msg) )
            elif r == self.a2f:
                msg = r.read()
                self.a2f.reset()
                ((sid,tag), msg) = msg
                # TODO if not corrupt, crash
                _fid = self.getFID(self.a2fid, sid, tag)
                _fid.write( msg )
            elif r == self.f2_:
                ((_sid,_pid), msg) = r.read()
                self.f2_.reset()
                ((__sid,__pid), _msg) = msg
                _fid = self.getFID(self.f2fid, __sid,__pid)
                _fid.write( ((_sid,_pid), _msg) )
            else:
                print('SHEEEit')
                dump.dump()

class FunctionalityWrapperWrapper(object):
    def __init__(self, p2f, f2p, a2f, f2a, z2f, f2z):
        self.z2fid = {}
        self.p2fid = {}
        self.a2fid = {}
        self.f2fid = {}
        self.p2f = p2f; self.f2p = f2p;
        self.a2f = a2f; self.f2a = f2a;
        self.z2f = z2f; self.f2z = f2z;
        self.f2_ = comm.GenChannel('f2_')

        self.tagtocls = {}
        self.wrapper = FunctionalityWrapper(p2f, f2p, a2f, f2a, z2f, f2z)

    def newfunctionality(self, tag, cls):
        self.tagtocls[tag] = cls

    def newFID(self, sid, tag, cls):
        print('[{}] Creating new Functionality with pid: {}'.format(sid, tag))
          

    def getFID(self, _2fid, sid, tag):
        if (sid,tag) in _2fid: return _2fid[sid,tag]
        else:
            cls = self.tagtocls[tag]
            self.wrapper.newFID(sid, tag, cls)



class ITMAdversary2(object):
    #def __init__(self, sid, pid, z2a, z2p, a2f, a2g):
    def __init__(self, sid, pid, z2a, a2z, p2a, a2p, a2f, f2a):
        self.sid = sid
        self.pid = pid
        self.sender = (sid,pid)
        self.z2a = z2a; self.a2z = a2z
        self.p2a = p2a; self.a2p = a2p
        self.f2a = f2a; self.a2f = a2f

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
        self.a2f.write( ((69,'G_ledger'), (False, msg)) )
        r = gevent.wait(objects=[self.f2a],count=1)
        r = r[0]
        msg = r.read()
        print('response DELAY', msg, '\n')
        self.a2z.write(msg)
        self.f2a.reset()

    def input_ping(self, to):
        self.a2f.write( (to, ('ping',)) )

    def getLeaks(self, fro):
        if fro[1] == 'G_ledger':
            print('Write to a2f:', fro, (False, ('get-leaks',)))
            self.a2f.write( (fro, (False, ('get-leaks',))) )
        else:
            print('write to a2f:', fro, ('get-leaks',))
            self.a2f.write( (fro, ('get-leaks',)) )
        r = gevent.wait(objects=[self.f2a],count=1)
        r = r[0]
        msg = r.read()
        print('response F', msg)
        self.a2z.write( msg )
        self.f2a.reset()

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
            #    objects=[self.z2a, self.leak],
            #    count=1
            #)
            ready = gevent.wait(
                objects=[self.z2a, self.f2a, self.p2a],
                count=1
            )
            r = ready[0]
            #print('\n\t\t WE GOT SOMETHING', r.read())
            if r == self.z2a:
                msg = r.read()
                self.z2a.reset()
                t,msg = msg
                print('ADVERSARY MESSAGE ITM', t, msg)
                if t == 'A2F':
                    if msg[0] == 'get-leaks':
                        print('A2F message', msg)
                        self.getLeaks(msg[1])
                    elif msg[0] == 'delay-tx':
                        self.input_delay_tx(msg[1], msg[2], msg[3])
                    elif msg[0] == 'ping':
                        self.input_ping(msg[1])
                    else:
                        print('fucked up'); dump.dump()
                elif t == 'A2P':
                    self.a2p.write( msg )
                    #r = gevent.wait(objects=[self.p2a],count=1, timeout=0.1)
                    #if r:
                    #    r = r[0]
                    #    msg = r.read()
                    #    self.p2a.reset()
                    #    print('\033[1mP2A: \033[0m', msg)
                    #    self.a2z.write( msg )
            elif r == self.p2a:
                msg = r.read()
                self.p2a.reset()
                print('Go back from party', msg)
                self.a2z.write( msg )
            else:
                print('else dumping right after leak'); dump.dump()

class DummyAdversary(object):
    #def __init__(self, sid, pid, z2a, z2p, a2f, a2g):
    def __init__(self, sid, pid, z2a, a2z, p2a, a2p, a2f, f2a):
        self.sid = sid
        self.pid = pid
        self.sender = (sid,pid)
        self.z2a = z2a; self.a2z = a2z
        self.p2a = p2a; self.a2p = a2p
        self.f2a = f2a; self.a2f = a2f

        self.input = AsyncResult()
        self.leak = AsyncResult()
        self.parties = {}
        self.leakbuffer = []
    
    def __str__(self):
        return str(self.F)

    def read(self, fro, msg):
        print(u'{:>20} -----> {}, msg={}'.format(str(fro), str(self), msg))

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
        self.a2f.write( ((69,'G_ledger'), (False, msg)) )
        r = gevent.wait(objects=[self.f2a],count=1)
        r = r[0]
        msg = r.read()
        print('response DELAY', msg, '\n')
        self.a2z.write(msg)
        self.f2a.reset()

    def input_ping(self, to):
        self.a2f.write( (to, ('ping',)) )

    def getLeaks(self, fro):
        if fro[1] == 'G_ledger':
            print('Write to a2f:', fro, (False, ('get-leaks',)))
            self.a2f.write( (fro, (False,('get-leaks',))) )
        else:
            print('Write to a2f:', fro, ('get-leaks',))
            self.a2f.write( (fro, ('get-leaks',)) )
        r = gevent.wait(objects=[self.f2a],count=1)
        r = r[0]
        msg = r.read()
        print('response F', msg)
        self.a2z.write( msg )
        self.f2a.reset()

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
                objects=[self.z2a, self.f2a, self.p2a],
                count=1
            )
            r = ready[0]
            if r == self.z2a:
                msg = r.read()
                self.z2a.reset()
                t,msg = msg
                print('ADVERSARY MESSAGE ITM', t, msg)
                if t == 'A2F':
                    if msg[0] == 'get-leaks':
                        print('A2F message', msg)
                        self.getLeaks(msg[1])
                    elif msg[0] == 'delay-tx':
                        self.input_delay_tx(msg[1], msg[2], msg[3])
                    elif msg[0] == 'ping':
                        self.input_ping(msg[1])
                    else:
                        self.a2f.write( msg )
                elif t == 'A2P':
                    print('Write A2P', msg)
                    self.a2p.write( msg )
                    #r = gevent.wait(objects=[self.p2a],count=1, timeout=0.1)
                    #if r:
                    #    r = r[0]
                    #    msg = r.read()
                    #    self.p2a.reset()
                    #    print('\033[1mP2A: \033[0m', msg)
                    #    self.a2z.write( msg )
            elif r == self.p2a:
                msg = r.read()
                self.p2a.reset()
                print('Go back from party', msg)
                self.a2z.write( msg )
            elif r == self.f2a:
                msg = r.read()
                self.f2a.reset()
                self.a2z.write(msg)
            else:
                print('else dumping right after leak'); dump.dump()



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

