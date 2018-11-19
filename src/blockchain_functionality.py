import gevent
from gevent.event import AsyncResult
from gevent.queue import Queue, Channel

# Example definition of a contract, the object can be parameterized and it
# returns a callable object that represents the contract functionality, 
# this design was chosen so that the contract function could handle
# holding all state information and persistent storage of the contract.
def contract_addition():
    def _func(g, a, b):
        return int(a)+int(b)
    return _func

def contract_input(N):
    _inputs = [AsyncResult() for _ in range(N)]

    def _func(g, pid, inp):
        if not _inputs[pid].ready():
            _inputs[pid].set(inp)
    return _func

# Global functions is an object passed into each contract function when
# it is called. It's meant to mimic the globally available variables
# that contracts are supposed to have like the current block number and
# the block hash, the balances of addresses, etc...
class GlobalFunctions(object):
    def __init__(self, blocks, balances, current_block):
        self._blocks = blocks
        self._balances = balances
        self._current_block = current_block 

    def blocknumber(self):
        return self._current_block
   
    def balance(self, a):
        return self._balances[a]

# The main blockchain functionality that is parameterized by some set of 
# contracts. The contracts are callable and transactions to them are
# buffered until someone mines a new block and triggers processing of all
# pending transactions. The ledger tracks the blocks, transactions, 
# events (somewhat, yes) and the transfer of balances.
# TODO: it can only return values to parties that called the contract, so
# a functionality to add is the ability to consume events from the chain.
# This could just be as simple as a buffer where any party consumes events
# until it finds some that it cares about.
class Ledger_Functionality(object):
    def __init__(self, sid, contracts, N, delta=2, block_reward=10):
        self.sid = sid
        self.contracts = contracts
        self.N = N
        self.delta = delta
        self.block_reward = 10

        self.blocks = {}
        self.current_block = 0
        self.balances = {}
        self.buffer_txs = []

        self.outputs = [Queue() for _ in range(N)]
        self.input = Channel()

    def process_tx(self, tx):
        g = GlobalFunctions(self.blocks, self.balances, self.current_block)
        caller,addr,args = tx
        result = self.contracts[addr](g, *args)
        self.outputs[caller].put(result)

    # Processes the transactions in the current buffer when a new
    # block is triggered to be mined when 'tick' is sent to the 
    # functionality. Mining also pays out the beneficiary specified
    # with the command. 
    def new_block(self, beneficiary):
        self.current_block += 1
        new_block = (self.current_block, self.buffer_txs)
        self.blocks[self.current_block] = new_block

        for tx in self.buffer_txs:
            self.process_tx(tx)

        self.buffer_txs = []
    # Continuously running while loop which waits for input transactions
    # and triggers to mine new blocks.
    def run(self):
        while True:
            caller,addr,args = self.input.get()
            
            if addr == 'tick':
                self.new_block(*args)
            else:
                self.buffer_txs.append((caller,addr,args))

# The ideal protocol of the blockchain where users trigger the functionality
# with inputs such as transcations (contract calls only atm) and new blocks.
def Blockchain_IdealProtocol(N):
    class Ledger_IdealProtocol(object):
        _instances = {}
    
        def __init__(self, sid, myid, contracts, N, delta):
            if sid not in Ledger_IdealProtocol._instances:
                Ledger_IdealProtocol._instances[sid] = Ledger_Functionality(sid, contracts, N, delta)
            F_Ledger = Ledger_IdealProtocol._instances[sid]

            self.input = F_Ledger.input
            self.output = F_Ledger.outputs[myid]
            self.run = F_Ledger.run

    return Ledger_IdealProtocol

# Test function where parties give inputs to different contracts then
# tell the blockchain to mine a new block and prcess them.
def give_inputs(parties):
    for i in range(len(parties)):
        print('placing input party', i)
        parties[i].input.put((i,0,[i,i+1]))

    gevent.sleep()

    parties[0].input.put((i,'tick',[]))

    for i in range(len(parties)):
        result = parties[i].output.get()
        print(i,'+', i+1, '=', result) 

    for i in range(len(parties)):
        print('placing input party', i)
        parties[i].input.put((i,0,[i,i+1]))

    gevent.sleep()

    parties[0].input.put((i,'tick',[]))

    for i in range(len(parties)):
        result = parties[i].output.get()
        print(i,'+', i+1, '=', result) 

def test_eth_protocol_simple(N):
    contracts = [contract_addition(), contract_input(N)]
    ETH = Blockchain_IdealProtocol(N)

    parties = [ETH('sid', i, contracts, N, 0) for i in range(N)]

    functionality = gevent.spawn(parties[0].run)
    inputs = gevent.spawn(give_inputs, parties)

    #gevent.joinall([functionality, inputs])

    while True:
        gevent.sleep()

def test_eth_protocol_simple_transfer(N):
    contracts = [contract_addition(), contract_input(N)]
    ETH = Blockchain_IdealProtocol(N)

    parties = [ETH('sid', i, contracts, N, 0) for i in range(N)]

    functionality = gevent.spawn(parties[0].run)
    inputs = gevent.spawn(give_inputs, parties)

    #gevent.joinall([functionality, inputs])

    # Ensure that the main process is alive so that the
    # greenlets don't stop and blockchain can keep running
    while True:
        gevent.sleep()
if __name__=='__main__':
    test_eth_protocol(5)
        

