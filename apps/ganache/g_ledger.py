from uc.utils import waits
from uc.itm import GUCWrappedGlobalFunctionality
from web3 import Web3
from web3.types import RPCEndpoint
from collections import defaultdict
import requests


class Ganache_Ledger(GUCWrappedGlobalFunctionality):
    def __init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs, _ssids):
        GUCWrappedGlobalFunctionality.__init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs, _ssids)
        self.w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))
        self.last_block_round = 1

        self.min_interval = sid[1]
        self.max_interval = sid[2]
        self.delta = sid[3]

        # TODO: for now assume pid i = account[i] and so on
        self.party_msgs['transfer'] = self.party_transfer
        self.party_msgs['balance'] = self.party_balance
        self.func_msgs['accounts'] = self.func_accounts
        self.func_msgs['transfer'] = self.func_transfer

        #self.adv_msgs['mineblock'] = self.mineblock
        self.ssid2g_msgs['exec'] = self.wrapper_exec
        self.ssids = { 'Wrapper': _ssids[1] }

        self.mempool = set()
        self.mempool_deadlines = defaultdict(list)
        self.adv_tx_list = []

    def block_number(self):
        n = self.w3.eth.block_number
        return n

    def on_init(self):
        self.write_and_wait_expect(
            ch='g2ssid', msg=(self.ssids['Wrapper'], ('schedule', 'new_block', (), self.max_interval)),
            read='ssid2g', expect=(self.ssids['Wrapper'], ('OK',))
        )

    def clock_round(self):
        m = self.write_and_wait_for(
            ch='g2ssid', msg=(self.ssids['Wrapper'], ('clock-round',)),
            imp = 0, read='ssid2g'
        )
        fro, msg = m.msg
        return msg[1]

    def func_accounts(self, imp, sender):
        accounts = self.w3.eth.accounts
        self.write('g2f', (sender, ('accounts', accounts)))

    def party_balance(self, imp, sender):
        self.pump.write('')


    def wrapper_exec(self, imp, sender, name, args):
        assert sender == self.ssids['Wrapper']
        f = getattr(self, name)
        f(*args)

    def mine_block(self):
        print('\n mineblock \n')
        r = requests.post('http://localhost:8545', headers={"Content-Type": "application/json"}, data='{"id": 1337, "jsonrpc": "2.0", "method": "evm_mine", "params": [1231006505000]}')
        print('response to mine:', r.text)

    def new_block(self):
        r = self.clock_round()
        if abs(self.last_block_round - r) < self.min_interval or abs(self.last_block_round - r) > self.max_interval:
            raise Exception("adversary mined violated block time limits. Last block round={}, round submtted={}, max_interval={}, min_interval={}".format(self.last_block_round, r, self.max_interval, self.min_interval))

        if self.adv_tx_list:
            new_block = set(self.adv_tx_list)
            self.adv_tx_list = []
        else:
            new_block = set( self.mempool_deadlines[ self.block_number() + 1 ] )

        self.mempool = self.mempool - new_block
        for tx in new_block:
            self.w3.sendTransaction( tx )

        self.mine_block()

        self.write_and_wait_expect(
            ch='g2ssid', msg=(self.ssids['Wrapper'], ('schedule', 'new_block', (), self.max_interval)),
            read='ssid2g', expect=(self.ssids['Wrapper'], ('OK',))
        )

        self.pump.write('')
  
    def _transfer(self, to, fro, value):
        #tx = self.w3.signTransaction(dict(
        #    nonce=self.w3.get_transaction_count(fro),
        #    to=to,
        #    value=value,
        #))
        tx = {'from': fro, 'to': to, 'value': value}
        self.mepool.add( tx )
        self.mempool_deadlines[ self.block_number() + self.delta ].append(tx) 
    
    def func_transfer(self, imp, sender, to, fro, value):
        _transfer(to, fro, value)
        #self.write('g2f', (sender, ('txhash', txhash)))
        self.write('g2f', (sender, ('OK',)))

    def party_transfer(self, imp, sender, to, value):
        sid,pid = sender
        fro = self.w3.accounts[pid-1]
        _transfer(to, fro, value)
        #self.write('g2p', (sender, ('txhash', txhash)))
        self.write('g2p', (sender, ('OK',)))

     
