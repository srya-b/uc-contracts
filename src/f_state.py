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
    def __init__(self, sid, pid, G, C, U, f2g, *p):
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
        self.state = ''
        self.buf = ''
        self.lastblock = self.subroutine_block_number()
        print("LASTBLOCK:", self.lastblock)

        self.round = 0
        self.outputs = defaultdict(Queue)
        self.deadline = self.lastblock + self.DELTA
        self.inputs = [None for _ in range(len(p))]
        self.past_inputs = {}
        self.pmap = dict( (p,i) for i,p in enumerate(self._p))
        self.adversary_out = qqueue()
        self.buffer_output = defaultdict(list)

    def p(self,i):
        return self.pmap[i]
    
    def pinput(self,pid):
        return self.inputs[self.p(pid)]

    def isplayer(self, pid):
        return pid in self._p

    def __str__(self):
        return '\033[92mF_state\033[0m'
    
    def subroutine_block_number(self):
        #print('calling blockno')
        return self.G.subroutine_call((
            (self.sid, self.pid),
            True,
            ('block-number',)
        ))

    def buffer(self, msg, delta, p):
        self.buffer_output[ self.subroutine_block_number()+delta ].append((msg,p))

    def write(self, to, msg):
        #print(u'\033[92m{:>20}\033[0m -----> {}, msg={}'.format('F_state', str(to), msg))
        gwrite(u'92m', 'F_state', to, msg)

    def leak(self, msg):
        self.adversary_out.put(msg)


    def process_buffer(self):
        rnd = self.subroutine_block_number()
        for i in range(0,rnd+1):
            for m,p in self.buffer_output[i]:
                self.outputs[p].put(m)
            self.buffer_output[i] = []

    def subroutine_read(self, pid):
        o = []
        while True:
            try:
                m = self.outputs[pid].get_nowait()
                o.append(m)
            except:
                break
        return o


    def execute(self):
        #print('state:', self.state, 'inputs:', self.inputs, 'auxin:', self.aux_in)
        state,o = self.U(self.state, self.inputs, self.aux_in[-1] if self.aux_in else [], self.round)
        print("state':", state)
        #for p in range(len(self._p)):
        #    if isdishonest(self.sid,p):
        #        # deliver updated state in O(delta) rounds
        #        return

        self.state = state
       
        delta = 1
        for i in self._p:
            if isdishonest(self.sid,i):
                delta = self.DELTA; break
        
        for i in self._p:
            self.buffer(state, delta, i)

        #for i in self._p:
        #    self.outputs[i].put(state)
        #print('get output', self.outputs)

        self.past_inputs[self.round] = self.inputs
        self.inputs = [None for _ in range(len(self._p))]
        if o:
            # create on-chain transaction for aux contract
            print('some contract output')
            self.f2g.write( (True,('transfer', self.C, 0, ('output', (o,)), 'doesntmatter')) )
        else: dump.dump()

    def allinputs(self):
        for inp in self.inputs:
            if inp is None:
                return False
        return True

#    def tx_check(self):
#        blockno = self.subroutine_block_number()
#        txs = self.G.subroutine_call((
#            (self.sid, self.pid),
#            True,
#            (False, ('get-txs', self.C , blockno-1, self.lastblock))
#        ))
#        #print('LASTBLOCK={}, BLOCK={}, BLOCK-1={}'.format(self.lastblock, blockno, blockno-1))
#        if txs:
#            for tx in txs:
#                to,fro,val,data,nonce = tx
#                output = self.G.subroutine_call((
#                    self.sender,
#                    True,
#                    (False, ('read-output', [(fro,nonce)]))
#                ))
#                print('Output for (fro,nonce)={}, outputs={}'.format((fro,nonce), output))
#                if not output: continue
#                for o in output[0]:
#                    self.aux_in.append(o[1:])
#                #print('aux in after update', self.aux_in)
#
#        self.lastblock = blockno
#    
#        # check for ending round with input
#        #print('CHECKING INPUTS', self.inputs)
#        #print('blockno', blockno, 'deadline', self.deadline, 'lastblock', self.lastblock)
#        if blockno > self.deadline or self.allinputs():
#            if blockno > self.deadline: self.deadline = self.deadline + self.DELTA
#            elif self.allinputs(): self.deadline = self.lastblock + self.DELTA
#            #self.deadline = self.lastblock + self.DELTA
#            #self.deadline = self.deadline + self.DELTA
#            self.execute()
#            self.round = self.round + 1
#        else: dump.dump()

    
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
                #print('aux in after update', self.aux_in)
        self.lastblock = blockno
        #dump.dump()

    def state_check(self):
        blockno = self.subroutine_block_number()
        print('blockno', blockno, 'deadline', self.deadline, 'allinputs', self.allinputs()) 
        if self.allinputs() or blockno > self.deadline:
            self.deadline = blockno + self.DELTA
            self.execute()
            self.round = self.round + 1
        else:
            dump.dump()

    def ping(self):
        self.tx_check()
        self.state_check()

    def input_input(self, sid, pid, inp):
        msg = inp
        #if i != self.round: dump.dump(); return
        if self.pinput(pid): print('pinput dumping'); dump.dump(); return
              
        self.inputs[self.pmap[pid]] = msg
        self.leak(('input',pid,self.round,msg))
        #self.tx_check()
        print('state check')
        self.state_check()
        #print('\t f_state input input dump')
        #dump.dump()

    def input_msg(self, sender, msg):
        #print('FSTATE INPUTS MSG', sender, msg)
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
            #print('F_State got an INPUT', msg, sender)
            self.input_input(sid, pid, msg[1])
        else:
            dump.dump()

    def adversary_msg(self, msg):
        if msg[0] == 'ping': self.ping()
        else: dump.dump()

    def subroutine_msg(self, sender, msg):
        #print('FSTATE SUBROUTINE', msg)
        #self.tx_check()
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

class Sim_State:
    def __init__(self, sid, pid, G, F, crony):
        self.sid = sid; self.pid = pid
        self.sender = (sid,pid)
        self.G = G; self.F = F
        self.crony = crony
    
    def __str__(self):
        return '\033[91mSimulator (%s, %s)\033[0m' % (self.sid, self.pid) 

    def write(self, to, msg):
        #print('\033[91m{:>20}\033[0m -----> {}, msg={}'.format('Simulator (%s,%s)' % (self.sid, self.pid), str(to), msg))
        gwrite(u'91m', 'Simulator (%s,%s)'%(self.sid,self.pid), to, msg)

    def input_delay_tx(self, fro, nonce, rounds):
        msg=('delay-tx', fro, nonce, rounds)
        self.write(self.G, msg)
        self.G.backdoor.set((
            self.sender,
            True,
            (False, msg)
        ))

    def input_party(self, to, msg):
        self.write(self.crony, msg)
        self.crony.backdoor.set(msg)

    def input_msg(self, msg):
        if msg[0] == 'delay-tx':
            self.input_delay_tx(msg[1], msg[2], msg[3])
        elif msg[0] == 'party-input':
            self.input_party(msg[1], msg[2])
        else:
            dump.dump()

