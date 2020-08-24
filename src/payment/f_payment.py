from itm import UCWrappedFunctionality, ITM
from utils import wait_for, waits
from numpy.polynomial.polynomial import Polynomial
from comm import ishonest, isdishonest
import gevent
import logging

log = logging.getLogger(__name__)

class Syn_Payment_Functionality(UCWrappedFunctionality):
    def __init__(self, k, bits, sid, pid, channels, pump, poly, importargs):
        self.ssid = sid[0]
        self.parties = sid[1]
        self.n = len(self.parties)
        self.round_upper_bound = 1
        self.delta = sid[2] * self.round_upper_bound
        self.balances[self.n] # record all parties' balances
        self.isOpen = False # if there's a payment channel open
        UCWrappedFunctionality.__init__(self, k, bits, sid, pid, channels, poly, pump, importargs)

    def init_channel(self, _from, amount):
        if not self.isOpen:
            self.leak('f2a', ('init', (_from, amount)), 0)
            self.balances[_from] += amount
            self.isOpen = True

    def close_channel(self, _from):
        if self.isOpen:
            self.leak('f2a', ('close', (_from)), 0)
            self.write('f2w', ('withdrawAll', _from, self.n, self.balances))
            self.balances = [0] * self.n
            self.isOpen = False

    def pay(self, _from, _to, amount):
        if self.balances[_from] < amount:
            self.write('f2w', ('pay_fail', sender, amount))
            return
        self.balances[_from] -=  amount
        self.balances[_to] += amount
        self.leak('f2a', ('pay', (_from, _to, amount)), 0)

    def read_balance(self, _from):
        amount = self.balances[_from]
        self.write('f2p', ('read_balance', _from, amount))
        self.leak('f2a', ('read_balance', (_from, amount)), 0)

    def wrapper_msg(self, msg):
        self.pump.write("dump")
    def adv_msg(self, msg):
        self.pump.write("dump")
    def env_msg(self, msg):
        self.pump.write("dump")


from itm import WrappedPartyWrapper, PartyWrapper
from adversary import DummyWrappedAdversary
from syn_ours import Syn_FWrapper
from execuc import execWrappedUC
def env1(static, z2p, z2f, z2a, z2w, a2z, p2z, f2z, w2z, pump):
    n = 2
    sid = ('one', (1,2), 3)
    static.write( ('sid', sid) )

    z2p.write( ((sid,1), ('input',1)), n*(4*n + 1) )
    waits(pump, a2z)#wait_for(a2z)

    z2a.write( ('A2W', ('get-leaks',)) )
    m = waits(a2z, pump)#wait_for(a2z)


if __name__=='__main__':
    # execWrappedUC(env1, [('F_bracha',Syn_Bracha_Functionality)], WrappedPartyWrapper, Syn_FWrapper, 'F_bracha', RBC_Simulator)
    pass

