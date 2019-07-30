import dump
import gevent
from itm import ITMFunctionality
from comm import ishonest, isdishonest, isadversary
from queue import Queue as qqueue
from hashlib import sha256
from collections import defaultdict
from gevent.queue import Queue, Channel

class PaymentChannel_Functionality(object):
    def __init__(self, sid, pid, G, p1, p2):
        self.sid = sid
        self.pid = pid
        self.G = G

        self.outputs = defaultdict(Queue)
        self.p1 = p1
        self.p2 = p2
        self.balances = {
            p1: 0,
            p2: 0
        }

        print(p1, p2, self.balances)

        self.transfers = []

        self.buffer_changes = []
        self.DELTA = self.G.F.DELTA
        self.adversary_out = qqueue()
        self.blockno = -1

    def __str__(self):
        return '\033[92mF_pay\033[0m'

    def write(self, to, msg):
        print(u'\033[92m{:>20}\033[0m -----> {}, msg={}'.format('F_pay', str(to), msg))

    def leak(self, msg):
        self.adversary_out.put((
            (self.sid, self.pid),
            True,
            msg
        ))

    def getLeaks(self):
        ret = []
        while not self.adversary_out.empty():
            leak = self.adversary_out.get()
            ret.append(leak)
        self.adversary_out = qqueue()
        adv = comm.adversary
        self.write(adv, ('leaks', ret))
        adv.leak.set((
            (self.sid, self.pid),
            ('leaks', ret)
        ))
        #return ret

    def other_party(self,sid,pid):
        if pid == self.p1:
            return self.p2
        else:
            return self.p1

    def p1balance(self):
        return self.balances[self.p1]
    def p2balance(self):
        return self.balances[self.p2]

    def isplayer(self, sid, pid):
        if pid == self.p1 or pid == self.p2:
            return True
        else:
            print('Accessed by rando')
            return False
    
    def subroutine_balance(self):
        return (self.p1balance(), self.p2balance())

    def input_deposit(self, sid, pid, val):
        self.G.input.set((
            (self.sid, self.pid),
            True,
            (True,
                ('transfer', (self.sid,self.pid), val, (), (sid,pid))
            )
        ))

    def subroutine_block_number(self):
        return self.G.subroutine_call((
            (self.sid,self.pid),
            True,
            (True, ('block-number',))
        ))

    ''' Buffer the output to the other party'''
    def buffer_output(self, sid, pid, msg):
        blockno = self.subroutine_block_number()
        self.buffer_changes.append((blockno+self.DELTA, sid, pid, msg))

    def write_output(self, sid, pid, msg):
        self.outputs[sid,pid].put(msg)

    '''Sender is paying $val to the other party'''
    def input_pay(self, sid, pid, val):
        if self.balances[pid] < val:
            dump.dump(); return

        self.leak( ('pay', (sid,pid), val) )

        self.balances[pid] -= val
        
        # If the sender is corrupted, delay the output to other P
        to_pid = self.other_party(sid,pid)
        to_msg = ('receive', (sid,pid), (self.sid,self.pid), val)
        
        if ishonest(sid,pid):   # If the receiver is honest, write 'pay' immediately
            self.balances[to_pid] += val
            self.write_output(sid, to_pid, to_msg)
        else:   
            # Instead of buffering and all, just submit the transaction
            # to the blockchain and let the adversary delay it according 
            # to the ledger rules. When pinged, the functionality will get
            # transaction from the ledger and deliver the "receive" message
            # TODO: g ledger needs make it easy to track the txs to/from 
            # every address for easy access
            self.G.input.set((
                (self.sid, self.pid),
                True,
                (True, ('transfer', (sid,pid), val, (), (self.sid,self.pid)))
            ))

            #self.buffer_output(sid, to_pid, to_msg)
        dump.dump()

    ''' The channel pays out to the player withdrawing after some balance
        checks. Initiate transaction from itself on the blockchain'''
    def input_withdraw(self, sid, pid, val):
        if self.balances[sid,pid] < val:
            dump.dump(); return

        self.leak( ('withdraw', (sid,pid), val) )
        # Submit a transaction from "channel" to sender
        self.G.input.set((
            (self.sid, self.pid),
            True,
            (True, ('transfer', (sid,pid), val, (), (self.sid,self.pid)))
        ))

    '''Create transaction from the player to the channel.
        Blockchain enforces the balances and delayed delivery'''
    def input_deposit(self, sid, pid, val):
        self.G.input.set((
            (self.sid, self.pid),
            True,
            (True, ('transfer', (self.sid,self.pid), val, (), (sid,pid)))
        ))
    
    '''Check list list of delayed messages and deliver the ones that are ready
        Also check for deposits or transfers from blockchain'''
    def process_buffer(self):
        blockno = self.subroutine_block_number()
        msg = (-1, '')

        while len(self.buffer_changes) and self.buffer_changes[0][0] <= blockno:
            no,sid,pid,msg = self.buffer_changes.pop(0)
            self.G.input.set((
                (self.sid,self.pid),
                True,
                (True, msg)
            ))
            #self.outputs[sid,pid].put(msg)

        '''Check the blockchain for new transactions'''
        txs = self.G.subroutine_call((
            (self.sid,self.pid),
            True,
            (True, ('get-txs', (self.sid,self.pid), blockno, self.blockno))
        ))
        self.blockno = blockno

        # Currently this really only updates balances for deposits
        # should add withdraws as well.
        for tx in txs:
            _to,_fro,_val = tx
          
            if _to == (self.sid,self.pid):          # these are the deposits
                _sid,_pid = _fro
                if _pid == self.p1 or _pid == self.p2: 
                    print('GOT DEPOSIT')
                    self.balances[_pid] += _val
            # withdraws are decremented instantly so that payments can't be made
            # TODO: review sprites paper and see the wd_i shit that they do
            #elif _fro == (self.sid,self.pid):       # these are withdraws
            #    _sid,_pid = _to
            #    if _pid == self.p1 or _pid == self.p2: self.balances[_pid] -= _val

    def backdoor_ping(self):
        self.process_buffer()
        dump.dump()

    def adversary_msg(self, sender, msg):
        sid,pid = None,None
        if sender:
            sid,pid = sender
        if msg[0] == 'get-leaks':
            self.getLeaks()
        elif msg[0] == 'ping':
            self.backdoor_ping()
        else:
            dump.dump()

    def input_msg(self, sender, msg):
        sid,pid = None,None
        if sender:
            sid,pid = sender
         
        if sid != self.sid:
            dump.dump(); return
        if not self.isplayer(sid,pid): 
            dump.dump(); return

        self.process_buffer()
        if msg[0] == 'deposit':
            self.input_deposit(sid, pid, msg[1])
        elif msg[0] == 'withdraw':
            self.input_withdraw(sid, pid, msg[1])
        elif msg[0] == 'pay':
            self.input_pay(sid, pid, msg[1])
        else:
            dump.dump()

    def subroutine_msg(self, sender, msg):
        self.process_buffer()
        sid,pid = None,None
        
        if sender:
            sid,pid = sender

        if not self.isplayer(sid,pid) and not isadversary(sid,pid):
            print('PAY: subroutine access by:', sid, pid)
            return None
        if msg[0] == 'balance':
            return self.subroutine_balance()
        #elif msg[0] == 'get-leaks':
        #    return self.getLeaks()

def PayITM(sid, pid, ledger, p1, p2):
    f = PaymentChannel_Functionality(sid,pid,ledger,p1,p2)
    itm = ITMFunctionality(sid,pid)
    itm.init(f)
    return f, itm


class C_Pay:
    def __init__(self, address, call, out):
        self.address = address
        self.call = call
        self.out = out
        self.p1, self.p2 = None,None
        self.balances = defaultdict(int)
        
    def init(self, p1, p2, tx):
        self.p1 = p1
        self.p2 = p2

    # TODO: send the money back if someone else gives it
    def deposit(self, tx):
        if tx['sender'] != self.p1 and tx['sender'] != self.p2:
            return 0

        self.balances[tx['sender']] += tx['value']
        return 1


class Sim_Payment:
    def __init__(self, sid, pid, G, F, crony, c_payment):
        self.sid = sid
        self.pid = pid
        self.sender = (sid,pid)
        self.crony = crony
        self.cronysid = crony.sid
        self.cronypid = crony.pid
        self.G = G
        self.F = F

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

    def input_ping(self):
        self.write(self.F, ('ping',))
        self.F.backdoor.set((
            self.sender,
            True,
            ('ping',)
        ))

    def input_party(self, to, msg):
        self.write(self.crony, msg)
        self.crony.backdoor.set(msg)

    def input_msg(self, msg):
        if msg[0] == 'delay-tx':
            self.input_delay_tx(msg[1], msg[2], msg[3])
        elif msg[0] == 'ping':
            self.input_ping()
        elif msg[0] == 'party-input':
            self.input_party(msg[1], msg[2])
        else:
            dump.dump()



