import dump
import comm
import copy
import gevent
import inspect
from itm import ITMFunctionality
from utils import print, gwrite
from queue import Queue as qqueue
from hashlib import sha256
from collections import defaultdict
from gevent.event import AsyncResult
from gevent.queue import Queue, Channel

ADVERSARY = -1
DELTA = 8

class Ledger_Functionality(object):
    def __init__(self, sid, pid):
        self.txqueue = defaultdict(list)
        self.newtxs = dict()
        self._balances = defaultdict(int)
        self.contracts = {}
        self.nonces = defaultdict(int)
        self.output = {}
        self.txs = {}
        self.round = 0
        self.sid = sid
        self.pid = pid
        self.DELTA = 1
        self.g2c = None
        self.clock = None
        #self.t_L = 0
        self.t_L = defaultdict(int)

        self.outputs = defaultdict(Queue)
        self.input = Channel()
        self.adversary_out = qqueue()
        self.receipts = defaultdict(dict)

        self.block_txs = defaultdict(list)
        
        self.functions = {
            'transfer': self.input_transfer,
            'contract-create': self.input_contract_create,
            'tick': self.decide_tick,
            'getbalance': self.getbalance,
            'read-output': self.read_output
        }

        self.restricted = defaultdict(bool)

    def __str__(self):
        return '\033[92mG_ledger\033[0m'

    @property
    def windowSize(self):
        return self.round

    @property
    def nu(self):
        return int(self.round / 2)

    def set_clock(self, c2c, clock):
        print('LEDGER SET CLOCK', c2c, clock)
        self.g2c = c2c; self.clock = clock

    def write(self, to, msg):
        #print(u'\033[92m{:>20}\033[0m -----> {}, msg={}'.format('G_ledger', str(to), msg))
        gwrite(u'92m', 'G_ledger', to, msg)

    def leak(self, msg):
        #self.write( comm.adversary, msg )
        self.adversary_out.put((
            (self.sid, self.pid),
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

    def get_contract(self, sid, pid, addr):
        if addr in self.contracts:
            return inspect.getsource(type(self.contracts[addr])).split(':',1)[1] 
        else:
            return ''

    def get_caddress(self, sid, pid, addr):
        sender = (sid,pid)
        return sha256(str(addr).encode() + str(self.nonces[addr]+1).encode()).hexdigest()[24:]

    def compute_address(self, sid, pid, addr, nonce):
        sender = (sid,pid)
        return sha256(str(addr).encode() + str(nonce).encode()).hexdigest()[24:]

    def get_nonce(self, sid, pid, addr):
        return self.nonces[addr]

    def txref(self, val, sender):
        return {
                'value': val,
                'sender': sender,
                'blocknumber': self.round,
               }

    def getbalance(self, sid, pid, addr):
        #print('[DEBUG]:', 'writing output for (%s,%s)' % (sid,pid))
        self.outputs[sid,pid].put(self._balances[addr])
        return self._balances[addr]

    def get_txs(self, sid, pid, addr, to, fro):
        if fro > to: print('da fuck'); return []
        output = []
        print('Searching txs, fro={}, to={}, addr={:.10}'.format(fro, to, addr))
        #print('txqueue round={}, queue={}'.format(fro-1, self.txqueue[fro-1]))
        for blockno in range(fro,to+1):
            txqueue = self.txqueue[blockno]
            #print('Get tx round', blockno, 'txs', txqueue)
            #print('txqueue round={}, queue={}, to={}, from={}'.format(blockno,txqueue,to,fro))
            for tx in txqueue:
                if tx[0] == 'transfer':
                    ########
                    to,val,data,fro,nonce = tx[1:]
                    if to == addr or fro == addr:
                        #print('to', to, 'from', fro, 'addr', addr)
                        output.append((to,fro,val,data,nonce))
        #print('Returning transactions:', output)
        return output

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
        print('PRINT: sender={}, nonce={}, msg={}'.format(sender, nonce, data))
        self.output[sender,nonce].append(data)

    def Exec(self,to,val,data,fro):
        if data == ():
            return 1
        func,args = data
        _tx = self.txref(val, fro)
        r = getattr(self.contracts[to], func)(*args, _tx)
        if 'return' in _tx:
            print('Contract returned something:', _tx['return'])
        self.receipts[fro, self.nonces[fro]] = _tx
        # TODO: REVERT CHANGES TO CONTRACT STORAGE WHEN FAILED TX
        # THIS MEANS WE NEED STORAGE TO BE OUTSIDE THE CONTRACT/TEMP
        return r

    def read_output(self, sid, pid, indices):
        ret = []
        for sender,nonce in indices:
            try:
                ret.append(self.output[sender,nonce])
            except KeyError: continue
        return ret

    def input_delay_tx(self, fro, nonce, rounds):
        tx = self.newtxs[fro,nonce]
        self.txqueue[self.round + rounds].append( (*tx, nonce) )
        del self.newtxs[fro,nonce]
        #print('** delay tx dump **')
        dump.dump()

    def input_transfer(self, sid, pid, to, val, data, fro):
        print('TRANSFERRING to', to, 'sid,pid', sid, pid, 'val', val, 'fro', fro)
        assert self._balances[fro] >= val
        self.nonces[fro] += 1
        self.newtxs[fro,self.nonces[fro]] = ('transfer', to, val, data, fro)
        # Leak message to the adversary ONLY if not private
        self.leak( ((fro,self.nonces[fro]),('transfer', to, val, data, fro)) )
        #print('** transfer dump **')
        dump.dump()

    ''' Functionality chooses how long to delay tx
        Need to consider for other transactions as well where adversary can
        delay tx like 'deposit'.'''
    def input_transfer_f(self, sid, pid, fro, nonce, rounds):
        assert self._balances[fro] >= val
        self.nonces[fro] += 1
        self.newtxs[fro,self.nonces[fro]] = ('transfer', to, val, data, fro)
        self.input_delay_tx(sid,pid,fro,nonce,rounds)

    def input_contract_create(self, sid, pid, addr, val, data, private, fro):
        assert self._balances[fro] >= val
        self.nonces[fro] += 1
        # TODO finalize and test without pseudonyms
        #compute_addr = sha256(fro.encode() + str(self.nonces[fro]).encode()).hexdigest()[24:]
        compute_addr = sha256(str(fro).encode() + str(self.nonces[fro]).encode()).hexdigest()[24:]
        assert compute_addr == addr, 'Given address: %s, computed address %s, nonce: %s' % (addr, compute_addr, self.nonces[fro]+1)
        assert data is not None
        self.newtxs[fro,self.nonces[fro]] = ('contract-create', addr, val, data, fro, private)
        # Leak to adversary only if not private
        self.leak( ((fro,self.nonces[fro]),('contract-create',addr,val,data,fro,private)) )
        #print('** contract create dump **')
        dump.dump()

    def exec_tx(self, to, val, data, fro):
        # Need to check again in case of other txs
        assert self._balances[fro] >= val
        self._balances[fro] -= val
        self._balances[to] += val
        self.receipts[fro,self.nonces[fro]] = self.txref(val, fro)
        if to in self.contracts:
            print('\t[G_ledger] EXEC function "{}" in {}'.format(data,to))
            r = self.Exec(to, val, data, fro)
            self.txs[fro,self.nonces[fro]] = r

    def exec_contract_create(self, addr, val, data, fro, private):
        assert self._balances[fro] >= val
        self._balances[fro] -= val
        self._balances[addr] += val
        contract,args = data
        # TODO: just make the contract def the init function
        functions = contract(addr, self.CALL, self.OUT)
        self.contracts[addr] = functions
        print('[CONTRACT CREATE]', 'contract: (%s)' % (addr))
        r = getattr(self.contracts[addr], 'init')(*args, self.txref(val,fro))
        self.restricted[addr] = private

        # unco balance changes if creation failes
        if not r:
            self._balances[fro] += val
            self._balances[addr] -= val

    def subroutine_contractref(self, sid, pid, addr):
        return self.contracts[addr]

    def input_tick_honest(self, sender):
        self.round += 1
        # WHAT DOES DELAY LOOK LIKE IN PYTHON
        self._balances[sender] += 100000
        print('\n\tBLOCK #{}:'.format(self.round-1))
        for tx in self.txqueue[self.round-1]:
            print('\t\t TX:to={:.10}, val={}, data={}, fro={:.10}'.format(str(tx[1]),tx[2],tx[3],str(tx[4])))
            if tx[0] == 'transfer':
                self.exec_tx(tx[1], tx[2], tx[3], tx[4])
            elif tx[0] == 'contract-create':
                self.exec_contract_create(tx[1], tx[2], tx[3], tx[4], tx[5])
        print('\n')
        #print('Next Round from', self.round-1, 'to', self.round, 'txs', self.txqueue[self.round-1])
        #print('** tick honest dump **')
        dump.dump()
               
    def input_tick_adversary(self, sid, pid, addr, permutation):
        new_txqueue = self.txqueue[self.round+1].copy() 
        for i,x in enumerate(permutation):
            new_txqueue[i] = self.txqueue[self.round+1][x]
        self.txqueue[self.round+1] = new_txqueue
        self.input_tick_honest(sid, pid, addr)
        #print('** adv tick dump **')
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

    def util_read_clock(self, sid):
        t = self.clock.subroutine_msg( (sid,-1), ('clock-read',))
        self.t_L[sid] = t 

    def allowed(self, sender):
        _sid,_pid = sender
        return _sid == self.sid

    def adversary_msg(self, msg):
        #sid,pid = None,None
        #if sender:
        #    sid,pid = sender
        if msg[0] == 'tick':
            self.input_tick_adversary(msg[1], msg[2])
        elif msg[0] == 'get-leaks':
            self.getLeaks()
        elif msg[0] == 'delay-tx':
            self.input_delay_tx(msg[1],msg[2],msg[3])
        else:
            dump.dump()

    '''
    An extant problem that I will ignore for now:
    in the composable treatmnet paper the ledger does clock interaction whenever it receives any 
    input from a party. The purpose really is to collect and know how many times each party has been
    activated so that it can be simulated. This should happen for subroutines as well since
    the party is being activated by the environment, but for now just leave it for input tape
    writes only.
    
    To globalize, the ledger must check clock read for the sid sending the input.
    '''

    def input_msg(self, sender, msg):
        sid,pid = None,None
        if sender:
            sid,pid = sender
       
        # only check and read the party input not functionality
        if comm.isparty(sid,pid): self.util_read_clock(sid)

        if msg[0] == 'transfer':
            self.input_transfer(sid, pid, msg[1],msg[2],msg[3],msg[4])
        elif msg[0] == 'contract-create':
            self.input_contract_create(sid, pid, msg[1], msg[2], msg[3], msg[4], msg[5])
        elif msg[0] == 'tick':
            self.input_tick_honest(msg[1])
        elif msg[0] == 'transferf':
            self.input_transfer_f(sid, pid, msg[1], msg[2], msg[3], msg[4])
        else:
            dump.dump()

    def subroutine_msg(self, sender, msg):
        sid,pid = sender
        if msg[0] == 'get-caddress':
            return self.get_caddress(sid, pid, msg[1])
        elif msg[0] == 'compute-caddress':
            return self.compute_address(sid, pid, msg[1], msg[2])
        elif msg[0] == 'get-nonce':
            return self.get_nonce(sid, pid, msg[1])
        elif msg[0] == 'getbalance':
            return self.getbalance(sid, pid, msg[1])
        elif msg[0] == 'read-output':
            return self.read_output(sid, pid, msg[1])
        elif msg[0] == 'block-number':
            return self.block_number(sid, pid)
        elif msg[0] == 'get-contract':
            return self.get_contract(sid, pid, msg[1])
        elif msg[0] == 'get-txs':
            return self.get_txs(sid, pid, msg[1], msg[2], msg[3])
        elif msg[0] == 'contract-ref':
            return self.subroutine_contractref(sid, pid, msg[1])

class Ledger_Functionality2(object):
    def __init__(self, sid, pid, _f2p, _f2a, _f2z, _2f, f2_):
        self.txqueue = defaultdict(list)
        self.newtxs = dict()
        self._balances = defaultdict(int)
        self.contracts = {}
        self.nonces = defaultdict(int)
        self.output = {}
        self.txs = {}
        self.round = 0
        self.sid = sid
        self.pid = pid
        self.DELTA = 1
        self.g2c = None
        self.clock = None
        #self.t_L = 0
        self.f2p = _f2p; self.f2a = _f2a; self.f2z = _f2z
        self._2f = _2f;
        self.f2_ = f2_
        self.t_L = defaultdict(int)

        self.outputs = defaultdict(Queue)
        self.input = Channel()
        self.adversary_out = qqueue()
        self.receipts = defaultdict(dict)

        self.block_txs = defaultdict(list)
        
        self.functions = {
            'transfer': self.input_transfer,
            'contract-create': self.input_contract_create,
            'tick': self.decide_tick,
            'getbalance': self.getbalance,
            'read-output': self.read_output
        }

        self.restricted = defaultdict(bool)

    def __str__(self):
        return '\033[92mG_ledger\033[0m'

    @property
    def windowSize(self):
        return self.round

    @property
    def nu(self):
        return int(self.round / 2)

    def set_clock(self, c2c, clock):
        print('LEDGER SET CLOCK', c2c, clock)
        self.g2c = c2c; self.clock = clock

    def write(self, to, msg):
        #print(u'\033[92m{:>20}\033[0m -----> {}, msg={}'.format('G_ledger', str(to), msg))
        gwrite(u'92m', 'G_ledger', to, msg)

    def leak(self, msg):
        #self.write( comm.adversary, msg )
        self.adversary_out.put((
            (self.sid, self.pid),
            msg
        ))

    def getLeaks(self):
        ret = []
        while not self.adversary_out.empty():
            leak = self.adversary_out.get()
            ret.append(leak)
        print('THESE ARE THE LEAKS', ret)
        self.f2a.write(ret)

    def get_contract(self, sid, pid, addr):
        if addr in self.contracts:
            return inspect.getsource(type(self.contracts[addr])).split(':',1)[1] 
        else:
            return ''

    def get_caddress(self, sid, pid, addr):
        sender = (sid,pid)
        return sha256(str(addr).encode() + str(self.nonces[addr]+1).encode()).hexdigest()[24:]

    def input_get_caddress(self, sender):
        sid,pid = sender
        c = sha256(str(sender).encode() + str(self.nonces[sender]+1).encode()).hexdigest()[24:]
        self.f2p.write( (pid, c) )

    def compute_address(self, sid, pid, addr, nonce):
        sender = (sid,pid)
        return sha256(str(addr).encode() + str(nonce).encode()).hexdigest()[24:]

    def get_nonce(self, sid, pid, addr):
        return self.nonces[addr]

    def txref(self, val, sender):
        return {
                'value': val,
                'sender': sender,
                'blocknumber': self.round,
               }

    def getbalance(self, sid, pid, addr):
        #print('[DEBUG]:', 'writing output for (%s,%s)' % (sid,pid))
        self.outputs[sid,pid].put(self._balances[addr])
        return self._balances[addr]

    def get_txs(self, sid, pid, addr, to, fro):
        if fro > to: print('da fuck'); return []
        output = []
        print('Searching txs, fro={}, to={}, addr={}'.format(fro, to, addr))
        #print('txqueue round={}, queue={}'.format(fro-1, self.txqueue[fro-1]))
        for blockno in range(fro,to+1):
            txqueue = self.txqueue[blockno]
            #print('Get tx round', blockno, 'txs', txqueue)
            #print('txqueue round={}, queue={}, to={}, from={}'.format(blockno,txqueue,to,fro))
            for tx in txqueue:
                if tx[0] == 'transfer':
                    ########
                    to,val,data,fro,nonce = tx[1:]
                    if to == addr or fro == addr:
                        #print('to', to, 'from', fro, 'addr', addr)
                        output.append((to,fro,val,data,nonce))
        #print('Returning transactions:', output)
        return output
    
    def input_get_txs(self, sid, pid, addr, to, fro):
        if fro > to: print('da fuck'); self.f2_.write( ((sid,pid), []) ); return
        output = []
        print('Searching txs, fro={}, to={}, addr={}'.format(fro, to, addr))
        for blockno in range(fro,to+1):
            txqueue = self.txqueue[blockno]
            #print('Get tx round', blockno, 'txs', txqueue)
            #print('txqueue round={}, queue={}, to={}, from={}'.format(blockno,txqueue,to,fro))
            for tx in txqueue:
                if tx[0] == 'transfer':
                    to,val,data,fro,nonce = tx[1:]
                    if to == addr or fro == addr:
                        #print('to', to, 'from', fro, 'addr', addr)
                        output.append((to,fro,val,data,nonce))
        print('Returning transactions:', output)
        if comm.isf(sid,pid):
            self.f2_.write( ((sid,pid), output) )
        elif comm.isparty(sid,pid):
            self.f2p.write( ((sid,pid), output) )
        else:
            raise Exception("Not a functionality or a partu")
        #return output


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
        print('PRINT: sender={}, nonce={}, msg={}'.format(sender, nonce, data))
        self.output[sender,nonce].append(data)

    def Exec(self,to,val,data,fro):
        if data == ():
            return 1
        func,args = data
        _tx = self.txref(val, fro)
        r = getattr(self.contracts[to], func)(*args, _tx)
        if 'return' in _tx:
            print('Contract returned something:', _tx['return'])
        self.receipts[fro, self.nonces[fro]] = _tx
        # TODO: REVERT CHANGES TO CONTRACT STORAGE WHEN FAILED TX
        # THIS MEANS WE NEED STORAGE TO BE OUTSIDE THE CONTRACT/TEMP
        return r

    def read_output(self, sid, pid, indices):
        ret = []
        for sender,nonce in indices:
            try:
                ret.append(self.output[sender,nonce])
            except KeyError: continue
        return ret

    def input_read_output(self, sid, pid, indices):
        ret = []
        for sender,nonce in indices:
            try:
                ret.append(self.output[sender,nonce])
            except KeyError: continue
        if comm.isf(sid,pid):
            self.f2_.write( ((sid,pid), ret) )
        elif comm.isparty(sid,pid):
            self.f2p.write( ((sid,pid), ret) )

    def input_delay_tx(self, fro, nonce, rounds):
        tx = self.newtxs[fro,nonce]
        self.txqueue[self.round + rounds].append( (*tx, nonce) )
        del self.newtxs[fro,nonce]
        #print('** delay tx dump **')
        #dump.dump()
        self.f2a.write( 'DELAY_OK' )

    def input_transfer(self, sid, pid, to, val, data, fro):
        print('TRANSFERRING to', to, 'sid,pid', sid, pid, 'val', val, 'fro', fro)
        assert self._balances[fro] >= val
        self.nonces[fro] += 1
        self.newtxs[fro,self.nonces[fro]] = ('transfer', to, val, data, fro)
        # Leak message to the adversary ONLY if not private
        self.leak( ((fro,self.nonces[fro]),('transfer', to, val, data, fro)) )
        #print('** transfer dump **')
        self.f2p.write( (pid, 'TRANSFER_OK') )
        #dump.dump()

    ''' Functionality chooses how long to delay tx
        Need to consider for other transactions as well where adversary can
        delay tx like 'deposit'.'''
    def input_transfer_f(self, sid, pid, fro, nonce, rounds):
        assert self._balances[fro] >= val
        self.nonces[fro] += 1
        self.newtxs[fro,self.nonces[fro]] = ('transfer', to, val, data, fro)
        self.input_delay_tx(sid,pid,fro,nonce,rounds)

    def input_contract_create(self, sid, pid, addr, val, data, private, fro):
        assert self._balances[fro] >= val
        self.nonces[fro] += 1
        # TODO finalize and test without pseudonyms
        #compute_addr = sha256(fro.encode() + str(self.nonces[fro]).encode()).hexdigest()[24:]
        compute_addr = sha256(str(fro).encode() + str(self.nonces[fro]).encode()).hexdigest()[24:]
        assert compute_addr == addr, 'Given address: %s, computed address %s, nonce: %s' % (addr, compute_addr, self.nonces[fro]+1)
        assert data is not None
        self.newtxs[fro,self.nonces[fro]] = ('contract-create', addr, val, data, fro, private)
        # Leak to adversary only if not private
        self.leak( ((fro,self.nonces[fro]),('contract-create',addr,val,data,fro,private)) )
        #print('** contract create dump **')
        #dump.dump()
        self.f2p.write( (pid, 'CREATE_OK') )

    def exec_tx(self, to, val, data, fro):
        # Need to check again in case of other txs
        assert self._balances[fro] >= val
        self._balances[fro] -= val
        self._balances[to] += val
        self.receipts[fro,self.nonces[fro]] = self.txref(val, fro)
        if to in self.contracts:
            print('\t[G_ledger] EXEC function "{}" in {}'.format(data,to))
            r = self.Exec(to, val, data, fro)
            self.txs[fro,self.nonces[fro]] = r

    def exec_contract_create(self, addr, val, data, fro, private):
        assert self._balances[fro] >= val
        self._balances[fro] -= val
        self._balances[addr] += val
        contract,args = data
        # TODO: just make the contract def the init function
        functions = contract(addr, self.CALL, self.OUT)
        self.contracts[addr] = functions
        print('[CONTRACT CREATE]', 'contract: (%s)' % (addr))
        r = getattr(self.contracts[addr], 'init')(*args, self.txref(val,fro))
        self.restricted[addr] = private

        # unco balance changes if creation failes
        if not r:
            self._balances[fro] += val
            self._balances[addr] -= val

    def subroutine_contractref(self, sid, pid, addr):
        return self.contracts[addr]

    def input_tick_honest(self, sender):
        self.round += 1
        # WHAT DOES DELAY LOOK LIKE IN PYTHON
        self._balances[sender] += 100000
        print('\n\tBLOCK #{}:'.format(self.round-1))
        for tx in self.txqueue[self.round-1]:
            print('\t\t TX:to={}, val={}, data={}, fro={}'.format(str(tx[1]),tx[2],tx[3],str(tx[4])))
            if tx[0] == 'transfer':
                self.exec_tx(tx[1], tx[2], tx[3], tx[4])
            elif tx[0] == 'contract-create':
                self.exec_contract_create(tx[1], tx[2], tx[3], tx[4], tx[5])
        print('\n')
        #print('Next Round from', self.round-1, 'to', self.round, 'txs', self.txqueue[self.round-1])
        #print('** tick honest dump **')
        #dump.dump()
        sid,pid = sender
        self.f2p.write( (pid, 'TICK OK') )
               
    def input_tick_adversary(self, sid, pid, addr, permutation):
        new_txqueue = self.txqueue[self.round+1].copy() 
        for i,x in enumerate(permutation):
            new_txqueue[i] = self.txqueue[self.round+1][x]
        self.txqueue[self.round+1] = new_txqueue
        self.input_tick_honest(sid, pid, addr)
        #print('** adv tick dump **')
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

    def util_read_clock(self, sid):
        t = self.clock.subroutine_msg( (sid,-1), ('clock-read',))
        self.t_L[sid] = t 

    def allowed(self, sender):
        _sid,_pid = sender
        return _sid == self.sid

    def adversary_msg(self, msg):
        #sid,pid = None,None
        #if sender:
        #    sid,pid = sender
        print('DEBUG: ledger adversary msg', msg)
        if msg[0] == 'tick':
            self.input_tick_adversary(msg[1], msg[2])
        elif msg[0] == 'get-leaks':
            self.getLeaks()
        elif msg[0] == 'delay-tx':
            self.input_delay_tx(msg[1],msg[2],msg[3])
        else:
            dump.dump()

    '''
    An extant problem that I will ignore for now:
    in the composable treatmnet paper the ledger does clock interaction whenever it receives any 
    input from a party. The purpose really is to collect and know how many times each party has been
    activated so that it can be simulated. This should happen for subroutines as well since
    the party is being activated by the environment, but for now just leave it for input tape
    writes only.
    
    To globalize, the ledger must check clock read for the sid sending the input.
    '''

    def input_msg(self, sender, msg):
        sid,pid = None,None
        if sender:
            sid,pid = sender
       
        # only check and read the party input not functionality
        #if comm.isparty(sid,pid): 
        #    self.util_read_clock(sid)

        print('[G_LEDGER] INPUT MESSAGE', sender, msg)
        if msg[0] == 'transfer':
            self.input_transfer(sid, pid, msg[1],msg[2],msg[3],msg[4])
        elif msg[0] == 'contract-create':
            self.input_contract_create(sid, pid, msg[1], msg[2], msg[3], msg[4], msg[5])
        elif msg[0] == 'tick':
            self.input_tick_honest(msg[1])
        elif msg[0] == 'transferf':
            self.input_transfer_f(sid, pid, msg[1], msg[2], msg[3], msg[4])
        elif msg[0] == 'get-caddress':
            self.input_get_caddress(msg[1])
        elif msg[0] == 'block-number':
            print('\n\t\t block number request', sid, pid)
            if comm.isparty(sid,pid):
                print('\n\t\t party asked block-number')
                self.f2p.write( (pid, self.round) )
            elif comm.isf(sid,pid):
                print('\n\t\t functionality blocknumber')
                self.f2_.write( ((sid,pid), self.round) )
            else:
                self.f2_.write( 'fail' )
                dump.dump()
        elif msg[0] == 'get-txs':
            return self.input_get_txs(sid, pid, msg[1], msg[2], msg[3])
        elif msg[0] == 'read-output':
            return self.input_read_output(sid, pid, msg[1])
        else:
            dump.dump()

    def subroutine_msg(self, sender, msg):
        sid,pid = sender
        if msg[0] == 'get-caddress':
            return self.get_caddress(sid, pid, msg[1])
        elif msg[0] == 'compute-caddress':
            return self.compute_address(sid, pid, msg[1], msg[2])
        elif msg[0] == 'get-nonce':
            return self.get_nonce(sid, pid, msg[1])
        elif msg[0] == 'getbalance':
            return self.getbalance(sid, pid, msg[1])
        elif msg[0] == 'read-output':
            return self.read_output(sid, pid, msg[1])
        elif msg[0] == 'block-number':
            return self.block_number(sid, pid)
        elif msg[0] == 'get-contract':
            return self.get_contract(sid, pid, msg[1])
        elif msg[0] == 'get-txs':
            return self.get_txs(sid, pid, msg[1], msg[2], msg[3])
        elif msg[0] == 'contract-ref':
            return self.subroutine_contractref(sid, pid, msg[1])


def LedgerITM(sid, pid, a2f, f2f, p2f):
    g_ledger = Ledger_Functionality(sid,pid)
    ledger_itm = ITMFunctionality(sid,pid,a2f,f2f,p2f)
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

