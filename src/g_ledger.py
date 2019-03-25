import gevent
from gevent.event import AsyncResult
from gevent.queue import Queue, Channel
from hashlib import sha256
from collections import defaultdict
from itm import ITMFunctionality
import dump

ADVERSARY = -1
DELTA = 8

class Ledger_Functionality(object):
    def __init__(self, sid, pid):
        self.txqueue = []
        self.txqueue = defaultdict(list)
        self._balances = defaultdict(int)
        self.contracts = {}
        self.nonces = defaultdict(int)
        self.output = {}
        self.txs = {}
        self.round = 0
        self.sid = sid
        self.pid = pid
        self.DELTA = 8

        self.outputs = defaultdict(Queue)
        self.input = Channel()
        self.adversary_out = Queue()

        self.block_txs = defaultdict(list)
        
        self.functions = {
            'transfer': self.input_transfer,
            'contract-create': self.input_contract_create,
            'tick': self.decide_tick,
            'getbalance': self.getbalance,
            'read-output': self.read_output
        }

        self.restricted = defaultdict(bool)

    def get_caddress(self, sender, addr):
        return sha256(addr.encode() + str(self.nonces[addr]+1).encode()).hexdigest()[24:]

    def txref(self, val, sender):
        return {
                'value': val,
                'sender': sender,
                'blocknumber': self.round,
               }

    def set_backdoor(self, _backdoor):
        self.adversary_out = _backdoor

    def getbalance(self, sid, pid, addr):
        print('[DEBUG]:', 'writing output for (%s,%s)' % (sid,pid))
        self.outputs[sid,pid].put(self._balances[addr])
        return self._balances[addr]

    def CALL(self,to,fro,data,amt):
        if self._balances[fro] < amt: return 0
        self._balances[fro] -= amt
        self._balances[to] += amt

        if to in self.contracts:
            r = self.Exec(to,amt,data,fro)
            if not r:
                self._balances[fro] += amt
                self.balances[to] -= amt
            return r
  
    def OUT(self,data,sender):
        nonce = self.nonces[sender]
        if (sender,nonce) not in self.output:
            self.output[sender,nonce] = []
        self.output[sender,nonce].append(data)

    def Exec(self,to,val,data,fro):
        if data == ():
            return 1
        func,args = data
        r = getattr(self.contracts[to], func)(*args, self.txref(val, fro))
        # TODO: REVERT CHANGES TO CONTRACT STORAGE WHEN FAILED TX
        # THIS MEANS WE NEED STORAGE TO BE OUTSIDE THE CONTRACT/TEMP
        return r

    def read_output(self, sid, pid, indices):
        print('[DEBUG]:', 'writing output to (%s,%s)' % (sid,pid))
        ret = []
        for sender,nonce in indices:
            ret.append(self.output[sender,nonce])
        return ret

    def input_transfer(self, sid, pid, to, val, data, fro):
        assert self._balances[fro] >= val
        self.txqueue[self.round + self.DELTA].append(('transfer', to, val, data, fro))
        # Leak message to the adversary ONLY if not private
        self.adversary_out.set(((self.sid,self.pid), True, ('transfer',to,val,data,fro)))
        # TODO: is this the right way to do it?
        print('[TX RECEIVED]', 'to (%s), from (%s), data (%s), val (%d)' % (to, fro, data, val))
        #dump.dump()

    def input_contract_create(self, sid, pid, addr, val, data, private, fro):
        assert self._balances[fro] >= val
        compute_addr = sha256(fro.encode() + str(self.nonces[fro]+1).encode()).hexdigest()[24:]
        assert compute_addr == addr, 'Given address: %s, computed address %s, nonce: %s' % (addr, compute_addr, self.nonces[fro]+1)
        assert data is not None
        self.txqueue[self.round + self.DELTA].append(('contract-create', addr, val, data, fro, private))
        # Leak to adversary only if not private
        self.adversary_out.set( ((self.sid,self.pid), True, ('contract-create',addr,val,data,fro,private)))

        print('[DEBUG]', 'tx from', fro, 'creates contract', addr)
        dump.dump()

    def exec_tx(self, sid, to, val, data, fro):
        # Need to check again in case of other txs
        self.nonces[fro] += 1
        assert self._balances[fro] >= val
        self._balances[fro] -= val
        self._balances[to] += val
        if to in self.contracts:
            r = self.Exec(to, val, data, fro)
            self.txs[fro,self.nonces[fro]] = r

    def exec_contract_create(self, sid, addr, val, data, fro, private):
        self.nonces[fro] += 1
        assert self._balances[fro] >= val
        self._balances[fro] -= val
        self._balances[addr] += val
        contract,args = data
        # TODO: just make the contract def the init function
        functions = contract(self.CALL, self.OUT)
        self.contracts[addr] = functions
        print('[CONTRACT CREATE]', 'contract: (%s)' % (addr))
        r = getattr(self.contracts[addr], 'init')(*args, self.txref(val,fro))
        self.restricted[addr] = private

        # unco balance changes if creation failes
        if not r:
            self._balances[fro] += val
            self._balances[addr] -= val

    def input_tick_honest(self, sid, pid, sender):
        self.round += 1
        # WHAT DOES DELAY LOOK LIKE IN PYTHON
        print('Block (%d) mined by (%s)' % (self.round, sender))
        self._balances[sender] += 100000
        for tx in self.txqueue[self.round]:
            if tx[0] == 'transfer':
                self.exec_tx(sid, tx[1], tx[2], tx[3], tx[4])
            elif tx[0] == 'contract-create':
                self.exec_contract_create(sid, tx[1], tx[2], tx[3], tx[4], tx[5])
        dump.dump()
               
    def input_tick_adversary(self, sid, pid, permutation):
        new_txqueue = self.txqueue[self.round].copy() 
        for i,x in enumerate(permuatation):
            new_txqueue[i] = self.txqueue[self.round][x]
        self.txqueue[self.round] = new_txqueue
        self.input_tick_honest()
        dump.dump()

    def block_number(self, sid, pid):
        return self.round

    def decide_tick(self, sid, sender, msg):
        if sender == ADVERSARY:
            self.input_tick_adversary(sid, msg[1])
            print('Adversary mined!')
        else:
            self._balances[sender] += 100000
            print("Miner:", sender, "balance:",self._balances[sender])
            self.input_tick_honest(sid)

    def allowed(self, sender):
        _sid,_pid = sender
        return _sid == self.sid

    def adversary_msg(self, sender, msg):
        sid,pid = None,None
        if sender:
            sid,pid = sender

        if msg[0] == 'tick':
            self.input_tick_adversary(sid,pid,msg[1])

    def input_msg(self, sender, msg):
        sid,pid = None,None
        if sender:
            sid,pid = sender
        
        if msg[0] == 'transfer':
            self.input_transfer(sid, pid, msg[1],msg[2],msg[3],msg[4])
        elif msg[0] == 'contract-create':
            self.input_contract_create(sid, pid, msg[1], msg[2], msg[3], msg[4], msg[5])
        elif msg[0] == 'tick':
            self.input_tick_honest(sid, pid, msg[1])
        else:
            dump.dump()

    def subroutine_msg(self, sender, msg):
        sid,pid = sender
        print('SUBTROUTINE', msg)
        if msg[0] == 'get-caddress':
            return self.get_caddress(sender, msg[1])
        elif msg[0] == 'getbalance':
            return self.getbalance(sid, pid, msg[1])
        elif msg[0] == 'read-output':
            return self.read_output(sid, pid, msg[1])
        elif msg[0] == 'block-number':
            return self.block_number(sid, pid)


def LedgerITM(sid, pid):
    g_ledger = Ledger_Functionality(sid,pid)
    ledger_itm = ITMFunctionality(sid,pid)
    ledger_itm.init(g_ledger)
    return g_ledger,ledger_itm


# Contract definition as a list of functions
# all contracts have an init (constructor)
# and all functions must take in some standard
# blockchain input, TODO: what's a better way to
# this?
def c_printsomething(call, out):
    def init(x):
        return 1

    def printsomething(x,tx):
        print(x)
        out(x, tx['sender'])
        return 1

    return {'init': init, 'printsomething': printsomething}

def Blockchain_IdealProtocol(gfunctionality):
    class Ledger_IdealProtocol(object):
        _instances = {}

        def __init__(self, sid, pid):
            self.sid = sid
            self.pid = pid
            if sid not in Ledger_IdealProtocol._instances:
                Ledger_IdealProtocol._instances[sid] = gfunctionality
            F_Ledger = Ledger_IdealProtocol._instances[sid]

            self.input = F_Ledger.input
            self.output = F_Ledger.outputs[sid,pid]
    return Ledger_IdealProtocol

# 1. Mine a block to get some coins
# 2. Create a contract at a particular address
# 3. check balance to assert that it is correct
# 4. call a function in the contract
# 5. mine the new transaction
# 6. read the logs generated by the transaction
def give_inputs(parties, sid):
    addr = 'abcd'
    print('parties:', len(parties))
    for i in range(len(parties)):
        pid = parties[i].pid
        print('mining...')
        parties[i].input.put(((sid,pid), True,
            ('tick', addr)
        ))
        gevent.sleep()

        print('creating contract...')
        caddress = sha256(addr.encode() + b'1').hexdigest()[24:]
        parties[i].input.put(((sid,pid), True, 
            ('contract-create', caddress, 1, (c_printsomething,()), False, addr)
        ))
        gevent.sleep()

        print('mine next block to process creation...')
        parties[i].input.put(((sid,pid), True,
            ('tick', addr)
        ))
        gevent.sleep()

        print('call getbalance...')
        parties[i].input.put(((sid,pid), True,
            ('getbalance',addr)
        )) 
        gevent.sleep()

        print('get output...')
        result = parties[i].output.get()
        print('Balance of', addr, 'is', result)

        parties[i].input.put(((sid,pid), True,
            ('transfer', caddress, 0, ('printsomething',('42069',)), addr)))
        gevent.sleep()

        parties[i].input.put(((sid,pid), True,
            ('tick', addr)))
        gevent.sleep()

        parties[i].input.put(((sid,pid), True, 
            ('read-output', [(addr, 2)])
        ))
        gevent.sleep()
        result = parties[i].output.get()
        print('Output:', result)

def test_blockchain_protocol():
    idealf = Ledger_Functionality('sid', 0)
    idealitm = ITMFunctionality('sod', 0)
    idealitm.init(idealf)

    # Ideal functionality is pid 0 for now
    ETH = Blockchain_IdealProtocol(idealitm)

    parties = [ETH('sid', i) for i in range(1,2)]
#    functionality = gevent.spawn(parties[0].run)
    functionality = gevent.spawn(idealitm.run)
    inputs = gevent.spawn(give_inputs, parties, 'sid')

    while True:
        gevent.sleep()

if __name__ == '__main__':
    test_blockchain_protocol()

