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

    def __deposit(self, _from, _amount):
        self.balances[_from] += _amount

    def __withdraw(self, _from, _amount):
        self.balances[_from] -= _amount

    def __pay(self, _from, _to, _amount):
        self.balances[_from] -= _amount
        self.balances[_to] += _amount

    def __init(self, _from, _amount):
        __deposit(_from, _amount)
        self.write('f2p', 'channel init')

    def __close(self):
        for i in range(self.n):
            __withdraw(i, self.balances[i])
        self.write('f2p', 'channel close')

    def init_channel(self, _from, amount):
        if not self.isOpen:
            delay = 0 # some delay of time
            codeblock = (
                'schedule'
                self.__init,
                (_from, amount),
                delay
            )
            self.write('f2w', codeblock)
            m = wait_for(self.channels['w2f']).msg
            assert m == ('OK',)

            leaked_msg = 'leaked msg (i don know what is the format of leaked message is look like, so a placeholder here)'
            self.leak('f2a', leaked_msg, 0)
            self.isOpen = True

    def close_channel(self, _from):
        if self.isOpen:
            delay = 0 # some delay of time
            codeblock = (
                'schedule'
                self.__close,
                (),
                delay
            )
            self.write('f2w', codeblock)
            m = wait_for(self.channels['w2f']).msg
            assert m == ('OK',)

            leaked_msg = ('close', (_from))
            self.leak('f2a', leaked_msg, 0)
            self.isOpen = False

    def pay(self, _from, _to, amount):
        if self.balances[_from] < amount: return

        delay = 0 # some delay of time
        codeblock = (
            'schedule'
            self.__pay,
            (_from, _to, amount),
            delay
        )
        self.write('f2w', codeblock)
        m = wait_for(self.channels['w2f']).msg
        assert m == ('OK',)

        leaked_msg = ('pay', (_from, _to, amount))
        self.leak('f2a', leaked_msg, 0)

    def read_balance(self, _from):
        amount = self.balances[_from]
        msg = ('read_balance', (_from, amount)) # donna if the format is right
        self.write('f2p', msg)
        # no need to leak to adversary, pointless

    def deposit(self, _from, amount):
        if self.isOpen:
            delay = 0 # some delay of time
            codeblock = (
                'schedule'
                self.__deposit,
                (_from, amount),
                delay
            )
            self.write('f2w', codeblock)
            m = wait_for(self.channels['w2f']).msg
            assert m == ('OK',)

            leaked_msg = 'leaked msg (i don know what is the format of leaked message is look like, so a placeholder here)'
            self.leak('f2a', leaked_msg, 0)

    def withdraw(self, _from, amount):
        if self.isOpen:
            if amount > self.balances[_from]
                return

            delay = 0 # some delay of time
            codeblock = (
                'schedule'
                self.__withdraw,
                (_from, amount),
                delay
            )
            self.write('f2w', codeblock)
            m = wait_for(self.channels['w2f']).msg
            assert m == ('OK',)

            leaked_msg = 'leaked msg (i don know what is the format of leaked message is look like, so a placeholder here)'
            self.leak('f2a', leaked_msg, 0)

    # the handler bound on p2f channel, handling message from parties
    def party_msg(sef, msg):
        log.debug('Party message in payment {}'.format(msg))
        command = msg['msg']
        tokens = msg['imp']
        data = msg['data']
        if command == 'init':
            sender = data['sender']
            amount = data['amount']
            init_channel(sender, amount)
        elif command == 'close':
            sender = data['sender']
            close_channel(sender)
        elif command == 'pay':
            sender = data['sender']
            receiver = data['receiver']
            amount = data['amount']
            pay(sender, receiver, amount)
        elif command == 'read':
            sender = data['sender']
            read_balance(sender)
        elif command == 'deposit':
            sender = data['sender']
            amount = data['amount']
            deposit(sender, amount)
        elif command == 'withdraw':
            sender = data['sender']
            amount = data['amount']
            withdraw(sender, amount)
        else:
            self.pump.write("pump")

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

