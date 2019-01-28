import gevent
from gevent.event import AsyncResult
from gevent.queue import Queue, Channel
from hashlib import sha256
from collections import defaultdict

ADVERSARY = -1

class Ledger_Functionality(object):
    def __init__(self, sid):
        self.txqueue = []
        self._balances = defaultdict(int)
        self.contracts = {}
        self.nonces = defaultdict(int)
        self.output = {}
        self.txs = {}
        self.round = 0

        self.outputs = defaultdict(Queue)
        self.input = Channel()
        self.adversary_out = Queue()

    def txref(self, val, sender):
        return {
                'value': val,
                'sender': sender,
                'blocknumber': self.round,
               }


    def getbalance(self, sid, addr):
        self.outputs[sid].put(self._balances[addr])

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
        r = self.contracts[to][func](*args, self.txref(val,fro))
        # TODO: REVERT CHANGES TO CONTRACT STORAGE WHEN FAILED TX
        # THIS MEANS WE NEED STORAGE TO BE OUTSIDE THE CONTRACT/TEMP
        return r

    def read_output(self, sid, indices):
        for sender,nonce in indices:
            self.outputs[sid].put(self.output[sender,nonce])

    def input_transfer(self, sid, to, val, data, fro):
        assert self._balances[fro] >= val
        self.txqueue.append(('transfer',to,val,data,fro))
        # Leak message to the adversary
        self.adversary_out.put(('transfer',to,val,data,fro))  

    def input_contract_create(self, sid, addr, val, data, fro):
        assert self._balances[fro] >= val
        assert sha256(fro.encode() + str(self.nonces[fro]+1).encode()).hexdigest()[24:] == addr
        assert data is not None
        self.txqueue.append(('contract-create',addr,val,data,fro))
        # Leak to adversary
        self.adversary_out.put(('contract-create',addr,val,data,fro))

        print('[DEBUG]', 'tx from', fro, 'creates transaction', addr)

    def exec_tx(self, sid, to, val, data, fro):
        # Need to check again in case of other txs
        self.nonces[fro] += 1
        assert self._balances[fro] >= val
        self._balances[fro] -= val
        self._balances[to] += val
        if to in self.contracts:
            r = self.Exec(to, val, data, fro)
            self.txs[fro,self.nonces[fro]] = r

    def exec_contract_create(self, sid, addr, val, data, fro):
        self.nonces[fro] += 1
        assert self._balances[fro] >= val
        self._balances[fro] -= val
        self._balances[addr] += val
        contract,args = data
        # TODO: just make the contract def the init function
        functions = contract(self.CALL, self.OUT)
        self.contracts[addr] = functions
        r = self.contracts[addr]['init'](*args, self.txref(val,fro))

        # unco balance changes if creation failes
        if not r:
            self._balances[fro] += val
            self._balances[addr] -= val

    def input_tick_honest(self, sid):
        self.round += 1
        # WHAT DOES DELAY LOOK LIKE IN PYTHON

        for tx in self.txqueue:
            if tx[0] == 'transfer':
                self.exec_tx(sid, tx[1], tx[2], tx[3], tx[4])
            elif tx[0] == 'contract-create':
                self.exec_contract_create(sid, tx[1], tx[2], tx[3], tx[4])
        
        self.txqueue = []
               
    def input_tick_adversary(self, sid, permutation):
        new_txqueue = self.txqueue.copy() 
        for i,x in enumerate(permuatation):
            new_txqueue[i] = self.txqueue[x]
        self.txqueue = new_txqueue
        self.input_tick_honest()

    def run(self):
        while True:
            sid,sender,msg = self.input.get()
            print('Received message:', msg, 'from:', sender)

            if msg[0] == 'transfer':
                self.input_transfer(sid, msg[1],msg[2],msg[3],sender)
            elif msg[0] == 'contract-create':
                self.input_contract_create(sid, msg[1], msg[2], msg[3], sender)
            elif msg[0] == 'tick':
                if sender == ADVERSARY:
                    self.input_tick_adversary(sid, tx[1])
                    print('Adversary mined!')
                else:
                    self._balances[sender] += 100000
                    print("Miner:", sender, "balance:",self._balances[sender])
                    self.input_tick_honest(sid)
            elif msg[0] == 'getbalance':
                self.getbalance(sid, msg[1])
            elif msg[0] == 'read-output':
                self.read_output(sid, msg[1])
                 

# Contract definition as a list of functions
# all contracts have an init (constructor)
# and all functions must take in some standard
# blockchain input, TODO: what's a better way to
# this?
def c_printsomething(call, out):
    def init():
        return 1

    def printsomething(x,tx):
        print(x)
        out(x, tx['sender'])
        return 1

    return {'init': init, 'printsomething': printsomething}

def Blockchain_IdealProtocol():
    class Ledger_IdealProtocol(object):
        _instances = {}

        def __init__(self, sid, myid):
            if sid not in Ledger_IdealProtocol._instances:
                Ledger_IdealProtocol._instances[sid] = Ledger_Functionality(sid)
            F_Ledger = Ledger_IdealProtocol._instances[sid]

            self.input = F_Ledger.input
            self.output = F_Ledger.outputs[myid]
            self.run = F_Ledger.run
    return Ledger_IdealProtocol

# 1. Mine a block to get some coins
# 2. Create a contract at a particular address
# 3. check balance to assert that it is correct
# 4. call a function in the contract
# 5. mine the new transaction
# 6. read the logs generated by the transaction
def give_inputs(parties):
    addr = 'abcd'
    for i in range(len(parties)):
        print('mining...')
        parties[i].input.put((i,addr, ('tick',)))
        gevent.sleep()

        print('creating contract...')
        caddress = sha256(addr.encode() + b'1').hexdigest()[24:]
        parties[i].input.put(
            (i, addr, 
            ('contract-create', caddress, 1, (c_printsomething,()) )
            ))
        gevent.sleep()

        print('mine next block to process creation...')
        parties[i].input.put((i, addr, ('tick',)))
        gevent.sleep()

        parties[i].input.put((i, addr, ('getbalance',addr))) 
        gevent.sleep()

        result = parties[i].output.get()
        print('Balance of', addr, 'is', result)

        parties[i].input.put((i,addr,
            ('transfer', caddress, 0, ('printsomething',('42069',)),addr)))
        gevent.sleep()

        parties[i].input.put((i,addr,
            ('tick',)))
        gevent.sleep()

        parties[i].input.put((i,addr,
            ('read-output', [(addr, 2)])))
        gevent.sleep()
        result = parties[i].output.get()
        print('Output:', result)

def test_blockchain_protocol():
    ETH = Blockchain_IdealProtocol()

    parties = [ETH('sid', i) for i in range(1)]
    functionality = gevent.spawn(parties[0].run)
    inputs = gevent.spawn(give_inputs, parties)

    while True:
        gevent.sleep()

if __name__ == '__main__':
    test_blockchain_protocol()

