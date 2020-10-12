from itm import UCWrappedFunctionality
from utils import wait_for
import logging
log = logging.getLogger(__name__)

class Contract(UCWrappedFunctionality):
    def __init__(self, k, bits, sid, pid, channels, pump, poly, importargs):
        self.ssid = sid[0]
        self.n = sid[1]
        self.delta = sid[2]
        self.settlement = self.delta * 2 # the challenge period
        
        self.deadline = -1
        self.nonce = -1

        self.balances = sid[3]
        self.flag = 'OPEN'
        ## Following is for general case, above is for channel's already open
        # self.balances = [0] * self.n
        # self.flag = 'CLOSED'    # {'CLOSED', 'OPEN', 'CHALLANGE'}
        #                         # 'CLOSED': channel closed
        #                         # 'OPEN': channel open
        #                         # 'CHALLANGE': enter into challenge period
        UCWrappedFunctionality.__init__(self, k, bits, sid, pid, channels, poly, pump, importargs)


    def _check_sig(self, party, sig, state):
        # TODO: check if `party` sign the `state` with signature `sig`
        return True or False

    def _current_time(self):
        # TODO: return current round
        return current_round


    # smart contract logic
    def close_channel(data, imp):
        _from = data['sender']
        _state = data['state']
        _sig = data['sig']

        assert self.flag = 'OPEN'
        for p in range(self.n):
            if p != _from:
                isHonest = self._check_sig(p, _sig[p], _state)

        if isHonest:
            # means also have receiver's signature
            # Q: should the following action be scheduled for a delay?
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
            # Q: should the following action be scheduled for a delay?
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


    # smart contract logic
    def init_channel(self, data, imp):
        _from = data['sender']
        _amt = data['amount']

        # Q: should the following action be scheduled for a delay?
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

    # smart contract logic
    # Q: should the following action be scheduled for a delay?
    def recv_challenge(self, data, imp):
        _from = data['sender']
        _state = data['state']
        _sig = data['sig']

        assert self.flag == 'CHALLANGE'
        assert self._current_time() <= self.deadline # ensure not due
        assert _state['nonce'] >= self.nonce
        for p in range(self.n):
            assert self._check_sig(p, _sig[p], _state)

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

    # offchain synchronous channel
    # used for communication between parties, relaying `msg`
    def offchain_channel(self, _from, _to, msg, imp):
        codeblock = (
            'schedule', 
            self.__send2p,
            (_to, msg, imp),
            1
        )
        self.write('f2w', codeblock, imp)
        m = wait_for(self.channels['w2f']).msg
        assert m == ('OK',)

        leaked_msg = ('send', (_from, _to, _amt))
        self.leak(leaked_msg, 0)

    # onchain synchronous channel
    # used to simulate onchain mining txs
    def wrapper_contract(self, sender, msg, imp):
        if sender > 0: # sender is parties
            codeblock = (
                'schedule',
                self.__send2c,
                (msg, imp),
                self.delta
            )
            self.write('f2w', codeblock, imp)
            m = wait_for(self.channels['w2f']).msg
            assert m == ('OK',)
        elif sender == -1: # sender is contract, and this is broadcast
            for _to in range(self.n):
                codeblock = (
                    'schedule',
                    self.__send2p,
                    (_to, msg, imp),
                    1
                )
                self.write('f2w', codeblock, imp)
                m = wait_for(self.channels['w2f']).msg
                assert m == ('OK',)
        else:
            return
        #Q: do we leak message here? or leak in the actual codeblock execution
        #Q: how do we handle `imp` tokens?

    def __send2p(self, i, msg, imp):
        self.write('f2p', (i, msg), imp)

    def __send2c(self, msg, imp):
        self.write('w2f', (msg), imp)

    # p2f handler
    def party_msg(self, msg):
        log.debug('Contract/Receive msg from P in real world: {}'.format(msg))
        command = msg['msg']
        tokens = msg['imp']
        data = msg['data']
        sender = data['sender']
        if command == 'send': # united interface with synchronous channel
            # normal offchain payment
            receiver = data['receiver']
            self.offchain_channel(sender, receiver, msg, imp)
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
        log.debug('Contract/Receive msg from Wrapper: {}'.format(msg))
        command = msg['msg']
        imp = msg['imp']
        data = msg['data']
        if command == 'challenge':
            # entering into challenge, receive challenge from P_{receiver}
            self.recv_challenge(data, imp)
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
