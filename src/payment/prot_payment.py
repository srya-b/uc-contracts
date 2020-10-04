from itm import UCWrappedProtocol, MSG
from payment import Syn_Channel
from math import ceil, floor
from utils import wait_for, waits
from collections import defaultdict
from numpy.polynomial.polynomial import Polynomial
import logging

log = logging.getLogger(__name__)

class Syn_Payment_Protocol(UCWrappedProtocol):
    #def __init__(self, sid, pid, channels):
    def __init__(self, k, bits, sid, pid, channels, pump, poly, importargs):
        self.ssid = sid[0]
        self.parties = sid[1]
        self.delta = sid[2]
        self.n = len(self.parties)
        self.t = floor(self.n/3)
        UCWrappedProtocol.__init__(self, k, bits, sid, pid, channels, poly, pump, importargs)

        self.id = # TODO: get id from sid or ?
        self.nonce = 0
        self.balances = [0] * self.n
        self.states = {}
        self.isOpen = False
        self.flag = 'NORMAL'    # {'NORMAL', 'CHALLANGE'}
                                # 'NORMAL': all are honest
                                # 'CHALLANGE': enter into challenge period


    def normal_offchain_payment(self, data):
        nonce = data['nonce']
        assert nonce == self.nonce
        self.states[nonce] = data['state']
        self.nonce += 1

        s = data['sender']
        r = data['receiver']
        a = data['amount']
        assert r == self.id
        assert a <= self.balances[s]
        self.balances[r] += a
        self.balances[s] -= a

    def react_challenge(self, data, imp):
        _s = data['state']
        _n = _s[0] # nonce of the state
        _b = _s[1] # balances of the state
        # basically P_recv doesnt need to check anything
        # just send the latest state to challenge is fine

        msg = {
            'msg': 'challenge',
            'imp': imp,
            'data': {
                'sender': self.id,
                'nonce': self.nonce-1,
                'states': self.states[self.nonce-1]
            }
        }
        self.write('p2f', msg)


    def recv_close_channel(self, data):
        self.nonce = 0
        self.balances = [0] * self.n
        self.states = {}
        self.isOpen = False
        self.flag = 'NORMAL'

    def recv_init_channel(self, data):
        s = data['sender']
        a = data['amount']
        self.balances[s] += amount
        self.isOpen = True

    # functionality handler
    # receive msg from the smart contract ideal functionality in the real world
    # b/c it's in a hybrid model
    def func_msg(self, msg):
        log.debug('Protocol/Receive msg from F in real world: {}'.format(msg))
        command = msg['msg']
        tokens = msg['imp']
        data = msg['data']
        if command == 'pay':
            # normal offchain payment
            self.normal_offchain_payment(data)
        elif command == 'challenge':
            # entering into challenge
            self.react_challenge(data, tokens)
        elif command == 'init_channel':
            # get onchain notification of channel initialization
            self.recv_init_channel(data)
        elif command == 'close_channel':
            self.recv_close_channel(data)
        else:
            self.pump.write("dump")

    # wrapper handler
    def wrapper_msg(self, msg):
        self.pump.write("dump")

    # adv handler
    def adv_msg(self, msg):
        self.pump.write("dump")

    def close_channel(self, _from, imp):
        if not self.isOpen: return # if a channel doesnt exitst, then fail

        msg = {
            'msg': 'close',
            'imp': imp,
            'data': {
                'sender': _from
            }
        }
        self.write('p2f', msg)

    def init_channel(self, _from, imp):
        if self.isOpen: return # if a channel is already open, then fail

        msg = {
            'msg': 'init',
            'imp': imp,
            'data': {
                'sender': _from,
                'amount': amount
            }
        }
        self.write('p2f', msg)


    def pay(self, _from, _to, amount, imp):
        if not self.isOpen: return # if there's no channel, cannot pay offchain
        if amount > self.balances[_from]: return # not enough balance

        self.balances[_from] -= amount
        self.balances[_to] += amount
        self.states[self.nonce] = self.balances

        msg = {
            'msg': 'pay',
            'imp': imp,
            'data': {
                'sender': _from,
                'receiver': _to,
                'amount': amount,
                'nonce': self.nonce,
                'state': self.states[self.nonce]
            }
        }
        self.write('p2f', msg)
        self.nonce += 1
        

    # env handler
    def env_msg(self, msg):
        log.debug('Env/Receive message from Z in real world: {}'.format(msg))
        command = msg['msg']
        tokens = msg['imp']
        data = msg['data']
        if command == 'pay':
            # Z tells P_i to pay another P_j
            sender = data['sender']
            receiver = data['receiver']
            amount = data['amount']
            self.pay(sender, receiver, amount, tokens)
        elif command == 'read':
            # Z tells P_i to read its own balance
            self.write('p2z', self.balances[self.id])
        elif command == 'init':
            # Z tells P_i to init a channel
            sender = data['sender']
            amount = data['amount']
            init_channel(sender, amount, tokens)
        elif command == 'close':
            # Z tells P_i to close a channel
            sender = data['sender']
            close_channel(sender, tokens)
        # elif command == 'deposit':
        #     # Z tells P_i to init a channel
        #     pass
        # elif command == 'withdraw':
        #     # Z tells P_i to close a channel
        #     pass
        else:
            self.pump.write("dump")
            return
        self.write('p2z', 'OK')


from itm import ProtocolWrapper, WrappedProtocolWrapper
from adversary import DummyWrappedAdversary
from syn_ours import Syn_FWrapper, Syn_Channel
from execuc import execWrappedUC
from utils import z_get_leaks

def env1(static, z2p, z2f, z2a, z2w, a2z, p2z, f2z, w2z, pump):
    delta = 3
    n = 3
    #sid = ('one', (1,2,3), delta)
    sid = ('one', tuple(range(1,n+1)), delta)
    static.write( ('sid', sid) )

    z2p.write( ((sid,1), ('input', 2)), n*(4*n + 1) )
    #wait_for(p2z)
    waits(pump, p2z)

    def channel_id(fro, to, r):
        s = ('one', (sid,fro), (sid,to), r, delta)
        return (s,'F_chan')

    z2a.write( ('A2W', ('get-leaks',)) )
    msgs = waits(pump, a2z)
    print('\033[91m [Leaks] \033[0m', '\n'.join(str(m) for m in msgs.msg))


if __name__ == '__main__':
    execWrappedUC(env1, [('F_chan',Syn_Channel)], WrappedProtocolWrapper, Syn_FWrapper, Syn_Bracha_Protocol, DummyWrappedAdversary)
