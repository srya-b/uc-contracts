import os
import sys
from gevent.queue import Queue, Channel, Empty
from gevent.event import AsyncResult, Event
import dump
import gevent
import comm
from utils import gwrite, z_write

'''
There are 2 options with channels:
    1. The channels are greenlets themselves where they wait for
        the AsyncResult to be set and then write the result to the
        input of the 'to' itm. However, the channel itself needs
        to be the input to the itm, otherwise there's just an extra
        layer that ads another call to it.
    2. Calling 'write' on the channel writes to the input tape of the
        'to' itm. This allows the same interface for the party that's
        writing, but the recipient can be someone different. If the
        simulator want to run a sandbox of the adversary, then the 
        desired construction is that all channels connect to the 
        simulator and the simulator can control the output messages
        to the actual intended recipient.

Design Decision:
    * Instead 'to' and 'fro' will be just identifiers of the form
        (sid,pid). Having 'to' be the AsyncResult itself means the 
        code will still be at the mercy of having to spawn itms
        in a specific order based on the protocol at hand. Which
        really blows.
    * Can't be ^ (above) either. If 'to' is the identifier and the
        itm is got from 'comm' then you're screwed because you have 
        to fake an identifier and register is in 'comm' for the 
        simulator to be able to sandbox run the adversary and
        intercept outputs.
    * Actually, shit the channel has to be the AsyncResult itself
        that's the only way. That's the way it was the first time
        idk how I convinced myself to change it. rip
'''
class GenChannel(Event):
    def __init__(self, i=-1):
        Event.__init__(self)
        self._data = None
        self.i = i

    def write(self,data):
        if not self.is_set():
            #print('\033[93m \t\tWriting {} id={}\033[0m'.format(data,self.i))
            self._data = data; self.set()
        else: 
            raise Exception("\033[1mwriting to channel already full with {}. Writing {} in {}\033[0m".format(self._data,data,self.i))
            dump.dump()

    def read(self): 
        #print('\033[91m Reading message: {} id={}\033[0m'.format(self._data,self.i)); 
        return self._data
    def reset(self, s=''): 
        #print('\033[1m Resetting id={}, string={}\033[0m'.format(self.i,s)); 
        self.clear()


class ITMFunctionality(object):

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

class ITMSyncProtocol(object):
    def __init__(self, sid, pid, channels, handlers):
        self.channels = channels
        self.handlers = handlers
        self.sid = sid
        self.ssid = self.sid[0]
        self.parties = self.sid[2]
        self.pid = pid
        self.clock_round = 1
        self.roundok = False
        # n-1 length todo function to ensure that many future activations
        self.todo = [ (lambda: dump.dump(),()) for p in self.parties if p != self.pid]
        self.startsync = True
        # TODO change the name of this because it's not broadcast specific
        self.outputset = False

        print('[{}] Sending start synchronization...'.format(self.pid))
        self.p2f.write( ((self.sid,'F_clock'),('RoundOK')) )
        self.roundok = True

    def wait_for(self, chan):
        r = gevent.wait(objects=[chan],count=1)
        r = r[0]
        fro,msg = r.read()
        chan.reset()
        return fro,msg

    def p2p_handler(self, fro, msg):
        raise Exception("p2p_handler must be implemented by deriving class")

    def fetch(self, fbdsid):
        fro = fbdsid[1]
        self.p2f.write( ((fbdsid, 'F_bd'), ('fetch',)) )
        _fro,_msg = self.wait_for(self.f2p)
        _,msg = _msg
        if msg is None: return
        else: self.p2p_handler(fro, msg)

    def send_message(self, fbdsid, msg):
        _ssid,_fro,_to,_r = fbdsid
        self.p2f.write( ((fbdsid,'F_bd'), msg) )

    def send_in_o1(self, pid, msg):
        fbdsid = (self.ssid, self.pid, pid, self.clock_round)
        self.todo.append( (self.send_message, (fbdsid, ('send', msg))) )
   
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
        if self.outputset:
            if len(self.todo) > 0: self.todo.pop(0); dump.dump()
            else:
                self.p2z.write( self.val )
            return

        # If RoundOK has been sent, then wait until we have a new round
        if self.roundok:
            self.p2f.write( ((self.sid,'F_clock'),('RequestRound',)) )
            fro,di = self.wait_for(self.f2p)
            if di == 0:     # this means the round has ended
                self.clock_round += 1
                self.read_messages()    # reads messagesna dn queues the messages to be sent
                self.roundok = False
            else: 
                self.p2z.write( ('early',) )
                return #TODO change to check

        if len(self.todo) > 0:
            # pop off todo and do it
            f,args = self.todo.pop(0)
            if f: f(*args)
            else: dump.dump()
        elif len(self.todo) == 0 and not self.outputset:      
            self.p2f.write( ((self.sid,'F_clock'),('RoundOK',)) )
            self.roundok = True
        else: dump.dump()

    def start_sync(self):
        if self.roundok and self.startsync:
            self.p2f.write( ((self.sid, 'F_clock'),('RequestRound',)) )
            fro,di = self.wait_for(self.f2p)
            if di == 1: raise Exception('Start synchronization not done')
            self.roundok = False
            self.startsync = False

    def run(self):
        while True:
            ready = gevent.wait(
                objects=self.channels,
                count=1
            )
            assert len(ready) == 1
            r = ready[0]
            self.start_sync()
            msg = r.read()
            r.reset()
            self.handlers[r](msg)


class ITMSyncFunctionality(object):
    def __init__(self, sid, pid, channels, handlers):
        self.sid = sid; self.pid = pid
        self.ssid = self.sid[0]
        self.Rnd = self.sid[1]
        self.parties = self.sid[2]

        self.channels = channels
        self.handlers = handlers

        self.x = dict( (p,None) for p in self.parties )
        self.y = dict( (p,None) for p in self.parties )
        self.t = dict( (p,len(self.parties)) for p in self.parties )
        self.l = 1
        self.crupted = set()

    def function(self):
        raise Exception("ITMSyncFunctinality.function must be defined in the deriving class!")

    def outputs_set(self):
        for i in self.y.values():
            if i is None: return False
        return True

    def are_all_honest_0(self):
        for i in self.parties:
            if i not in self.crupted and self.t[i] != 0: return False
        return True

    def input_input(self, pid, v):
        # TODO can input be set more than once??
        self.x[pid] = v
        self.f2a.write( ('input', pid, v) )

    def input_output(self, pid):
        #if pid not in self.crupted and self.x[pid] is None:
        if comm.ishonest(self.sid, pid) and self.x[pid] is None:
            dump.dump(); return

        if self.t[pid] > 0:
            self.t[pid] = self.t[pid]-1
            if self.are_all_honest_0() and self.l < self.Rnd:
                self.l += 1
                for i in self.t: self.t[i] = len(self.parties)
            self.f2a.write( ('activated',pid) )
        elif self.t[pid] == 0 and self.l < self.Rnd:
            self.f2p.write( (pid, ('early',)) )
        else:
            if self.x[1] is not None and not self.outputs_set():
                self.y = self.function()
            self.f2p.write( (pid, self.y[pid]) )

    def run(self):
        while True:
            ready = gevent.wait(
                objects=self.channels,
                count=1
            )
            assert len(ready) == 1
            r = ready[0]
            msg = r.read()
            r.reset()
            self.handlers[r](msg)

class ITMProtocol(object):
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
                if comm.ishonest(self.sid,self.pid):
                    self.p2z.write( msg )
                else:
                    self.p2a.write( msg )
            else:
                print('else dumping somewhere ive never been'); dump.dump()

class ITMSyncCruptProtocol(object):
    def __init__(self, sid, pid, a2p, p2a, z2p, p2z, f2p, p2f):
        self.sid = sid
        self.pid = pid
        self.sender = (sid,pid)

        self.z2p = z2p; self.p2z = p2z
        self.f2p = f2p; self.p2f = p2f###
        self.a2p = a2p; self.p2a = p2a

        self.input = AsyncResult()
        self.subroutine = AsyncResult()
        self.backdoor = AsyncResult()
        self.outputidx = 0
        self.roundok = False

        print('[{}] Sending start synchronization...'.format(self.pid))
        self.p2f.write( ((self.sid,'F_clock'), ('RoundOK',)) )
        self.roundok = True
       
    def __str__(self):
        return '\033[1mITM(%s, %s)\033[0m' % (self.sid, self.pid)

    def write(self, to, msg):
        gwrite(u'1m', 'ITM(%s, %s)'%(self.sid,self.pid), to, msg)

    def init(self, functionality):
        self.F = functionality
        self.outputs = self.F.outputs

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

    def wait_for(self, chan):
        r = gevent.wait(objects=[chan],count=1)
        r = r[0]
        fro,msg = r.read()
        chan.reset()
        return fro,msg

    def adv_msg(self, msg):
        if msg[0] == 'send':
            self.adv_send(msg[1], msg[2])
        else:
            self.p2f.write(msg)

    def run(self):
        while True:
            ready = gevent.wait(
                #objects=[self.a2p, self.z2p],
                objects=[self.z2p, self.a2p, self.f2p],
                count=1
            )
            assert len(ready) == 1
            r = ready[0]

            if self.roundok:
                self.p2f.write( ((self.sid,'F_clock'), ('RequestRound',)) )
                fro,di = self.wait_for(self.f2p)
                if di == 1: raise Exception('Start synchronization not complete')
                self.roundok = False

            msg = r.read()
            if r == self.z2p:
                assert False
            elif r == self.a2p:
                self.a2p.reset()
                if comm.ishonest(self.sid, self.pid):
                    assert False
                self.adv_msg(msg)
            elif r == self.f2p:
                self.f2p.reset()
                if comm.ishonest(self.sid,self.pid):
                    self.p2z.write( msg )
                else:
                    self.p2a.write( msg )
            else:
                print('else dumping somewhere ive never been'); dump.dump()

from comm import setFunctionality2, setParty
class PartyWrapper:
    def __init__(self, sid, z2p, p2z, f2p, p2f, a2p, p2a, tof):
        self.sid = sid
        self.z2pid = {}
        self.f2pid = {}
        self.a2pid = {}
        self.z2p = z2p; self.p2z = p2z;
        self.f2p = f2p; self.p2f = p2f;
        self.a2p = a2p; self.p2a = p2a
        self.tof = tof  # TODO: for GUC this will be a problems, who to passthrough message to?

    def _newPID(self, pid, _2pid, p2_, tag):
        pp2_ = GenChannel(('write-translate',pid)) 
        _2pp = GenChannel(('read',pid)) # _ to 

        def _translate():
            while True:
                r = gevent.wait(objects=[pp2_],count=1)
                r = r[0]
                msg = r.read()
                pp2_.reset('pp2_ translate reset')
                p2_.write( ((self.sid,pid), msg) )
        gevent.spawn(_translate)

        _2pid[pid] = _2pp
        return (_2pp, pp2_) 


    def newPID(self, pid):
        print('[{}] Creating new party with pid: {}'.format(self.sid, pid))
        _z2p,_p2z = self._newPID(pid, self.z2pid, self.p2z, 'NA')
        _f2p,_p2f = self._newPID(pid, self.f2pid, self.p2f, 'NA')
        _a2p,_p2a = self._newPID(pid, self.a2pid, self.p2a, 'NA')
        
        itm = ITMPassthrough(self.sid, pid, _a2p, _p2a, _z2p, _p2z, _f2p, _p2f) 
        setParty(itm)
        gevent.spawn(itm.run)
        # TODO maybe remove later but for start synchronization
        dump.dump()

    def getPID(self, _2pid, pid):
        if pid in _2pid: return _2pid[pid]
        else:
            self.newPID(pid)
            return _2pid[pid]

    def spawn(self,pid):
        self.newPID(pid)

    def run(self):
        while True:
            ready = gevent.wait(objects=[self.z2p, self.f2p, self.a2p], count=1)
            r = ready[0]
            m = r.read() 
            if r == self.z2p:
                pid,msg = m
                self.z2p.reset('z2p party reset')
                if not comm.ishonest(self.sid,pid):
                    raise Exception
                _pid = self.getPID(self.z2pid,pid)
                _pid.write( (self.tof, msg) )
            elif r == self.f2p:
                self.f2p.reset('f2p in party')
                fro,(to,msg) = m
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
        self.p2_ = GenChannel()
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
        pp2_ = GenChannel(('write-async',pid))
        _2pp = GenChannel(('read-async',pid))

        def _translate():
            while True:
                r = gevent.wait(objects=[pp2_],count=1)
                r = r[0]
                msg = r.read()
                pp2_.reset()
                msg = ((self.sid,pid),msg)
                rnd = self.util_clock_read(pid)
                if self.eventually_queue[pid] != (): raise Exception("theres a {} eventually that never got processed {}".format(pid, self.eventually_queue))
                self.leaks[pid].append( msg )
                self.eventually_queue.append( (msg,rnd,p2_) )


    def _newPID(self, sid, pid, _2pid, p2_, tag):
        pp2_ = GenChannel(('write-translate',pid)) 
        _2pp = GenChannel(('read',pid)) # _ to 

        def _translate():
            while True:
                r = gevent.wait(objects=[pp2_],count=1)
                r = r[0]
                msg = r.read()
                pp2_.reset('pp2_ translate reset')
                #print('\n\t Translating: {} --> {}'.format(msg, ((sid,pid),msg)))
                #print('\t\t\033[93m {} --> {}, msg={}\033[0m'.format((self.sid,pid), msg[0], msg[1]))
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

    def newPID(self, pid):
        print('\033[1m[{}]\033[0m Creating new party with pid: {}'.format('PWrapper', pid))
        _z2p,_p2z = self._newPID(self.sid, pid, self.z2pid, self.p2z, 'NA')
        _f2p,_p2f = self._newPID(self.sid, pid, self.f2pid, self.p2f, 'NA')
        _a2p,_p2a = self._newPID(self.sid, pid, self.a2pid, self.p2a, 'NA')
        _2p, p2_ = self._newPID(self.sid, pid, self.p2pid, self.p2_, 'NA')
        
        if comm.isdishonest(self.sid, pid):
            print('\033[1m[{}]\033[0m Party is corrupt, so ITMSyncCruptProtocol')
            p = ITMSyncCruptProtocol(self.sid, pid, _a2p, _p2a, _z2p, _p2z, _f2p, _p2f)
        else:
            p = self.prot(self.sid, pid, _p2f,_f2p, _p2a,_a2p, _p2z,_z2p)
        setParty(p)
        gevent.spawn(p.run)

    def newPassthroughPID(self, pid, params=()):
        print('[{}] Creating simulated passthrough party with pid: {}'.format(self.sid,pid))
        _z2p,_p2z = self._newPID(self.sid, pid, self.z2pid, self.p2z, 'NA')
        _f2p,_p2f = self._newPID(self.sid, pid, self.f2pid, self.p2f, 'NA')
        _a2p,_p2a = self._newPID(self.sid, pid, self.a2pid, self.p2a, 'NA')
        
        itm = ITMPassthrough(self.sid,pid, _a2p, _p2a, _z2p, _p2z, _f2p, _p2f)
        setParty(itm)
        gevent.spawn(itm.run)

    def getPID(self, _2pid, pid):
        if pid in _2pid: return _2pid[pid]
        else:
            self.newPID(pid)
            return _2pid[pid]

    def spawn(self, pid):
        self.newPID(pid)

    def run(self):
        while True:
            ready = gevent.wait(objects=[self.z2p, self.f2p, self.a2p, self.p2_], count=1)
            r = ready[0]
            if r == self.z2p:
                (pid, msg) = r.read() 
                self.z2p.reset('z2p party reset')
                if not comm.ishonest(self.sid,pid):
                    raise Exception
                # pass onto the functionality
                _pid = self.getPID(self.z2pid,pid)
                _pid.write(msg)
            elif r == self.f2p:
                m = r.read()
                (fro,(to,msg)) = m
                try:
                    _s,_p = to
                    assert self.sid == _s
                except TypeError:
                    _p = to
                self.f2p.reset('f2p in party')
                _pid = self.getPID(self.f2pid, _p)
                _pid.write( (fro, msg) )
            elif r == self.a2p:
                (pid, msg) = r.read() 
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
                assert _s == self.sid
                
                if comm.ishonest(_s,_p):
                    _pid = self.getPID(self.p2pid, _p)
                    _pid.write( (fro, _m)  )
                else:
                    self.p2a.write( (fro,_m) )
            else:
                dump.dump()
        print('Its over??')


class FunctionalityWrapper:
    def __init__(self, p2f, f2p, a2f, f2a, z2f, f2z):
        self.z2fid = {}
        self.p2fid = {}
        self.a2fid = {}
        self.f2fid = {}
        self.p2f = p2f; self.f2p = f2p;
        self.a2f = a2f; self.f2a = f2a;
        self.z2f = z2f; self.f2z = f2z;
        self.f2_ = GenChannel('f2_')
        self.tagtocls = {}


    def newcls(self, tag, cls):
        print('New cls', tag, cls)
        self.tagtocls[tag] = cls

    def _newFID(self, _2fid, f2_, sid, tag):
        ff2_ = GenChannel(('write-translate',sid,tag))
        _2ff = GenChannel(('read',sid,tag))

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


    '''Received a message for a functionality that doesn't exist yet
    create a new functionality and add it to the wrapper'''
    def newFID(self, sid, tag, cls, params=()):
        #print('\033[1m[{}]\033[0m Creating new Functionality with pid: {}'.format('FWrapper', tag))
        _z2f,_f2z = self._newFID(self.z2fid, self.f2z, sid, tag)
        _p2f,_f2p = self._newFID(self.p2fid, self.f2p, sid, tag)
        _a2f,_f2a = self._newFID(self.a2fid, self.f2a, sid, tag)
        _2f,_f2_ = self._newFID(self.f2fid, self.f2_, sid, tag)
       
        f = cls(sid, -1, _f2p, _p2f, _f2a, _a2f, _f2z, _z2f)
        setFunctionality2(sid,tag)
        gevent.spawn(f.run)

    '''Get the relevant channel for the functionality with (sid,tag)
    for example, if call is getFID(self, self.a2fid, sid, tag) this
    means: get the a2f channel for the functionality.'''
    def getFID(self, _2pid, sid,tag):
        if (sid,tag) in _2pid: return _2pid[sid,tag]
        else:
            cls = self.tagtocls[tag]
            self.newFID(sid, tag, cls)
            return _2pid[sid,tag]

    '''Basic gevent loop that will run forever'''
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
                ((__sid,_tag), msg) = msg
                _fid = self.getFID(self.p2fid, __sid, _tag)
                _fid.write( ((_sid,_pid), msg) )
            elif r == self.a2f:
                msg = r.read()
                self.a2f.reset()
                ((sid,tag), msg) = msg
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


####
####
####  Deprecated data stuctures that are right now only used for 
####  f_state stuff that's out of date.
####

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
                #print('ADVERSARY MESSAGE ITM', t, msg)
                if t == 'A2F':
                    if msg[0] == 'get-leaks':
                        print('A2F message', msg)
                        self.getLeaks(msg[1])
                    elif msg[0] == 'delay-tx':
                        self.input_delay_tx(msg[1], msg[2], msg[3])
                    elif msg[0] == 'ping':
                        self.input_ping(msg[1])
                    else:
                        dump.dump()
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

class ProtocolWrapperOld:
    def __init__(self, sid, z2p, p2z, f2p, p2f, a2p, p2a, prot):
        self.sid = sid
        self.z2pid = {}
        self.f2pid = {}
        self.a2pid = {}
        self.p2pid = {}
        self.z2p = z2p; self.p2z = p2z;
        self.f2p = f2p; self.p2f = p2f;
        self.a2p = a2p; self.p2a = p2a
        self.p2_ = GenChannel()
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
        pp2_ = GenChannel(('write-async',pid))
        _2pp = GenChannel(('read-async',pid))

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
        pp2_ = GenChannel(('write-translate',pid)) 
        _2pp = GenChannel(('read',pid)) # _ to 

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
        
        #itm = ITMPassthrough(self.sid, pid, _a2p, _p2a, _z2p, _p2z, _f2p, _p2f) 
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
        
        itm = ITMPassthrough(self.sid,pid, _a2p, _p2a, _z2p, _p2z, _f2p, _p2f)
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
                #print('\033[92m[{}] A2P Message for ({}): {}\033[0m'.format(self.sid, pid, msg))
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

