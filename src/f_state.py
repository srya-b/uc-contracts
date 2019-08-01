import dump 
import gevent
from itm import ITMFunctionality
from comm import ishonest, isdishonest, isadversary
from queue import Queue as qqueue
from hashlib import sha256
from collections import defaultdict
from gevent.queue import Queue, Channel

class StateChannel_Functionality(object):
    def __init__(self, sid, pid, G, C, U, *p):
        self.sid = sid
        self.pid = pid
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
        print("LASTBLOCL:", self.lastblock)

        self.round = 0
        self.outputs = defaultdict(Queue)
        self.deadline = self.lastblock + self.DELTA
        self.inputs = [None for _ in range(len(p))]
        self.past_inputs = {}
        self.pmap = dict( (p,i) for i,p in enumerate(self._p))
        self.adversary_out = qqueue()

    def p(self,i):
        return self.pmap[i]
    
    def pinput(self,pid):
        return self.inputs[self.p(pid)]

    def isplayer(self, pid):
        return pid in self._p

    def __str__(self):
        return '\033[92mF_state\033[0m'

    def write(self, to, msg):
        print(u'\033[92m{:>20}\033[0m -----> {}, msg={}'.format('F_state', str(to), msg))

    def subroutine_block_number(self):
        return self.G.subroutine_call((
            (self.sid, self.pid),
            True,
            ('block-number',)
        ))

    def leak(self, msg):
        self.adversary_out.put(msg)

    def execute(self):
        print('state:', self.state, 'inputs:', self.inputs, 'auxin:', self.aux_in)
        state,o = self.U(self.state, self.inputs, self.aux_in[-1] if self.aux_in else [], self.round)
        print("state':", state)
        for p in range(len(self._p)):
            if isdishonest(self.sid,p):
                # deliver updated state in O(delta) rounds
                return

        self.state = state
        
        for i in self._p:
            self.outputs[i].put(state)
        #print('get output', self.outputs)

        if o:
            # create on-chain transaction for aux contract
            print('some contract output')
        self.past_inputs[self.round] = self.inputs
        self.inputs = [None for _ in range(len(self._p))]
       
    def allinputs(self):
        for inp in self.inputs:
            if inp is None:
                return False
        return True

    def tx_check(self):
        blockno = self.subroutine_block_number()
        txs = self.G.subroutine_call((
            (self.sid, self.pid),
            True,
            (False, ('get-txs', self.C , blockno-1, self.lastblock))
        ))
        #print('LASTBLOCK={}, BLOCK={}, BLOCK-1={}'.format(self.lastblock, blockno, blockno-1))
        if txs:
            for tx in txs:
                to,fro,val,data,nonce = tx
                output = self.G.subroutine_call((
                    self.sender,
                    True,
                    (False, ('read-output', [(fro,nonce)]))
                ))
                print('Output for (fro,nonce)={}, outputs={}'.format((fro,nonce), output))
                for o in output[0]:
                    self.aux_in.append(o[1:])
                #print('aux in after update', self.aux_in)

        self.lastblock = blockno
    
        # check for ending round with input
        if blockno > self.deadline or self.allinputs():
            self.deadline = self.lastblock + self.DELTA
            self.execute()
            self.round = self.round + 1

    def input_input(self, sid, pid, inp):
        msg = inp
        #if i != self.round: dump.dump(); return
        if self.pinput(pid): dump.dump(); return
        
        self.inputs[self.pmap[pid]] = msg
        self.leak(('input',pid,self.round,msg))
        self.tx_check()
        dump.dump()

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
        if msg[0] == 'input':
            self.input_input(sid, pid, msg[1])
        else:
            dump.dump()

    def subroutine_msg(self, sender, msg):
        self.tx_check()
        if sender: sid,pid = sender
        else: sid,pid = None,None
        assert sid == self.sid 
        if msg[0] == 'get-output':
            return self.outputs[pid]
        else:
            return self.G.subroutine_call( (self.sender, True, msg) )

def StateITM(sid, pid, G, C, U, *p):
    f = StateChannel_Functionality(sid,pid,G,C,U,*p)
    itm = ITMFunctionality(sid,pid)
    itm.init(f)
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
        print('\033[91m{:>20}\033[0m -----> {}, msg={}'.format('Simulator (%s,%s)' % (self.sid, self.pid), str(to), msg))

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

