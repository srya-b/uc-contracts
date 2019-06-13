import gevent
import comm 
import dump
from itm import ITMFunctionality
from utils import print
from hashlib import sha256
from collections import defaultdict
from gevent.queue import Queue, Channel

DELTA = 8

class Multisig_Functionality(object):
    def __init__(self, sid, pid, G, p1, p2, addr):
        self.sid = sid
        self.pid = pid
        self.G = G
        self.addr = addr
        
        self.outputs = defaultdict(Queue)
        self.p1 = p1
        self.p2 = p2
        self.balance = 0
        self.transfers = []

        self.buffer_changes = []
        self.DELTA = self.G.F.DELTA 

        # TODO: should this be queue or channel? 
        self.adversary_out = Queue()
   
    def __str__(self):
        #return 'asd'
        return '\033[92mF_multisig\033[0m'

    def write(self, to, msg):
        print(u'\033[92m{:>20}\033[0m -----> {}, msg={}'.format('F_multisig', str(to), msg))
                  
    def leak(self, msg):
        self.write(comm.adversary, msg)
        self.adversary_out.put(
            (self.sid, self.pid),
            True,
            msg
        )

    def process_buffer(self):
        number = self.subroutine_block_number()

        if len(self.buffer_changes) == 0: 
            return
        if self.buffer_changes[0][0] > number:
            return
        #change = self.buffer_changes.pop(0)
        change = (-1,)
        while self.buffer_changes[0][0] <= number:
            change = self.buffer_changes.pop(0)
            change[1](*change[2:])
            if len(self.buffer_changes) == 0:
                break

    def subroutine_block_number(self):
        return self.G.subroutine_call((
            (self.sid, self.pid),
            True,
            (True, ('block-number',))
        ))

    '''
        This just queries the functionality's balance in G_ledger
    '''
    def subroutine_balance(self, sid, pid):
        return self.G.subroutine_call((
            (self.sid,self.pid),
            True,
            (True, ('getbalance', (self.sid,self.pid)))
        ))

    '''
        In this case, we want a transaction to occurr in the underlying
        blockchain functionality, so directly submit the transaction
        to G_ledger and that will do the buffer.
        TODO: this functionality should poll the blockchain for transactions
        that it received, like wallet software.
    '''
    def input_deposit(self, sid, pid, val):
        msg = ('transfer', (self.sid,self.pid), val, (), (sid,pid))
        self.write(self.G, msg)
        self.G.input.set((
            (self.sid,self.pid),
            True,
            (True, msg
                #('transfer', (self.sid,self.pid), val, (), (sid,pid))
            )
        ))
        #dump.dump()

    def _deliver_transfer(self, to, val):
        new_transfer_msg = (True, ('transfer', to, val, (), (self.sid, self.pid)))
        self.transfers.append(new_transfer_msg)

    def input_transfer(self, sid, pid, to, val):
        self.buffer_changes.append(
            (self.subroutine_block_number(), self._deliver_transfer, to, val)
        )
        
        self.leak( ('transfer', to, val) )
        dump.dump()

    def _deliver_confirm_transfer(self, idx):
        _wrapper,_msg = self.transfers[idx]
        
        if self.subroutine_balance(self.sid,self.pid) >= _msg[2]:
            print('Sending transfer to ledger')
            self.G.input.set((
                (self.sid, self.pid),
                True,
                (_wrapper,_msg)
            ))
            self.balance -= _msg[2]
        else:
            dump.dump()

    '''
        Confirm transactions will end up creating the transaction
        anyway so the ledger can buffer for us. Therefore, send the 
        transaction immediately
    '''
    def input_confirm_transfer(self, sid, pid, idx):
        _wrapper,_msg = self.transfers[idx]

        if self.subroutine_balance(self.sid,self.pid) >= _msg[2]:
            print('sending confirm')
            self.G.input.set((
                (self.sid, self.pid),
                True,
                (_wrapper, _msg)
            ))
        else:
            dump.dump()

    def backdoor_ping(self, sid, pid):
        self.process_buffer()
        dump.dump()

    def input_msg(self, sender, msg):
        sid,pid = None,None
        if sender:
            sid,pid = sender

        if pid != self.p1 and pid != self.p2:
            dump.dump()
            return

        self.process_buffer()

        if msg[0] == 'deposit':
            self.input_deposit(sid, pid, msg[1])
        elif msg[0] == 'transfer':
            self.input_transfer(sid, pid, msg[1], msg[2])
        elif msg[0] == 'confirm':
            self.input_confirm_transfer(sid, pid, msg[1])
        else:
            dump.dump()

    def subroutine_msg(self, sender, msg):
        self.process_buffer()
        sid,pid = None,None
        if sender:
            sid,pid = sender

        if pid != self.p1 and pid != self.p2:
            print(pid, self.p1, self.p2)
            return None
        
        if msg[0] == 'balance':
            return self.subroutine_balance(sid, pid)

    def backdoor_msg(self, sender, msg):
        sid,pid = None,None
        if sender:
            sid,pid = sender

        if msg[0] == 'ping':
            self.backdoor_ping()

def MultisigITM(sid, pid, ledger, p1, p2, caddr):
    f = Multisig_Functionality(sid, pid, ledger, p1, p2, caddr)
    itm = ITMFunctionality(sid,pid)
    itm.init(f)
    return f,itm

class C_Multisig:
    def __init__(self, address, call, out):
        self.call = call
        self.out = out
        self.p1, self.p2 = None,None
        self.balance = 0
        self.transfers = []
        self.address = address

    def init(self, p1, p2, tx):
        self.p1 = p1
        self.p2 = p2

    def balance(self, tx):
        self.out(self.balances, tx['sender'])

    def owner(self, p):
        return p == self.p1 or p == self.p2

    def deposit(self, tx):
        if tx['sender'] != self.p1 and tx['sender'] != self.p2:
            return 0

        self.balance += tx['value']
        return 1 

    def transfer(self, amt, to, tx):
        if not self.owner(tx['sender']):
            return 0

        _transfer = (to, amt, tx['sender'])
        self.transfers.append(_transfer)
        return 1

    def confirm(self, idx, tx):
        if not self.owner(tx['sender']):
            return 0
        to,amt,sender = self.transfers[idx]

        if sender == tx['sender']:
            return 0
        if self.balance < amt:
            return 0

        self.balance -= amt
        self.call(to, self.address, (), amt)
        return 0

import inspect

class Sim_Multisig:
    def __init__(self, sid, pid, G, F, crony, c_multisig):
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
        print('\033[91m{:>20}\033[0m -----> {}, msg={}'.format('Simulator (%s,%s)'%(self.sid,self.pid), str(to), msg))
        #print('%s:<15 -----> %s\tmsg=%s' % (str(self), str(to), msg))

    '''
        On receiving deposit from Z, simulator
        just passes 'deposit' to the functionality
    '''
    def input_deposit(self, val):
        msg = ('deposit', val)
        self.write(self.crony, msg)
        self.crony.input.set(msg)

    '''
        Create a transfer
    '''
    def input_transfer(self, to, val):
        msg = ('transfer', to, val)
        self.write(self.crony, msg)
        self.crony.input.set(msg)

    def input_confirm(self, idx):
        msg = ('confirm', idx)
        self.write(self.crony, msg)
        self.crony.input.set(msg)

    def input_tick(self, permutation):
        msg = (self.sender, True, (True, ('tick', perm)))
        self.write(self.G, msg)
        self.G.backdoor.set((
            self.sender,
            True,
            (True, ('tick', perm))
        ))

    def input_delay_tx(self, fro, nonce, rounds):
        msg = ('delay-tx', fro, nonce, rounds)
        self.write(self.G, msg)
        self.G.backdoor.set((
            self.sender,
            True,
            (False, msg)
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
            return 'lulz'
    
    #def input_msg(self, msg):
    #    if msg[0] == 'tick':
    #        self.input_tick(msg[1])
    #    else:
    #        dump.dump()
    #        print('[WARNING] Environment requested functionality contract')
    #        # Create the contract with 
    #        source = inspect.getsource(c_multisig).split(':',1)[1]
    #    else:
    #        source = self.G.subroutine_call((
    #            (self.sid, self.pid),
    #            True,
    #            (True, ('get-contract'))
    #        ))
    #    print('SIMULATOR got source:', source[:20])
    #    return source

    def input_msg(self, msg):
        if msg[0] == 'transfer':
            self.input_transfer(msg[1], msg[2])
        elif msg[0] == 'deposit':
            self.input_deposit(msg[1])
        elif msg[0] == 'confirm':
            self.input_confirm(msg[1])
        elif msg[0] == 'tick':
            self.input_tick(msg[1])
        elif msg[0] == 'delay-tx':
            self.input_delay_tx(msg[1], msg[2], msg[3])
        else:
            dump.dump()

    def subroutine_msg(self, msg):
        if msg[0] == 'get-contract':
            return self.subroutine_get_contract(msg[1])

