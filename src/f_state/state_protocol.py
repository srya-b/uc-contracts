import dump
import gevent
from itm import ITMFunctionality
from comm import ishonest, isdishonest, isadversary, isf, isparty
from queue import Queue as qqueue
from utils import print, gwrite, z_write 
from hashlib import sha256
from collections import defaultdict
from gevent.queue import Queue, Channel

class State_Protocol(object):
    #def __init__(self, sid, pid, G, F_bc, C, C_aux, U, p2g, p2bc, *peers):
    def __init__(self, sid, pid, _p2f, _f2p, _p2a, _p2z, p2_, _2p, C, C_aux, U, leaderpid, *peers):
        self.sid = sid
        self.pid = pid
        self.sender = (sid,pid)
        self.first = True
        self.sendinput = False
        
        self.p2f = _p2f
        self.p2a = _p2a
        self.p2z = _p2z
        self.f2p = _f2p
        self.p2_ = p2_
        self._2p = _2p

        #self.G = G
        #self.F_bc = F_bc
        self.C = C          # C here is not the aux contract but contract_state
        self.C_aux = C_aux
        self.U = U
        #self.p2g = p2g
        #self.p2bc = p2bc
        self.outputs = defaultdict(Queue)
        self.peers = peers
        self.leader = False
        self.pleader = None
        self.leaderpid = leaderpid
        if leaderpid == self.pid: self.leader = True
        self.pinputs = defaultdict(dict)
        self.psigns = defaultdict(dict)
        self.currentroundinput = None
        
        # flag \in {0=OK,1=PENDING}
        self.flag = 0
        self.round = 0
        self.lastround = -1
        self.lastblock = 0
        # TODO: get the current clock time for this sid
        self.clockround = 0
        self.lastcommit = None
        self.allcommits = {}
        self.inputsent = False
        self.expectbatch = False
        self.expectcommit = False
        self.expectsign = False
        # TODO: running U once here to get initial state
        self.state, self.outr = self.U(None, [], None, 0)
        self.alloutr = {}
        self.allstates = {}
        self.aux_in = []
        #z_write( self.sender, self.state )

        # TODO make this work
        # the main idea here is that the protocol tracks what actions are remaining to take
        # this is easy to check in the next round to check if the environment gave enough
        # activations
        # the simplest form is the function and the arguments to pass to it
        # (f, (args,))
        self.actions_remaining = []
        
        ''' The idea here is that state protocol won't send clock-update
            until it has been activated at least twice, enough to check
            for multicasts and to check for transactions to respond to
        '''
        self.activation_state = 0  # 0=wait for check tx, 1=wait for check bc, 2=ready
        self.lastactivationround = 0  # TODO get current clock time

        self.p2c = None; self.clock = None

        # step1=input, step2=batch
        self.step = 1

    #def set_leader(self, leaderpid, pleader, p2l):
    #    if leaderpid==self.pid: self.leader = True
    #    self.pleader = pleader; self.p2l = p2l
    #def set_leader(self, leaderpid):
    #    if leaderpid == self.pid: self.leader = True
    #    self.leaderpid = leaderpid

    def printleaders(self):
        print('%s reporting leader: %s' % (self.pid, self.pleader))
        print('Am I the leader %s: %s' % (self.pid, self.leader))

    def __str__(self):
        return '\033[92mProt_state(%s,%s)\033[0m' % (self.sid, self.pid)

    def write(self, to, msg):
        gwrite(u'92m', 'Prot_state(%s,%s)' % (self.sid,self.pid), to, msg)

    def util_read_clock(self):
        self.p2f.write( ((420,'G_clock'), ('clock-read,')) )
        r = gevent.wait(objects=[self.f2p],count=1)
        r = r[0]
        fro,rnd = r.read()
        self.f2p.reset()
        return rnd
    
    def set_clock(self, c2c, clock):
        self.p2c = c2c; self.clock = clock

    def clock_read(self):
        return self.clock.subroutine_call( self.sender, ('clock-read',))
    
    def subroutine_block_number(self):
        self.p2f.write( ((69,'G_ledger'), ('block-number',)) )
        r = gevent.wait(objects=[self.f2p],count=1)
        r = r[0]
        fro,blockno = r.read()
        self.f2p.reset()
        print('blockno', blockno)
        return blockno

    def input_input(self, v_i, r):
        if r == self.round and not self.inputsent and self.flag == 0:
            print('SUBIMTTING FOR ROUND', self.round, r, v_i)
            # send v_i,r --> leader
            self.write( self.pleader, (v_i,r) )
            self.inputsent = True; self.expectbatch = True
            #self.p2l.write( ('input',v_i,r) )
            self.p2_.write( ((self.sid, self.leaderpid), ('input', v_i,r)) )
        else: 
            print('Input from wrong round, round={}  v_i={}, r_i={}'.format(self.round, v_i, r))
            dump.dump()
 
    def send_batch(self):
        print('\n\t\t self.aux_in={}'.format(self.aux_in))
        msg = ('BATCH', self.round, self.aux_in if self.aux_in else [], list(self.pinputs[self.round].values()))
        self.expectsign = True
        self.p2f.write( (('hello', 'F_bcast'), ('bcast', msg)) )

    def input_pinput(self, p_i, v_i, r):
        print('[LEADER] received input from', p_i, v_i, r)
        if r != self.round: dump.dump(); print('Not the right round', r, self.round); return
        if p_i not in self.pinputs[r]:
            self.pinputs[r][p_i] = v_i
        for p in self.peers:
            if p not in self.pinputs[self.round]:
                print('\033[1m\n\ndumped because not complete\033[0m', self.pinputs[self.round], self.peers)
                dump.dump(); return
        print('send batch')
        self.send_batch()

    def send_commit(self):
        msg = ('COMMIT', self.round, list(self.pinputs[self.round].values()))
        self.expectsign = False
        #self.p2bc.write( ('bcast', msg) )
        self.p2f.write( (('hello','F_bcast'),('bcast', msg)) )

    def input_psign(self, p_i, r_i, sig):
        if not self.expectsign: print('Message out of order'); dump.dump(); return
        print('[LEADER] received SIGN from', p_i, sig)
        if r_i != self.round: dump.dump(); return
        if p_i not in self.psigns[r_i]:
            self.psigns[r_i][p_i] = sig
        # TODO check signature rather than that the states are all correct
        for p in self.peers:
            if p not in self.psigns[r_i]:
                print('\t\tcurr psigns', self.psigns[self.round], 'P', p, 'r_i', r_i, 'round', self.round)
                dump.dump(); return
            else:
                assert self.psigns[r_i][p] == sig
        self.send_commit()

    # Check for messages from leader
    def query_leader(self):
        pass

    def subroutine_read(self):
        # TODO: not quite right
        if not self.lastcommit:
            z_write( self.sender, self.state )
        else:
            z_write( (self.sid, self.pid), self.lastcommit[0])
       
    def execute(self, inputs, aux_in):
        for aux in aux_in:
            assert aux in self.aux_in, 'Not here \t\tAUX_IN={} \n\t\tself={}'.format(aux_in, self.aux_in)
        _s, _o = self.U(self.state, inputs, aux_in, self.round)
        print('New state computed at={}, state={}'.format(self.sender, _s))
        # TODO don't confirm state until commit is received
        self.state = _s
        self.outr = _o
       
        # TODO send actual signature
        self.expectcommit = True
        # self.p2l.write( ('SIGN', self.round, _s) )
        self.p2_.write( ((self.sid,self.leaderpid), ('SIGN', self.round, _s)) )
        # TODO set a timeout for waiting for COMMIT message

    def input_batch(self, rnd, aux_in, inputs):
        if self.flag == 0 and self.expectbatch:
            print('\n\033[1m got a batch \033[0m', rnd, aux_in, inputs)
            self.expectbatch = False
            self.expectcommit = True
            # TODO do some more checks of the clock
            if self.round == rnd:
                self.execute(inputs, aux_in)
            else: dump.dump()
        else: dump.dump()
            
    def input_commit(self, rnd, sigs):
        # TODO check commit messages
            self.expectcommit = False
            self.inputsent = False
            assert rnd == self.round
            self.lastcommit = (self.state, self.outr, _sigs)
            self.allcommits[self.round] = self.lastcommit
            self.round = sef.lastround + 1
            self.aux_in = []
            # TODO probably output the new state to the envronment??
            print('Update\n\t\tself.lastcommit={}\n\t\tself.lastround={}\n\t\tself.round={}\n'.format(self.lastcommit, self.lastround, self.round))
            dump.dump()


    def check_bc(self):
        if self.flag == 1: return
        # get all msgs in multicast, filter by leader
        msgs = self.F_bc.subroutine_call((
            (self.sid,self.pid),True,
            ('read',)
        ))
        # check that this cround = last_cround + 1, fail otherwise
        # more than 1 multicast message means failure ==> only leader sends at most one every round
        assert len(msgs) <= 1, "Too many messages in broadcast={}, msgs={}\nEnvironment skipped a round!".format(len(msgs), msgs)
        cur_round = self.util_read_clock()
        assert cur_round == self.clockround or cur_round == self.clockround+1, "Skipped more than one round. Current round={}, clock round={}".format(cur_round, self.clockround)
        if len(msgs)==0:
            self.clockround = cur_round
            dump.dump()
            return
        msg,p = msgs[0]
        print('Message from fBcast msg={} from={}'.format(msg,p))
        print('self.expectbatch={}, self.expectcommit={}'.format(self.expectbatch,self.expectcommit))
        if self.flag == 0:
            # if expect batch
            if self.expectbatch and msg[0] == 'BATCH':
                self.expectbatch = False
                self.expectcommit = True
                _round,_auxin,_inputs = msg[1:]
                if self.round == _round:
                    self.execute(_inputs, _auxin)
                else: dump.dump()
            # if expect commit
            elif self.expectcommit and msg[0] == 'COMMIT':
                self.expectcommit = False
                self.inputsent = False
                _round,_sigs = msg[1:]
                assert _round == self.round
                # TODO check commit message
                self.lastcommit = (self.state, self.outr, _sigs)
                self.allcommits[self.round] = self.lastcommit
                self.lastround = _round
                self.round = self.lastround+1
                self.aux_in = []
                print('Update\n\t\tself.lastcommit={}\n\t\tself.lastround={}\n\t\tself.round={}\n'.format(self.lastcommit, self.lastround, self.round))
                dump.dump()
            else:
                dump.dump()
        else: dump.dump()
        self.clockround = cur_round

    def _evidence(self, _r):
        _state,_outr,_sigs = self.allcommits[_r]
        tx = ('transfer', self.C, 0, ('evidence', (_r, _state, _outr, _sigs)), 'NA')
        self.write('G_Ledger', tx)
        self.p2g.write( tx )

    def call_evidence(self, _r):
        if _r <= self.lastround:
            self._evidence(_r)
        else:
            dump.dump()
    
    def handle_dispute(self, r, deadline):
        if r <= self.lastround:
            print('\t\t[ProtState{}] Dispute r={} <= lastRound={}'.format(self.sender,r,self.lastround))
#            self.p2g.write( ('transfer', self.C, 0, ('evidence',(self.lastround, *self.lastcommit)), 'NA') )
            self._evidence( self.lastround )
        elif r == self.lastround+1:
            print('\t\t[ProtState{}] Dispute r={} = lastRound+1={}'.format(self.sender,r,self.lastround+1))
            tx = ('transfer', self.C, 0, ('input',r,self.currentroundinput), 'NA')
            self.write('G_Ledger', tx)
            self.flag = 1   # PENDING
            self.p2g.write( tx  )
        else:
            raise Exception('r={}, self.lastround={}'.format(r, self.lastround))

    def tx_check(self):
        # first check the state channel contract for disputes or other
        blockno = self.subroutine_block_number()
        self.p2f.write( ((69,'G_ledger'), ('get-txs', self.C, blockno-1,self.lastblock)) )
        r = gevent.wait(objects=[self.f2p],count=1)
        r = r[0]
        fro,txs = r.read()
        self.f2p.reset()
        # if flag=OK only expect DISPUTE no other transaction
        #if txs:  # fag = OK
        #    for tx in txs:
        #        to,fro,val,data,nonce = tx
        #        output = self.G.subroutine_call((
        #            self.sender, True,
        #            ('read-output', [(fro,nonce)])
        #        ))
        #        if not output: continue
        #        for e in output[0]:
        #            if e[0] == 'EventDispute' and self.flag == 0:
        #                r,deadline = e[1:]
        #                # should set all flags to false and flag=PENDING
        #                self.handle_dispute(r,deadline)
        #                break
        ## check for transactions in CONTRACT_AUX
        #txs = self.G.subroutine_call((
        #    (self.sid, self.pid), True,
        #    ('get-txs', self.C_aux, blockno-1, self.lastblock)
        #))
        self.p2f.write( ((69,'G_ledger'), ('get-txs', self.C_aux, blockno-1, self.lastblock)) )
        r = gevent.wait(objects=[self.f2p],count=1)
        r = r[0]
        fro,txs = r.read()
        self.f2p.reset()
        #
        #if txs:
        #    for tx in txs:
        #        to,fro,val,data,nonce = tx
        #        output = self.G.subroutine_call((
        #            self.sender, True,
        #            ('read-output', [(fro,nonce)])
        #        ))
        #        if not output: continue
        #        for o in output[0]:
        #            self.aux_in.append(o[1:])
        #    print('\n\t\t aux_in={}'.format(self.aux_in))
        #self.lastblock = blockno
        #                

        # if flag=PENDING only expect some resolution off-chain or on-chain

        # if flag=OK check for contract aux_in

    def input_ping(self):
        self.tx_check()
        #self.check_bc()
        print('Pinged')
        dump.dump()

    def input_msg(self, sender, msg):   
        print('INPUT MSG', sender, msg)
        sid,pid = sender
        
        if isf(sid,pid):
            if msg[0] == 'BATCH':
                _,rnd,aux_in,inputs = msg
                self.input_batch(rnd, aux_in, inputs)
            elif msg[0] == 'COMMIT':
                _,rnd,signs = msg
                self.inout_commit(rnd,sigs)
            else:
                dump.dump()
        else:
            if self.sid == sid:         # sent by another party
                if msg[0] == 'input':
                    self.input_pinput(pid, msg[1], msg[2])
                elif msg[0] == 'SIGN':
                    self.input_psign(pid, msg[1], msg[2])
                else: dump.dump()
            else:                       # sent by environment
                if msg[0] == 'input':
                    self.input_input(msg[1], msg[2])
                elif msg[0] == 'ping':
                    self.input_ping()
                elif msg[0] == 'call-evidence':
                    self.call_evidence(msg[1])
                else: dump.dump()

    def subroutine_msg(self, sender, msg):
        if msg[0] == 'read':    
            return self.subroutine_read()

class State_Contract(object):
    def __init__(self, address, call, out):
        self.address = address
        self.call = call; self.out = out
        self.bestRound = -1
        self.state = None
        self.flag = 0 #OK = 0 DISPUTE=1 PENDING=2
        self.deadline = None
        self.applied = []
        self.ps = []
        self.DELTA = -1
        self.U = None
        self.pinputs = defaultdict(dict)
        self.C = ''

    def init(self, U, C, d, ps, tx):
        self.ps = ps
        self.DELTA = d
        self.U = U; self.C = C

    def evidence(self, r, s_, out, sigs, tx):
        if r < self.bestRound: return
        # TODO check all sigs
        if self.flag == 1: # DISPUTE
            self.flag = 0  # OK
            self.out( ('EventOffchain', self.bestRound+1), tx['sender'])
        self.bestRound = r
        self.state = s_
        # TODO invoke C.aux_out(out)
        self.applied.append(r)

    def dispute(self, r, tx):
        print('\t\tDISPUTE r={}, self.bestRound+1={}, self.flag={}\n'.format(r, self.bestRound+1, self.flag))
        if r != self.bestRound + 1: return
        if self.flag != 0: return   # OK
        
        self.flag = 1  # DISPUTE
        self.deadline = tx['blocknumber'] + self.DELTA
        self.out( ('EventDispute', r, self.deadline), tx['sender'])

    def input(self, r, i, tx):
        if tx['sender'] in self.pinputs[r]: return 
        self.pinputs[r][tx['sender']] = i

    def resolve(self, r, tx):
        if p not in self.pinputs[r]: self.pinputs[r][p] = None # Default value

        self.state = self.U(self.state, self.pinputs[r].values(), None)
        self.flag = 0   # OK
        self.out( ('EventOnchain', r, self.state), tx['sender'])
        self.bestRound += 1


class Adv:
    #def __init__(self, sid, pid, G, F, crony, c_payment, a2g):
    def __init__(self, sid, pid, a2f, a2p, a2z):
        self.sid = sid
        self.pid = pid
        self.sender = (sid,pid)
        self.a2f = a2f
        self.a2p = a2p
        self.a2z = a2z

    def __str__(self):
        return '\033[91mAdversary (%s, %s)\033[0m' % (self.sid, self.pid) 

    def write(self, to, msg):
        gwrite(u'91m', 'Adversary (%s,%s)' %(self.sid,self.pid), to, msg)

    def input_tick(self, permutation):
        msg = (self.sender, True, (True, ('tick', perm)))
        self.write(self.G, msg)
        self.G.backdoor.set((
            self.sender,
            True,
            (True, ('tick', perm))
        ))
    
    '''
        Get contract code at addr
    '''
    def subroutine_get_contract(self, addr):
        f_addr = self.G.subroutine_call((
            (self.sid,self.pid),
            True,
            ('get-addr', addr)
        ))

        assert f_addr is not None

        if f_addr == addr:
            print('LULZ')
            return 'lulz'


    def input_msg(self, msg):
        if msg[0] == 'delay-tx':
            self.input_delay_tx(msg[1], msg[2], msg[3])
        elif msg[0] == 'tick':
            self.input_tick(msg[1])
        else:
            #print('** adv input_msg dump **')
            dump.dump()

    def subroutine_msg(self, msg):
        if msg[0] == 'get-contract':
            return self.subroutine_get_contract(msg[1])

#class State_Protocol(object):
#    def __init__(self, sid, pid, G, F_bc, C, C_aux, U, p2g, p2bc, *peers):
#        self.sid = sid
#        self.pid = pid
#        self.sender = (sid,pid)
#        self.first = True
#        self.sendinput = False
#
#        self.G = G
#        self.F_bc = F_bc
#        self.C = C          # C here is not the aux contract but contract_state
#        self.C_aux = C_aux
#        self.U = U
#        self.p2g = p2g
#        self.p2bc = p2bc
#        self.outputs = defaultdict(Queue)
#        self.peers = peers
#        self.leader = False
#        self.pleader = None
#        self.p2l = None
#        self.pinputs = defaultdict(dict)
#        self.psigns = defaultdict(dict)
#        self.currentroundinput = None
#        
#        # flag \in {0=OK,1=PENDING}
#        self.flag = 0
#        self.round = 0
#        self.lastround = -1
#        self.lastblock = self.subroutine_block_number()
#        # TODO: get the current clock time for this sid
#        self.clockround = 0
#        self.lastcommit = None
#        self.allcommits = {}
#        self.inputsent = False
#        self.expectbatch = False
#        self.expectcommit = False
#        self.expectsign = False
#        # TODO: running U once here to get initial state
#        self.state, self.outr = self.U(None, [], None, 0)
#        self.alloutr = {}
#        self.allstates = {}
#        self.aux_in = []
#        #z_write( self.sender, self.state )
#
#        # TODO make this work
#        # the main idea here is that the protocol tracks what actions are remaining to take
#        # this is easy to check in the next round to check if the environment gave enough
#        # activations
#        # the simplest form is the function and the arguments to pass to it
#        # (f, (args,))
#        self.actions_remaining = []
#        
#        ''' The idea here is that state protocol won't send clock-update
#            until it has been activated at least twice, enough to check
#            for multicasts and to check for transactions to respond to
#        '''
#        self.activation_state = 0  # 0=wait for check tx, 1=wait for check bc, 2=ready
#        self.lastactivationround = 0  # TODO get current clock time
#
#        self.p2c = None; self.clock = None
#
#        # step1=input, step2=batch
#        self.step = 1
#
#    def set_leader(self, leaderpid, pleader, p2l):
#        if leaderpid==self.pid: self.leader = True
#        self.pleader = pleader; self.p2l = p2l
#
#    def printleaders(self):
#        print('%s reporting leader: %s' % (self.pid, self.pleader))
#        print('Am I the leader %s: %s' % (self.pid, self.leader))
#
#    def __str__(self):
#        return '\033[92mProt_state(%s,%s)\033[0m' % (self.sid, self.pid)
#
#    def write(self, to, msg):
#        gwrite(u'92m', 'Prot_state(%s,%s)' % (self.sid,self.pid), to, msg)
#
#    def round_number(self):
#        return self.G.subroutine_call((
#            (self.sid,self.pid), True,
#            (True, ('block-number',))
#        ))
#
#    def util_read_clock(self):
#        return self.clock.subroutine_msg( self.sender, ('clock-read',))
#    
#    def set_clock(self, c2c, clock):
#        self.p2c = c2c; self.clock = clock
#
#    def clock_read(self):
#        return self.clock.subroutine_call( self.sender, ('clock-read',))
#    
#    def subroutine_block_number(self):
#        #print('calling blockno')
#        return self.G.subroutine_call((
#            (self.sid, self.pid),
#            True,
#            ('block-number',)
#        ))
#
#
#    def input_input(self, v_i, r):
#        if r == self.round and not self.inputsent and self.flag == 0:
#            print('SUBIMTTING FOR ROUND', self.round, r, v_i)
#            # send v_i,r --> leader
#            self.write( self.pleader, (v_i,r) )
#            self.inputsent = True; self.expectbatch = True
#            self.p2l.write( ('input',v_i,r) )
#        else: 
#            print('Input from wrong round, round={}  v_i={}, r_i={}'.format(self.round, v_i, r))
#            dump.dump()
# 
#    # TODO check contract with different variable than self.lastround
#    def check_contract(self):
#        pass
##        blockno = self.subroutine_block_number()
##        txs = self.G.subroutine_call((
##            (self.sid, self.pid), True,
##            (False, ('get-txs', self.C, blockno-1, self.lastround))
##        ))
##        print("TXS", txs)
#
#    def send_batch(self):
#        print('\n\t\t self.aux_in={}'.format(self.aux_in))
#        #assert len(self.aux_in) <= 1, "More than one aux_in={}".format(self.aux_in)
#        #msg = ('BATCH', self.round, None, list(self.pinputs[self.round].values()))
#        msg = ('BATCH', self.round, self.aux_in if self.aux_in else [], list(self.pinputs[self.round].values()))
#        self.write(self.F_bc, ('bcast',msg))
#        self.expectsign = True
#        self.p2bc.write( ('bcast', msg) )
#
#    def input_pinput(self, p_i, v_i, r):
#        print('[LEADER] received input from', p_i, v_i, r)
#        if r != self.round: dump.dump(); return
#        if p_i not in self.pinputs[r]:
#            self.pinputs[r][p_i] = v_i
#        for p in self.peers:
#            if p not in self.pinputs[self.round]:
#                dump.dump(); return
#        self.send_batch()
#
#    def send_commit(self):
#        msg = ('COMMIT', self.round, list(self.pinputs[self.round].values()))
#        self.expectsig = False
#        self.p2bc.write( ('bcast', msg) )
#
#    def input_psign(self, p_i, r_i, sig):
#        if not self.expectsign: print('Message out of order'); dump.dump(); return
#        print('[LEADER] received SIGN from', p_i, sig)
#        if r_i != self.round: dump.dump(); return
#        if p_i not in self.psigns[r_i]:
#            self.psigns[r_i][p_i] = sig
#        # TODO check signature rather than that the states are all correct
#        for p in self.peers:
#            if p not in self.psigns[r_i]:
#                print('\t\tcurr psigns', self.psigns[self.round], 'P', p, 'r_i', r_i, 'round', self.round)
#                dump.dump(); return
#            else:
#                assert self.psigns[r_i][p] == sig
#        self.send_commit()
#
#    # Check for messages from leader
#    def query_leader(self):
#        pass
#
#    def subroutine_read(self):
#        # TODO: not quite right
#        if not self.lastcommit:
#            z_write( self.sender, self.state )
#        else:
#            z_write( (self.sid, self.pid), self.lastcommit[0])
#       
#    def execute(self, inputs, aux_in):
#        for aux in aux_in:
#            assert aux in self.aux_in, 'Not here \t\tAUX_IN={} \n\t\tself={}'.format(aux_in, self.aux_in)
#        _s, _o = self.U(self.state, inputs, aux_in, self.round)
#        print('New state computed at={}, state={}'.format(self.sender, _s))
#        # TODO don't confirm state until commit is received
#        self.state = _s
#        self.outr = _o
#       
#        # TODO send actual signature
#        self.expectcommit = True
#        self.p2l.write( ('SIGN', self.round, _s) )
#        # TODO set a timeout for waiting for COMMIT message
#
#
#
#    def check_bc(self):
#        if self.flag == 1: return
#        # get all msgs in multicast, filter by leader
#        msgs = self.F_bc.subroutine_call((
#            (self.sid,self.pid),True,
#            ('read',)
#        ))
#        # check that this cround = last_cround + 1, fail otherwise
#        # more than 1 multicast message means failure ==> only leader sends at most one every round
#        assert len(msgs) <= 1, "Too many messages in broadcast={}, msgs={}\nEnvironment skipped a round!".format(len(msgs), msgs)
#        cur_round = self.util_read_clock()
#        assert cur_round == self.clockround or cur_round == self.clockround+1, "Skipped more than one round. Current round={}, clock round={}".format(cur_round, self.clockround)
#        if len(msgs)==0:
#            self.clockround = cur_round
#            dump.dump()
#            return
#        msg,p = msgs[0]
#        print('Message from fBcast msg={} from={}'.format(msg,p))
#        print('self.expectbatch={}, self.expectcommit={}'.format(self.expectbatch,self.expectcommit))
#        if self.flag == 0:
#            # if expect batch
#            if self.expectbatch and msg[0] == 'BATCH':
#                self.expectbatch = False
#                self.expectcommit = True
#                _round,_auxin,_inputs = msg[1:]
#                if self.round == _round:
#                    self.execute(_inputs, _auxin)
#                else: dump.dump()
#            # if expect commit
#            elif self.expectcommit and msg[0] == 'COMMIT':
#                self.expectcommit = False
#                self.inputsent = False
#                _round,_sigs = msg[1:]
#                assert _round == self.round
#                # TODO check commit message
#                self.lastcommit = (self.state, self.outr, _sigs)
#                self.allcommits[self.round] = self.lastcommit
#                self.lastround = _round
#                self.round = self.lastround+1
#                self.aux_in = []
#                print('Update\n\t\tself.lastcommit={}\n\t\tself.lastround={}\n\t\tself.round={}\n'.format(self.lastcommit, self.lastround, self.round))
#                dump.dump()
#            else:
#                dump.dump()
#        else: dump.dump()
#        self.clockround = cur_round
#
#    def _evidence(self, _r):
#        _state,_outr,_sigs = self.allcommits[_r]
#        tx = ('transfer', self.C, 0, ('evidence', (_r, _state, _outr, _sigs)), 'NA')
#        self.write('G_Ledger', tx)
#        self.p2g.write( tx )
#
#    def call_evidence(self, _r):
#        if _r <= self.lastround:
#            self._evidence(_r)
#        else:
#            dump.dump()
#    
#    def handle_dispute(self, r, deadline):
#        if r <= self.lastround:
#            print('\t\t[ProtState{}] Dispute r={} <= lastRound={}'.format(self.sender,r,self.lastround))
##            self.p2g.write( ('transfer', self.C, 0, ('evidence',(self.lastround, *self.lastcommit)), 'NA') )
#            self._evidence( self.lastround )
#        elif r == self.lastround+1:
#            print('\t\t[ProtState{}] Dispute r={} = lastRound+1={}'.format(self.sender,r,self.lastround+1))
#            tx = ('transfer', self.C, 0, ('input',r,self.currentroundinput), 'NA')
#            self.write('G_Ledger', tx)
#            self.flag = 1   # PENDING
#            self.p2g.write( tx  )
#        else:
#            raise Exception('r={}, self.lastround={}'.format(r, self.lastround))
#
#    def tx_check(self):
#        # first check the state channel contract for disputes or other
#        blockno = self.subroutine_block_number()
#        txs = self.G.subroutine_call((
#            (self.sid, self.pid), True,
#            ('get-txs', self.C, blockno-1, self.lastblock)
#        ))
#        # if flag=OK only expect DISPUTE no other transaction
#        if txs:  # fag = OK
#            for tx in txs:
#                to,fro,val,data,nonce = tx
#                output = self.G.subroutine_call((
#                    self.sender, True,
#                    ('read-output', [(fro,nonce)])
#                ))
#                if not output: continue
#                for e in output[0]:
#                    if e[0] == 'EventDispute' and self.flag == 0:
#                        r,deadline = e[1:]
#                        # should set all flags to false and flag=PENDING
#                        self.handle_dispute(r,deadline)
#                        break
#        # check for transactions in CONTRACT_AUX
#        txs = self.G.subroutine_call((
#            (self.sid, self.pid), True,
#            ('get-txs', self.C_aux, blockno-1, self.lastblock)
#        ))
#        
#        if txs:
#            for tx in txs:
#                to,fro,val,data,nonce = tx
#                output = self.G.subroutine_call((
#                    self.sender, True,
#                    ('read-output', [(fro,nonce)])
#                ))
#                if not output: continue
#                for o in output[0]:
#                    self.aux_in.append(o[1:])
#            print('\n\t\t aux_in={}'.format(self.aux_in))
#        self.lastblock = blockno
#                        
#
#        # if flag=PENDING only expect some resolution off-chain or on-chain
#
#        # if flag=OK check for contract aux_in
#
#    #def tx_check(self):
#    #    blockno = self.subroutine_block_number()
#    #    txs = self.G.subroutine_call((
#    #        (self.sid, self.pid), True,
#    #        ('get-txs', self.C, blockno-1, self.lastblock)
#    #    ))
#    #    print('[ProtState {}] Searching for C={} from {} to {} '.format(self.sender,self.C,self.lastblock,blockno-1))
#    #    if txs:
#    #        for tx in txs:
#    #            to,fro,val,data,nonce = tx
#    #            output = self.G.subroutine_call((
#    #                self.sender, True,
#    #                ('read-output', [(fro,nonce)])
#    #            ))
#    #            print('[State Prot {}] {}'.format(self.sender, output))
#    #            for e in output[0]:
#    #                if e[0] == 'EventDispute':
#    #                    r,deadline = e[1:]
#    #                    self.handle_distpute(r,deadline)
#    #                    break
#    #                else:
#    #                    dump.dump()
#    #                    raise Exception('No matching event', e)
#    #    else:
#    #        dump.dump()
#    #        print('No TXS found', txs)
#    #    self.lastblock = blockno
#
#    def input_ping(self):
#        self.tx_check()
#        self.check_bc()
#
#    def input_msg(self, sender, msg):   
#        #print('INPUT MSG', sender, msg)
#        sid,pid = sender
#        if self.sid == sid:         # sent by another party
#            if msg[0] == 'input':
#                self.input_pinput(pid, msg[1], msg[2])
#            elif msg[0] == 'SIGN':
#                self.input_psign(pid, msg[1], msg[2])
#            else: dump.dump()
#        else:                       # sent by environment
#            if msg[0] == 'input':
#                self.input_input(msg[1], msg[2])
#            elif msg[0] == 'ping':
#                self.input_ping()
#            elif msg[0] == 'call-evidence':
#                self.call_evidence(msg[1])
#            else: dump.dump()
#
#    def subroutine_msg(self, sender, msg):
#        if msg[0] == 'read':    
#            return self.subroutine_read()
#
