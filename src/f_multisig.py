import gevent
from gevent.queue import Queue, Channel
from hashlib import sha256
from collections import defaultdict
from itm import ITMFunctionality
import dump

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
        self.adversary_out = None
    
    def set_backdoor(self, _backdoor):
        self.adversary_out = _backdoor

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
            ('block-number',)
        ))

    def subroutine_balance(self, sid, pid):
        return self.balance

    def _deliver_deposit(self, val):
        self.balance += val

    def input_deposit(self, sid, pid, val):
        print('block number', self.subroutine_block_number())
        self.buffer_changes.append((self.subroutine_block_number() + self.DELTA, self._deliver_deposit, val))
        print('[DEPOSIT]', 'deposit received from (%s,%s)' % (sid,pid))
        dump.dump()

    def _deliver_transfer(self, to, val):
        new_transfer_msg = ('transfer', to, val, (), self.addr)
        new_transfer = (pid, new_transfer_msg)
        transfers.append(new_transfer)

    def input_transfer(self, sid, pid, to, val):
        #new_transfer_msg = ('transfer', to, val, (), self.addr)
        #new_transfer = (pid, new_transfer_msg)
        #transfers.append(new_transfer)
        self.buffer_changes.append(
            (self.subroutine_block_number(), _deliver_transfer, to, val)
        )
        dump.dump()

    def _deliver_confirm_transfer(self, idx):
        _sender,_msg = _transfer
        
        if _sender != pid and self.balance >= _msg[2]:
            self.G.input.put(
                (self.sid, self.pid),
                True,
                _msg
            )
            self.balance -= _msg[2]

    def input_confirm_transfer(self, sid, pid, idx):
        #_transfer = transfers[idx]
        #_sender,_msg = _transfer
        #
        #if _sender != pid and self.balance >= _msg[2]:
        #    self.G.input.put(
        #        (self.sid, self.pid),
        #        True,
        #        _msg
        #    )
        #    self.balance -= _msg[2]
        self.buffer_changes.append(
            (self.subroutine_block_number(), _deliver_confirm_transfer, idx)
        )

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
            self.input_confirm_transfer(sid, pid, msg[1], msg[2])
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


class Sim_Multisig:
    def __init__(self, sid, pid, G, F):
        self.sid = sid
        self.pid = pid

