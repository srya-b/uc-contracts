import dump
import gevent
from itm import ITMFunctionality
from comm import ishonest, isdishonest, isadversary
from queue import Queue as qqueue
from utils import print, gwrite, z_write 
from hashlib import sha256
from collections import defaultdict
from gevent.queue import Queue, Channel

class State_Protocol(object):
    def __init__(self, sid, pid, G, F_bc, C, U, p2g, p2bc, *peers):
        self.sid = sid
        self.pid = pid
        self.sender = (sid,pid)
        self.first = True
        self.sendinput = False

        self.G = G
        self.F_bc = F_bc
        self.C = C          # C here is not the aux contract but contract_state
        self.U = U
        self.p2g = p2g
        self.p2bc = p2bc
        self.outputs = defaultdict(Queue)
        self.peers = peers
        self.leader = False
        self.pleader = None
        self.p2l = None
        self.pinputs = defaultdict(dict)
        self.psigns = defaultdict(dict)
        self.currentroundinput = None
        
        # flag \in {0=OK,1=PENDING}
        self.flag = 0
        self.round = 0
        self.lastround = -1
        self.lastblock = self.subroutine_block_number()
        # TODO: get the current clock time for this sid
        self.clockround = 0
        self.lastcommit = None
        self.inputsent = False
        self.expectbatch = False
        self.expectcommit = False
        self.expectsign = False
        #self.state = None
        #self.outr = None
        # TODO: running U once here to get initial state
        self.state, self.outr = self.U(None, [], None, 0)
        z_write( self.sender, self.state )
        
        ''' The idea here is that state protocol won't send clock-update
            until it has been activated at least twice, enough to check
            for multicasts and to check for transactions to respond to
        '''
        self.activation_state = 0  # 0=wait for check tx, 1=wait for check bc, 2=ready
        self.lastactivationround = 0  # TODO get current clock time

        self.p2c = None; self.clock = None

        # step1=input, step2=batch
        self.step = 1

    def set_leader(self, leaderpid, pleader, p2l):
        if leaderpid==self.pid: self.leader = True
        self.pleader = pleader; self.p2l = p2l

    def printleaders(self):
        print('%s reporting leader: %s' % (self.pid, self.pleader))
        print('Am I the leader %s: %s' % (self.pid, self.leader))

    def __str__(self):
        return '\033[92mProt_state(%s,%s)\033[0m' % (self.sid, self.pid)

    def write(self, to, msg):
        gwrite(u'92m', 'Prot_state(%s,%s)' % (self.sid,self.pid), to, msg)

    def round_number(self):
        return self.G.subroutine_call((
            (self.sid,self.pid), True,
            (True, ('block-number',))
        ))

    def util_read_clock(self):
        return self.clock.subroutine_msg( self.sender, ('clock-read',))
    
    def set_clock(self, c2c, clock):
        self.p2c = c2c; self.clock = clock

    def clock_read(self):
        return self.clock.subroutine_call( self.sender, ('clock-read',))
    
    def subroutine_block_number(self):
        #print('calling blockno')
        return self.G.subroutine_call((
            (self.sid, self.pid),
            True,
            ('block-number',)
        ))


    def input_input(self, v_i, r):
        print('SUBMITTING FOR ROUND', self.round, r, v_i)
        if r == self.round and not self.inputsent:
            # send v_i,r --> leader
            self.write( self.pleader, (v_i,r) ) 
            self.inputsent = True; self.expectbatch = True
            self.currentroundinput = v_i
            self.p2l.write( ('input',v_i,r) )
        else: 
            print('Input from wrong round, round={}  v_i={}, r_i={}'.format(self.round, v_i, r))
            dump.dump()
 
    # TODO check contract with different variable than self.lastround
    def check_contract(self):
        pass
#        blockno = self.subroutine_block_number()
#        txs = self.G.subroutine_call((
#            (self.sid, self.pid), True,
#            (False, ('get-txs', self.C, blockno-1, self.lastround))
#        ))
#        print("TXS", txs)

    def send_batch(self):
        #print('\tTIME FOR SOME BATCHIN BOIS!')
        msg = ('BATCH', self.round, None, list(self.pinputs[self.round].values()))
        #print('BATCH MSG', ('bcast',msg))
        #print("BITTCIN", self.p2bc)
        self.write(self.F_bc, ('bcast',msg))
        self.expectsign = True
        self.p2bc.write( ('bcast', msg) )
        #dump.dump()

    def input_pinput(self, p_i, v_i, r):
        print('[LEADER] received input from', p_i, v_i, r)
        if r != self.round: dump.dump(); return
        if p_i not in self.pinputs[r]:
            self.pinputs[r][p_i] = v_i
        print("\tPEERS", self.peers, "\n\tPINPUTS", self.pinputs)
        for p in self.peers:
            if p not in self.pinputs[self.round]:
                dump.dump(); return
        self.send_batch()

    def send_commit(self):
        #print('\tTIME FOR COMMITTING SOME UNSPEAKABLY GANGSTER SHIT')
        msg = ('COMMIT', self.round, list(self.pinputs[self.round].values()))
        #print('COMMIT MSG', ('bcast', msg))
        self.expectsig = False
        self.p2bc.write( ('bcast', msg) )

    def input_psign(self, p_i, r_i, sig):
        if not self.expectsign: print('Message out of order'); dump.dump(); return
        print('[LEADER] received SIGN from', p_i, sig)
        print('R_i', r_i, 'round', self.round)
        if r_i != self.round: dump.dump(); return
        if p_i not in self.psigns[r_i]:
            self.psigns[r_i][p_i] = sig
        print('\tSIGNS', self.peers, '\n\tPSIGNS', self.psigns)
        # TODO check signature rather than that the states are all correct
        for p in self.peers:
            if p not in self.psigns[r_i]:
                print('type(p)', type(p))
                print('\t\tcurr psigns', self.psigns[self.round], 'P', p, 'r_i', r_i, 'round', self.round)
                dump.dump(); return
            else:
                assert self.psigns[r_i][p] == sig
        self.send_commit()

    # Check for messages from leader
    def query_leader(self):
        pass

    def subroutine_read(self):
        # read from broadcast functionality for input
        #o = self.F_bc.subroutine_call((
        #    (self.sid,self.pid),True,
        #    ('read',)
        #))
        #z_write( (self.sid,self.pid), o )
        #print('\n\n', o, '\n\n')
        # TODO: not quite right
        if not self.lastcommit:
            z_write( self.sender, self.state )
        else:
            z_write( (self.sid, self.pid), self.lastcommit[0])
        #return self.lastcommit[0]
       
    def execute(self, inputs, aux_in):
        _s, _o = self.U(self.state, inputs, aux_in, self.round)
        print('New state computed at={}, state={}'.format(self.sender, _s))
        # TODO don't confirm state until commit is received
        self.state = _s
        self.outr = _o
       
        # TODO send actual signature
        self.expectcommit = True
        self.p2l.write( ('SIGN', self.round, _s) )
        # TODO set a timeout for waiting for COMMIT message

    def check_bc(self):
        o = self.F_bc.subroutine_call((
            (self.sid,self.pid),True,
            ('read',)
        ))
        currround = self.util_read_clock()
        print('CURR ROUND', currround, 'LAST CLOCK ROUND', self.clockround)
        #assert currround == self.clockround + 1
        if currround == self.clockround:
            dump.dump()
            return
        elif currround != self.clockround + 1:
            raise Exception("Curr Round={} - self.clockround={} = {}".format(currround,self.clockround,currround - self.clockround))
        
        print('\n\n', o)
        try:
            for bcast in o[currround]:
                msg = bcast[1]
                if msg[0] == 'BATCH' and self.expectbatch:
                    _round,_auxin,_inputs = msg[1:]
                    self.expectbatch = False
                    print('Expected Batch and got it')
                    # TODO check to make sure my input is in there
                    # TODO check that aux in is "a recent version of aux_in"
                    self.execute(_inputs, _auxin)
                elif msg[0] == 'COMMIT' and self.expectcommit:
                    self.expectcommit = False
                    _r,_sigs = msg[1:]
                    #print('hey hey hey got a commit message {}'.format(self.sender), _sigs)
                    # TODO check commit message
                    self.lastcommit = (self.state, self.outr, _sigs) 
                    self.lastround = _r 
                    assert self.lastround == self.round, 'lastround={} round={}'.format(self.lastround, self.round)
                    self.round = self.lastround + 1
                    self.inputsent = False
                    print('Last commit={}, lastround={}'.format(self.lastcommit, self.lastround))
                    # TODO if outr is not None, do an on-chain transaction
                    dump.dump()
                else:
                    print('Got an unexpected message!', msg)
                    dump.dump()
        except KeyError:
            print('NO OUTPUT FOR ROUND', currround)
            dump.dump()
        self.clockround = currround

    def handle_distpute(self, r, deadline):
        if r <= self.lastround:
            print('\t\t[ProtState{}] Dispute r={} <= lastRound={}'.format(self.sender,r,self.lastround))
            # TODO call "evidence" on the contract and give evidence and actual sigs
            self.p2g.write( ('transfer', self.C, 0, ('evidence',(self.lastround, *self.lastcommit)), 'NA') )
        elif r == self.lastround+1:
            print('\t\t[ProtState{}] Dispute r={} = lastRound+1={}'.format(self.sender,r,self.lastround+1))
            # TODO update lastRound and do some more
            self.flag = 1   # PENDING
            # TODO set all flags to False, basically act as if nothing has happened in this round
            #       buffer inputs already given until fast path starts again
            self.p2g.write( ('transfer', self.C, 0, ('input',r,self.currentroundinput), 'NA') )
        else:
            raise Exception('r={}, self.lastround={}'.format(r, self.lastround))

    def tx_check(self):
        blockno = self.subroutine_block_number()
        txs = self.G.subroutine_call((
            (self.sid, self.pid), True,
            ('get-txs', self.C, blockno-1, self.lastblock)
        ))
        print('[ProtState {}] Searching for C={} from {} to {} '.format(self.sender,self.C,self.lastblock,blockno-1))
        if txs:
            for tx in txs:
                to,fro,val,data,nonce = tx
                output = self.G.subroutine_call((
                    self.sender, True,
                    ('read-output', [(fro,nonce)])
                ))
                print('[State Prot {}] {}'.format(self.sender, output))
                for e in output[0]:
                    if e[0] == 'EventDispute':
                        r,deadline = e[1:]
                        self.handle_distpute(r,deadline)
                        break
                    else:
                        dump.dump()
                        raise Exception('No matching event', e)
        else:
            dump.dump()
            print('No TXS found', txs)
        self.lastblock = blockno
    
    def input_ping(self):
        print('PING ProtState {}: activation_state={}'.format(self.sender, self.activation_state))
        currround = self.util_read_clock()
        #print('PING currround={}, lastactivationround={}'.format(currround, self.lastactivationround))
        if currround > self.lastactivationround: # ready to reset activation state
            self.activation_state = 0
            assert currround == self.lastactivationround+1, 'curround={}, lastround={}'.format(currround,self.lastactivationround)
            self.lastactivationround = currround
        #print('2. PING ProtState {}: activation_state={}'.format(self.sender, self.activation_state))

        if self.activation_state == 0:
            self.tx_check()
            self.activation_state = 1
        elif self.activation_state == 1:
            self.check_bc()
            self.activation_state = 2
        else: dump.dump()

    ''' 
        Raise exception here if the environment asks for clock-update without proper input
        being sent 
    '''
    def clock_update_ready(self):
        # clock update ready only after 2 activations
        print('\t\t[Prot {}] update ready? activation_state={}'.format(self.sender,self.activation_state))
        if self.activation_state > 1:
            return True
        return False    

    #def clock_update_ready2(self):
    #    

    def input_msg(self, sender, msg):   
        #print('INPUT MSG', sender, msg)
        sid,pid = sender
        if self.sid == sid:
            if msg[0] == 'input':
                self.input_pinput(pid, msg[1], msg[2])
            elif msg[0] == 'SIGN':
                self.input_psign(pid, msg[1], msg[2])
            else: dump.dump()
        else:
            if msg[0] == 'input':
                self.input_input(msg[1], msg[2])
            elif msg[0] == 'ping':
                self.input_ping()
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
        if r != self.bestRound+1: return
        if self.flag != 2: return # PENDING
        if tx['blocknumber'] < self.deadline: return

        for p in self.ps:
            if p not in self.pinputs[r]: self.pinputs[r][p] = None # Default value

        self.state = self.U(self.state, self.pinputs[r].values(), None)
        self.flag = 0   # OK
        self.out( ('EventOnchain', r, self.state), tx['sender'])
        self.bestRound += 1


class Adv:
    def __init__(self, sid, pid, G, F, crony, c_payment, a2g):
        self.sid = sid
        self.pid = pid
        self.sender = (sid,pid)
        self.crony = crony
        self.G = G
        self.F = F
        self.a2g = a2g

    def __str__(self):
        return '\033[91mAdversary (%s, %s)\033[0m' % (self.sid, self.pid) 

    def write(self, to, msg):
        #print('\033[91m{:>20}\033[0m -----> {}, msg={}'.format('Adversary (%s,%s)' % (self.sid, self.pid), str(to), msg))
        gwrite(u'91m', 'Adversary (%s,%s)' %(self.sid,self.pid), to, msg)

    #def input_delay_tx(self, fro, nonce, rounds):
    #    msg=('delay-tx', fro, nonce, rounds)
    #    self.write(self.G, msg)
    #    self.G.backdoor.set((
    #        self.sender,
    #        True,
    #        (False, msg)
    #    ))
    
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
        # Get the mapping from (sid,pid) of F to address
        f_addr = self.G.subroutine_call((
            (self.sid,self.pid),
            True,
            ('get-addr', addr)
        ))

        assert f_addr is not None

        if f_addr == addr:
            print('LULZ')
            return 'lulz'


    def input_party(self, to, msg):
        self.write(self.crony, msg)
        self.crony.backdoor.set(msg)

    def input_msg(self, msg):
        if msg[0] == 'delay-tx':
            self.input_delay_tx(msg[1], msg[2], msg[3])
        elif msg[0] == 'party-input':
            self.input_party(msg[1], msg[2])
        elif msg[0] == 'tick':
            self.input_tick(msg[1])
        else:
            #print('** adv input_msg dump **')
            dump.dump()

    def subroutine_msg(self, msg):
        if msg[0] == 'get-contract':
            return self.subroutine_get_contract(msg[1])

