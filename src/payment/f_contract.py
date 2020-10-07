from itm import UCWrappedFunctionality
from utils import wait_for
import logging
log = logging.getLogger(__name__)

class Contract(UCWrappedFunctionality):
    def __init__(self, k, bits, sid, pid, channels, pump, poly, importargs):
        self.ssid = sid[0]
        self.n = sid[1]
        self.delta = sid[2]
        self.settlement = self.delta * sid[3] # the challenge period
        
        self.deadline = -1
        self.nonce = -1
        self.balances = [0] * self.n
        self.flag = 'CLOSED'    # {'CLOSED', 'OPEN', 'CHALLANGE'}
                                # 'CLOSED': channel closed
                                # 'OPEN': channel open
                                # 'CHALLANGE': enter into challenge period
        UCWrappedFunctionality.__init__(self, k, bits, sid, pid, channels, poly, pump, importargs)


    def __send2p(self, i, msg, imp):
        self.write('f2p', (i, msg), imp)

    def _check_sig(self, party, sig, state):
        # TODO: check if `party` sign the `state` with signature `sig`
        return True or False

    def _current_time(self):
        # TODO: return current round
        return current_round


    def close_channel(data, imp):
        _from = data['sender']
        _state = data['state']
        _sig = data['sig']

        assert self.flag = 'OPEN'
        for p in range(self.n):
            if p != _from:
                isHonest = self._check_sig(p, _sig[p], _state)

        if isHonest:
            # means also receiver's signature
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

                leaked_msg = ('close', (_from))
                self.leak(leaked_msg, 0)

        else:
            # means only sender's signature
            self.flag = 'CHALLANGE'
            self.deadline = self.current_round() + self.settlement

            msg = {
                'msg': 'challenge',
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

                leaked_msg = ('challenge', (_from))
                self.leak(leaked_msg, 0)


    def init_channel(self, data, imp):
        _from = data['sender']
        _amt = data['amount']

        self.flag = 'OPEN'

        msg = {
            'msg': 'init_channel',
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

            leaked_msg = ('init', (_from, _amt))
            self.leak(leaked_msg, 0)


    def recv_challenge(self, data, imp):
        _from = data['sender']
        _state = data['state']
        _sig = data['sig']

        assert self.flag == 'CHALLANGE'
        for p in range(self.n):
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

            leaked_msg = ('challenge', (_from, _state, _sig))
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
        elif command == 'init':
            self.init_channel(data, imp)
        elif command == 'close':
            self.close_channel(data, imp)
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
