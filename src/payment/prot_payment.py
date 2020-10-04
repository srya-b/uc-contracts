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

        self.nonce = 0
        self.balances = [0] * self.n
        self.isOpen = False
        self.flag = 'NORMAL'    # {'NORMAL', 'CHALLANGE'}
                                # 'NORMAL': all are honest
                                # 'CHALLANGE': enter into challenge period


    def _pay_offchain(self):
        pass

    def _pay_onchain(self):
        pass

    def normal_offchain_payment(self):
        pass

    def react_challenge(self):
        pass

    def get_onchain_block(self):
        pass

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
            pass
        elif command == 'challenge':
            # entering into challenge
            pass
        elif command == 'broadcast':
            # get onchain broadcast (like a mining block notification)
            pass
        else:
            self.pump.write("dump")

    # wrapper handler
    def wrapper_msg(self, msg):
        self.pump.write("dump")

    # adv handler
    def adv_msg(self, msg):
        self.pump.write("dump")

    # env handler
    def env_msg(self, msg):
        log.debug('Env/Receive message from Z in real world: {}'.format(msg))
        command = msg['msg']
        tokens = msg['imp']
        data = msg['data']
        if command == 'pay':
            # Z tells P_i to pay another P_j
            pass
        elif command == 'read':
            # Z tells P_i to read its own balance
            pass
        elif command == 'init':
            # Z tells P_i to init a channel
            pass
        elif command == 'close':
            # Z tells P_i to close a channel
            pass
        elif command == 'deposit':
            # Z tells P_i to init a channel
            pass
        elif command == 'withdraw':
            # Z tells P_i to close a channel
            pass
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
