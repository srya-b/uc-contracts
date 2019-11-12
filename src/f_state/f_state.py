import dump 
import gevent
from itm import ITMFunctionality
from comm import ishonest, isdishonest, isadversary, setFunctionality
from utils import gwrite, print
from queue import Queue as qqueue
from queue import Empty
from hashlib import sha256
from collections import defaultdict
from gevent.queue import Queue, Channel

class StateChannel_Functionality(object):
    def __init__(self, sid, pid, G, C, U, f2g,*p):
        self.sid = sid
        self.pid = pid
        self.f2g = f2g
        self.sender = (sid,pid)
        self.G = G
        self.C = C
        self.U = U

        self.DELTA = 8
        self._p = p
        self.ptr = 0
        self.aux_in = []
        self.state = None
        self.buf = ''
        self.lastblock = self.subroutine_block_number()
        print("LASTBLOCK:", self.lastblock)

        self.round = 0
        #self.outputs = defaultdict(Queue)
        self.outputs = defaultdict(list)
        self.deadline = self.lastblock + self.DELTA
        self.inputs = [None for _ in range(len(p))]
        self.past_inputs = {}
        self.pmap = dict( (p,i) for i,p in enumerate(self._p))
        self.adversary_out = qqueue()
        self.buffer_output = defaultdict(list)
        self.p2c = None; self.clock = None
        self.t_L = 0
        self.auxin_ptr = 0

    def p(self,i):
        return self.pmap[i]
    
    def pinput(self,pid):
        return self.inputs[self.p(pid)]

    def isplayer(self, pid):
        return pid in self._p

    def __str__(self):
        return '\033[92mF_state\033[0m'
   
    def set_clock(self, p2c, clock):
        self.p2c = p2c; self.clock = clock

    def subroutine_block_number(self):
        #print('calling blockno')
        return self.G.subroutine_call((
            (self.sid, self.pid),
            True,
            ('block-number',)
        ))

    def util_read_clock(self):
        return self.clock.subroutine_msg( self.sender, ('clock-read',))

    # when buffering, buffer according to clock rounds
    def buffer(self, msg, delta, p):
        print('writing to buffer f_state', '(block)',self.util_read_clock(), '(delta)',delta, '(msg)', msg, '(p)', p)
        self.buffer_output[ self.util_read_clock() + delta ].append((msg,p))

    def write(self, to, msg):
        gwrite(u'92m', 'F_state', to, msg)

    def leak(self, msg):
        self.adversary_out.put(msg)

    # instead of waiting for on-chain rounds, wait for clock rounds
    def process_buffer(self):
        rnd = self.util_read_clock()
        for i in range(0,rnd+1):
            for m,p in self.buffer_output[i]:
                print('write to outputs', 'rnd', i, 'm', m, 'p', p)
                self.outputs[p].append(m)
            self.buffer_output[i] = []

    def subroutine_read(self, pid):
        return self.outputs[pid]

    def execute(self):
        #print('state:', self.state, 'inputs:', self.inputs, 'auxin:', self.aux_in)
        state,o = self.U(self.state, self.inputs, self.aux_in[self.auxin_ptr:] if len(self.aux_in) > self.auxin_ptr else [], self.round)
        if len(self.aux_in) > self.auxin_ptr:
            self.auxin_ptr = len(self.aux_in)

        self.state = state
       
        delta = 1
        for i in self._p:
            if isdishonest(self.sid,i):
                delta = self.DELTA; break
        
        for i in self._p:
            self.buffer(state, delta, i)

        self.past_inputs[self.round] = self.inputs
        self.inputs = [None for _ in range(len(self._p))]
        if o:
            self.f2g.write( (True,('transfer', self.C, 0, ('output', (o,)), 'doesntmatter')) )
        else: dump.dump()

    def allinputs(self):
        for inp in self.inputs:
            if inp is None:
                return False
        return True

    # tx check remains unchanged with the clock because we are still
    # only checking the next on-chain round for new transactions
    def tx_check(self):
        blockno = self.subroutine_block_number()
        txs = self.G.subroutine_call((
            (self.sid, self.pid),
            True,
            (False, ('get-txs', self.C , blockno-1, self.lastblock))
        ))
        print('LASTBLOCK={}, BLOCK={}, BLOCK-1={}'.format(self.lastblock, blockno, blockno-1))
        if txs:
            for tx in txs:
                to,fro,val,data,nonce = tx
                output = self.G.subroutine_call((
                    self.sender,
                    True,
                    (False, ('read-output', [(fro,nonce)]))
                ))
                print('Output for (fro,nonce)={}, outputs={}'.format((fro,nonce), output))
                if not output: continue
                for o in output[0]:
                    self.aux_in.append(o[1:])
        self.lastblock = blockno

    # Clock update: state check needs to be updates because it should wait for 
    # DELTA off-chain rounds when expecting input from the parties, not on-chain rounds
    # similarly, t_L should update when a new clock round is detected
    # expectation is that at least one activation every round, so should increase
    # by only 1 every time, if not there's a problem, maybe insert an 'assert' for that?
    def state_check(self):
        rnd = self.util_read_clock()
        print('clock', rnd, 'deadline', self.deadline, 'allinputs', self.allinputs())
        if self.allinputs() or rnd > self.deadline:
            self.deadlines = rnd + self.DELTA
            self.execute()
            self.round = self.round + 1
        else:
            dump.dump()

    def ping(self):
        self.tx_check()
        self.process_buffer()
        self.state_check()

    def input_input(self, sid, pid, inp):
        msg = inp
        print('ALL INPUTS?', self.allinputs())
        if self.pinput(pid): print('pinput dumping'); dump.dump(); return
             
        self.inputs[self.pmap[pid]] = msg
        self.leak(('input',pid,self.round,msg))
        print('ALL INPUTS?', self.allinputs(), self.inputs)
        print('state check')
        self.state_check()

    def input_msg(self, sender, msg):
        sid,pid = None,None
        if sender:
            sid,pid = sender
        if sid != self.sid: 
            dump.dump()
            return
        if not self.isplayer(pid): 
            dump.dump()
            return
        self.tx_check()
        self.process_buffer()
        if msg[0] == 'input':
            self.input_input(sid, pid, msg[1])
        else:
            dump.dump()

    def adversary_msg(self, msg):
        if msg[0] == 'ping': self.ping()
        else: dump.dump()

    def subroutine_msg(self, sender, msg):
        self.process_buffer()
        if sender: sid,pid = sender
        else: sid,pid = None,None
        assert sid == self.sid 
        if msg[0] == 'get-output':
            return self.outputs[pid]
        elif msg[0] == 'read':
            return self.subroutine_read(pid)
        else:
            return self.G.subroutine_call( (self.sender, True, msg) )

def StateITM(sid, pid, G, C, U, a2f, f2f, f2g, p2f, *p):
    f = StateChannel_Functionality(sid,pid,G,C,U,f2g, *p)
    itm = ITMFunctionality(sid,pid,a2f,f2f,p2f)
    itm.init(f)
    setFunctionality(itm)
    return f,itm

class StateChannel_Functionality2(object):
    #def __init__(self, sid, pid, G, C, U, f2g,*p):
    # TODO morning: add parameters back to state channel and get back to get-txs
    def __init__(self, sid, pid, _f2p, _f2a, _f2z, _2f, f2_, C, U, *p):
        print('\n\t\tPs', p)
        self.sid = sid
        self.pid = pid
        #self.f2g = f2g
        self.sender = (sid,pid)
        self.f2p = _f2p
        self.f2a = _f2a
        self.f2z = _f2z
        self._2f = _2f
        self.f2_ = f2_
        #self.G = G
        self.C = C
        self.U = U

        self.DELTA = 8
        self._p = p
        self.ptr = 0
        self.aux_in = []
        self.state = None
        self.buf = ''
        #self.lastblock = self.subroutine_block_number()
        self.lastblock = 0
        print("LASTBLOCK:", self.lastblock)

        self.round = 0
        #self.outputs = defaultdict(Queue)
        self.outputs = defaultdict(list)
        self.deadline = self.lastblock + self.DELTA
        self.inputs = [None for _ in range(len(p))]
        self.past_inputs = {}
        self.pmap = dict( (p,i) for i,p in enumerate(self._p))
        self.adversary_out = qqueue()
        self.buffer_output = defaultdict(list)
        self.p2c = None; self.clock = None
        self.t_L = 0
        self.auxin_ptr = 0

    def p(self,i):
        return self.pmap[i]
    
    def pinput(self,pid):
        return self.inputs[self.p(pid)]

    def isplayer(self, pid):
        return pid in self._p

    def __str__(self):
        return '\033[92mF_state\033[0m'
   
    def set_clock(self, p2c, clock):
        self.p2c = p2c; self.clock = clock

    def subroutine_block_number(self):
        #print('calling blockno')
        #return self.G.subroutine_call((
        #    (self.sid, self.pid),
        #    True,
        #    ('block-number',)
        #))

        self.f2_.write( ((69,'G_ledger'), (True, ('block-number',))) )
        r = gevent.wait(objects=[self._2f],count=1)
        r = r[0]
        fro,blockno = r.read()
        self._2f.reset()
        return blockno 
        #return -1

    def util_read_clock(self):
        #return self.clock.subroutine_msg( self.sender, ('clock-read',))
        #print('\033[1m reading clock\033[0m')
        self.f2_.write( ((420,'G_clock'), ('clock-read',)) )
        r = gevent.wait(objects=[self._2f],count=1)
        r = r[0]
        fro,rnd = r.read()
        self._2f.reset()
        return rnd

    # when buffering, buffer according to clock rounds
    def buffer(self, msg, delta, p):
        rnd = self.util_read_clock()
        print('writing to buffer f_state', '(block)', rnd, '(delta)',delta, '(msg)', msg, '(p)', p)
        self.buffer_output[ rnd + delta ].append((msg,p))

    def write(self, to, msg):
        gwrite(u'92m', 'F_state', to, msg)

    def leak(self, msg):
        self.adversary_out.put(msg)

    # instead of waiting for on-chain rounds, wait for clock rounds
    def process_buffer(self):
        rnd = self.util_read_clock()
        for i in range(0,rnd+1):
            for m,p in self.buffer_output[i]:
                print('write to outputs', 'rnd', i, 'm', m, 'p', p)
                self.outputs[p].append(m)
            self.buffer_output[i] = []

    def subroutine_read(self, pid):
        return self.outputs[pid]

    def input_read(self, pid):
        self.f2p.write( ((self.sid,pid), self.outputs[pid]) )

    def execute(self):
        print('state:', self.state, 'inputs:', self.inputs, 'auxin:', self.aux_in)
        state,o = self.U(self.state, self.inputs, self.aux_in[self.auxin_ptr:] if len(self.aux_in) > self.auxin_ptr else [], self.round)
        if len(self.aux_in) > self.auxin_ptr:
            self.auxin_ptr = len(self.aux_in)

        self.state = state
        #print('\n\t EXECUTE 1\n')
        delta = 1
        for i in self._p:
            if isdishonest(self.sid,i):
                delta = self.DELTA; break
        
        #print('\n\t EXECUTE 2\n')
        for i in self._p:
            self.buffer(state, delta, i)

        #print('\n\t EXECUTE 3\n')
        self.past_inputs[self.round] = self.inputs
        self.inputs = [None for _ in range(len(self._p))]
        if o:
            self.f2g.write( (True,('transfer', self.C, 0, ('output', (o,)), 'doesntmatter')) )
        else: dump.dump()

    def allinputs(self):
        for inp in self.inputs:
            if inp is None:
                return False
        return True

    # tx check remains unchanged with the clock because we are still
    # only checking the next on-chain round for new transactions
    def tx_check(self):
        blockno = self.subroutine_block_number()
        print('\n\t block no', blockno)
        #txs = self.G.subroutine_call((
        #    (self.sid, self.pid),
        #    True,
        #    (False, ('get-txs', self.C , blockno-1, self.lastblock))
        #))
        self.f2_.write( ((69,'G_ledger'), (True, ('get-txs', self.C, blockno-1,self.lastblock))) )
        r = gevent.wait(objects=[self._2f],count=1)
        r = r[0]
        fro,txs = r.read()
        self._2f.reset()
        print('LASTBLOCK={}, BLOCK={}, BLOCK-1={}'.format(self.lastblock, blockno, blockno-1))
        if txs:
            #print('\n\t[F_state] txs:', txs)
            for tx in txs:
                #print('tx', tx)
                to,fro,val,data,nonce = tx
                #output = self.G.subroutine_call((
                #    self.sender,
                #    True,
                #    (False, ('read-output', [(fro,nonce)]))
                #))
                self.f2_.write( ((69,'G_ledger'), (False, ('read-output', [(fro,nonce)]))) )
                r = gevent.wait(objects=[self._2f],count=1)
                r = r[0]
                fro,output = r.read()
                self._2f.reset()
                print('Output for (fro,nonce)={}, outputs={}'.format((fro,nonce), output))
                if not output: continue
                for o in output[0]:
                    self.aux_in.append(o[1:])
        self.lastblock = blockno

    # Clock update: state check needs to be updates because it should wait for 
    # DELTA off-chain rounds when expecting input from the parties, not on-chain rounds
    # similarly, t_L should update when a new clock round is detected
    # expectation is that at least one activation every round, so should increase
    # by only 1 every time, if not there's a problem, maybe insert an 'assert' for that?
    def state_check(self):
        rnd = self.util_read_clock()
        print('\n\t\tclock', rnd, 'deadline', self.deadline, 'allinputs', self.allinputs(), '\n\t')
        if self.allinputs() or rnd > self.deadline:
            self.deadlines = rnd + self.DELTA
            self.execute()
            self.round = self.round + 1
        else:
            dump.dump()

    def ping(self):
        #print('\n\t PINGED'); dump.dump()
        self.tx_check()
        self.process_buffer(); dump.dump()
        #self.state_check()

    def input_input(self, sid, pid, inp):
        msg = inp
        print('ALL INPUTS?', self.allinputs())
        if self.pinput(pid): print('pinput dumping'); dump.dump(); return
             
        self.inputs[self.pmap[pid]] = msg
        self.leak(('input',pid,self.round,msg))
        print('ALL INPUTS?', self.allinputs(), self.inputs)
        #dump.dump()
        self.state_check()

    def input_msg(self, sender, msg):
        sid,pid = None,None
        if sender:
            sid,pid = sender
        # TODO fix this
        #if sid != self.sid: 
        #    dump.dump()
        #    return
        #if not self.isplayer(pid): 
        #    dump.dump()
        #    return
        self.tx_check()
        #TODO self.process_buffer()
        if msg[0] == 'input':
            self.input_input(sid, pid, msg[1])
        elif msg[0] == 'read':
            self.input_read(pid)
        else:
            dump.dump()

    def adversary_msg(self, msg):
        if msg[0] == 'ping': self.ping()
        else: dump.dump()

    def subroutine_msg(self, sender, msg):
        self.process_buffer()
        if sender: sid,pid = sender
        else: sid,pid = None,None
        assert sid == self.sid 
        if msg[0] == 'get-output':
            return self.outputs[pid]
        elif msg[0] == 'read':
            return self.subroutine_read(pid)
        else:
            return self.G.subroutine_call( (self.sender, True, msg) )

class Sim_State:
    def __init__(self, sid, pid, G, F, crony, c, a2p, a2g):
        self.sid = sid; self.pid = pid
        self.sender = (sid,pid)
        self.G = G; self.F = F
        self.crony = crony
        self.cronysid = crony.sid; self.cronypid = crony.pid
        self.a2p = a2p; self.a2g = a2g
    
    def __str__(self):
        return '\033[91mSimulator (%s, %s)\033[0m' % (self.sid, self.pid) 

    def write(self, to, msg):
        gwrite(u'91m', 'Simulator (%s,%s)'%(self.sid,self.pid), to, msg)

    def input_party(self, to, msg):
        self.write(self.crony, msg)
        self.a2p.write( msg)

    def input_tick(self, permutation):
        msg = (self.sender, True, (True, ('tick', perm)))
        self.write(self.G, msg)
        self.a2g.write( (True, ('tick', perm)) )

    def input_msg(self, msg):
        if msg[0] == 'party-input':
            self.input_party(msg[1], msg[2])
        elif msg[0] == 'tick':
            self.input_tick(msg[1])
        else:
            dump.dump()

class Sim_State2:
    def __init__(self, sid, pid, a2f, a2p, a2z):
        self.sid = sid; self.pid = pid
        self.sender = (sid,pid)
        self.a2f = a2f
        self.a2p = a2p
        self.a2z = a2z
    
    def __str__(self):
        return '\033[91mSimulator (%s, %s)\033[0m' % (self.sid, self.pid) 

    def write(self, to, msg):
        gwrite(u'91m', 'Simulator (%s,%s)'%(self.sid,self.pid), to, msg)

    def input_party(self, to, msg):
        self.write(self.crony, msg)
        self.a2p.write( msg)

    def input_tick(self, permutation):
        msg = (self.sender, True, (True, ('tick', perm)))
        self.write(self.G, msg)
        self.a2g.write( (True, ('tick', perm)) )

    def input_msg(self, msg):
        if msg[0] == 'party-input':
            self.input_party(msg[1], msg[2])
        elif msg[0] == 'tick':
            self.input_tick(msg[1])
        else:
            dump.dump()

