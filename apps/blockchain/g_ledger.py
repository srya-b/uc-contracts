from uc.itm import UCWrappedFunctionality, UCGlobalF
from uc.utils import wait_for, waits
from collections import defaultdict
import gevent
import logging
from ecdsa import NIST384p, VerifyingKey

log = logging.getLogger(__name__)


'''
Functionality
* 
'''
# TODO 
class G_Ledger(UCGlobalF):
    def __init__(self, k, bits, crupt, sid, pid, channels, pump, poly, importargs):
        self.ssid = sid[0]
        self.contract = sid[1]
        self.min_interval = sid[2]
        self.max_interval = sid[3]
        self.delta = sid[4]

        UCGlobalF.__init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs)

        self.block_number = 0
        self.last_block_round = 0
        self.balances = defaultdict(lambda:100)
        
        self.mempool = set()
        self.mempool_deadlines = defaultdict(list)
        self.confirmed_txs = defaultdict(set)
        self.blocks = [[]]
        self.adv_tx_list = []
        self.start = True


    def print_mempool(self):
        print('\n Mempool: {}\n'.format(self.mempool))

    def tx_ref(self, sender, val, data):
        f, args = data
        return {
                'val': val, 'func': f, 'args': args,
                'blockno': self.block_number
               }

    def new_tx(self, sender, tx):
        print('tx', sender, tx)
        (to,fro,data,value),signature = tx
        if VerifyingKey.from_string(fro).verify(signature, str((to,fro,data,value)).encode()):
            self.mempool.add( tx ) 
            self.mempool_deadlines[ self.block_number + self.delta ].append( tx )
            self.print_mempool()
        self.write('f2p', (sender,  ('OK',)))

    def party_msg(self, d):
        if self.start:
            print('Start')
            self.write_and_wait_expect(
                ch='f2w', msg=('schedule', 'new_block', (), self.max_interval),
                read='w2f', expect=('OK',)
            )
            self.start = False

        msg = d.msg
        imp = d.imp
        sender,msg = msg
        sid,pid = sender

        if msg[0] == 'send-tx':
            self.new_tx(sender, msg[1])
        elif msg[0] == 'contract-tx':
            self.contract_tx(self, msg)
        else:   
            self.pump.write('')

    def update_chain_state(self, new_block):
        for tx,sig in new_block:
            to,fro,p,d = tx
            self.balances[ to ] += p
            self.balances[ fro ] -=p

            if to == 'contract':
                self.contract.party_msg(self.tx_ref( fro, p, d ))

    def new_block(self):
        r = self.clock_round()

        if abs(self.last_block_round - r) < self.min_interval or abs(self.last_block_round - r) > self.max_interval:
            raise Exception("Adversary violated the block production limits. Last block round={}, round submitted: {}".format(self.last_block_round, r))

        # select adversary list or txs that HAVE to do out
        print('Adversary list', self.adv_tx_list)
        if self.adv_tx_list:
            new_block = set( self.adv_tx_list )
            self.adv_tx_list = []
        else:
            new_block = set( self.mempool_deadlines[ self.block_number + 1 ] )

        print('newblock', new_block)
        self.mempool = self.mempool - new_block
        self.blocks.append( new_block )
        self.update_chain_state( new_block ) 
        self.last_block_round = r
        self.block_number += 1

        self.write_and_wait_expect(
            ch='f2w', msg=('schedule', 'new_block', (), self.max_interval),
            read='w2f', expect=('OK',)
        )

        print('\n new state: {}\n', self.balances)
        self.pump.write('')

    def adv_select_tx(self, txs):
        for tx in txs:
            if tx in self.mempool and tx not in self.adv_tx_list:
                self.adv_tx_list.append(tx)
        self.write('f2a', ('OK',))

    def adv_msg(self, d):
        if self.start:
            self.write_and_wait_expect(
                ch='f2w', msg=('schedule', 'new_block', (), self.max_interval),
                read='w2f', expect=('OK',)
            )
            self.start = False

        msg = d.msg
        imp = d.imp

        if msg[0] == 'select-tx':
            self.adv_select_tx(msg[1])
        else:
            self.pump.write('')

    def wrapper_msg(self, d):
        if self.start:
            self.write_and_wait_expect(
                ch='f2w', msg=('schedule', 'new_block', (), self.max_interval),
                read='w2f', expect=('OK',)
            )
            self.start = False
        msg = d.msg
        imp = d.imp

        if msg[0] == 'exec':
            _, name, args = msg
            f = getattr(self, name)
            f(*args)
        else:
            self.pump.write('')


    def env_msg(self, d):
        if self.start:
            print('trying to start')
            self.write_and_wait_expect(
                ch='w2_', msg=((self.sid, 'Wrapper'), ('schedule', 'new_block', (), self.max_interval)),
                read='_2w', expect=((self.sid, 'Wrapper'), ('OK',))
            )
            self.start = False
        print('finished start') 
        msg = d.msg
        imp = d.imp
        self.pump.write('')
        if msg[0] == 'balances':
            self.write('w2z', ('balances', self.balances))
        else:
            self.pump.write('')
        
