from itm import UCWrappedFunctionality
from utils import wait_for
import logging
log = logging.getLogger(__name__)

class Contract(UCWrappedFunctionality):
    def __init__(self, k, bits, sid, pid, channels, pump, poly, importargs):
        self.ssid = sid[0]
        self.round = sid[1]
        self.delta = sid[2]
        UCWrappedFunctionality.__init__(self, k, bits, sid, pid, channels, poly, pump, importargs)

        self.on_chain_channel_id = 0 # not sure if it's the correct format
        self.on_chain_channel_id = 1 # not sure if it's the correct format

        self.settlement = self.delta * 2 # the challenge period
        self.deadline = 0
        self.nonce = 0
        self.balances = [0] * self.n
        self.flag = 'CLOSED'    # {'CLOSED', 'OPEN', 'CHALLANGE'}
                                # 'CLOSED': channel closed
                                # 'OPEN': channel open
                                # 'CHALLANGE': enter into challenge period


    def __send2p(self, i, msg, imp):
        self.write('f2p', (i, msg), imp)

    def _check_sig(self, party, sig, state):
        # check if party sign the state with signature sig
        return True or False

    def recv_challenge(self, data, imp):
        _from = data['sender']
        _state = data['state']
        _sig = data['sig']

        assert self.flag == 'CHALLANGE'
        for p in self.n:
            assert self._check_sig(p, _sig[p], _state)

        assert _state['nonce'] >= self.nonce
        self.nonce = _state['nonce']
        self.balances = _state['balances']
        self.flag = 'CLOSED'

        msg = {
            'msg': 'close_channel',
            'imp': imp,
            'data': data
        }

        for _to in range(self.n):
            codeblock = (
                'schedule',
                self.__send2p,
                (_to, msg, imp),
                self.delta
            )
            self.write('f2w', codeblock, imp)
            m = wait_for(self.channels['w2f']).msg
            assert m == ('OK',)

            leaked_msg = ('pay', (_from, _to, _amt))
            self.leak(leaked_msg, 0)


    def recv_pay(self, data, imp):
        _from = data['sender']
        _to = data['receiver']
        _nonce = data['nonce']
        _amt = data['amount']
        _state = data['state']
        _sig = data['sig']

        msg = {
            'msg': 'pay',
            'imp': imp,
            'data': data
        }

        codeblock = (
            'schedule', 
            self.__send2p,
            (_to, msg, imp),
            1
        )
        self.write('f2w', codeblock, imp)
        m = wait_for(self.channels['w2f']).msg
        assert m == ('OK',)

        leaked_msg = ('pay', (_from, _to, _amt))
        self.leak(leaked_msg, 0)


    # p2f handler
    def party_msg(self, msg):
        log.debug('Contract/Receive msg from P in real world: {}'.format(msg))
        command = msg['msg']
        tokens = msg['imp']
        data = msg['data']
        sender = data['sender']
        if command == 'pay':
            # normal offchain payment
            self.recv_pay(data, imp)
        elif command == 'challenge':
            # entering into challenge, receive challenge from P_{receiver}
            self.recv_challenge(data, imp)
        # === ^ offchain operations === v onchain operations
        elif command == 'read':
            pass
        elif command == 'init':
            pass
        elif command == 'close':
            pass
        # elif command == 'deposit':
        #     pass
        # elif command == 'withdraw':
        #     pass
        else:
            self.pump.write("dump")

    def adv_msg(self, d):
        self.pump.write("dump")

    def env_msg(self, msg):
        self.pump.write("dump")

    def wrapper_msg(self, msg):
        self.pump_write("dump")
