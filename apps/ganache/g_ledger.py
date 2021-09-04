from uc.utils import waits
from uc.itm import GUCWrappedGlobalFunctionality
from web3 import Web3
from web3.types import RPCEndpoint
import requests


class Ganache_Ledger(GUCWrappedGlobalFunctionality):
    def __init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs, _ssids):
        GUCWrappedGlobalFunctionality.__init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs, _ssids)
        self.w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))
        self.block_number = self.w3.eth.block_number
        self.last_block_round = 0

        self.min_interval = sid[1]
        self.max_interval = sid[2]
        self.delta = sid[3]

        # TODO: for now assume pid i = account[i] and so on
        self.party_msgs['transfer'] = self.party_transfer
        self.party_msgs['balance'] = self.party_balance
        self.func_msgs['accounts'] = self.func_accounts
        self.func_msgs['transfer'] = self.func_transfer

        self.adv_msgs['mineblock'] = self.mineblock
        self.ssids = { 'Wrapper': _ssids[1] }

    def on_init(self):
        self.write_and_wait_expect(
            ch='g2ssid', msg=(self.ssids['Wrapper'], ('schedule', 'new_block', (), self.max_interval)),
            read='ssid2g', expect=(self.ssids['Wrapper'], ('OK',))
        )

    def clock_round(self):
        m = self.write_and_wait_for(
            ch='g2ssid', msg=(self.ssids['Wrapper'], ('clock-round',)),
            imp = 0, read='w2p'
        )
        fro, msg = m.msg
        return msg[1]

    def func_accounts(self, imp, sender):
        accounts = self.w3.eth.accounts
        self.write('g2f', (sender, ('accounts', accounts)))

    def party_balance(self, imp, sender):
        self.pump.write('')

    def mineblock(self, imp):
        print('\n mineblock \n')
        r = requests.post('http://localhost:8545', headers={"Content-Type": "application/json"}, data='{"id": 1337, "jsonrpc": "2.0", "method": "evm_mine", "params": [1231006505000]}')
        print('response to mine:', r.text)
        self.pump.write('')

    def new_block(self):
        r = self.clock_round()
        #if abs(self.last_block_round - r) < self.min_interval or abs(self.last_block_round - r) > self.max_interval:
        #    raise Exception("adversary mined violated block time limits. Last block round={}, round submtted={}".format(self.last_block_round, r))

        print('\n\n ** success in calling clock round: {} ** \n\n'.format(r))

  
    def _transfer(self, to, fro, value):
        txhash = self.w3.send_transaction({
            'from': Web3.toChecksumAddress(fro),
            'to': Web3.toChecksumAddress(to),
            'value': value
        })
        return txhash
    
    def func_transfer(self, imp, sender, to, fro, value):
        txhash = _transfer(to, fro, value)
        self.write('g2f', (sender, ('txhash', txhash)))

    def party_transfer(self, imp, sender, to, value):
        sid,pid = sender
        fro = self.w3.accounts[pid-1]
        txhash = _transfer(to, fro, value)
        self.write('g2p', (sender, ('txhash', txhash)))

     
