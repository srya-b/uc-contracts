from itm import UCWrappedFunctionality, ITM
from utils import wait_for, waits
from numpy.polynomial.polynomial import Polynomial
from comm import ishonest, isdishonest
import gevent
import logging

log = logging.getLogger(__name__)

class Syn_Payment_Functionality(UCWrappedFunctionality):
    '''
    Ideal Functionality of Payment Channel (now only uni-directional)
    It includes the ideal functionality of on-chain smart contract open/close payment channel + off-chain synchronous communication of signed payloads.
    '''
    def __init__(self, k, bits, sid, pid, channels, pump, poly, importargs):
        # sid: pass in all needed intialized variables
        self.ssid = sid[0]
        self.n = sid[1] # number of parties, in uni/bi-directional is 2
        self.delta = sid[2] # the basic unit of delay

        self.balances = [0] * self.n # record all parties' balances
        self.flag = 'CLOSED'    # {'OPEN', 'CLOSED'}
                                # 'OPEN': channel is open
                                # 'CLOSED': channel is closed
        
        UCWrappedFunctionality.__init__(self, k, bits, sid, pid, channels, poly, pump, importargs)

    '''
    __func: functions with __ as prefix are actually executed in the wrapper
    func: normal functions are called in this ideal functionality to schedule __func call in the wrapper
    '''
    def __deposit(self, _from, _amount):
        self.balances[_from] += _amount

    def __withdraw(self, _from, _amount):
        if self.balances[_from] < _amount: return
        self.balances[_from] -= _amount

    def __read(self):
        return self.balances

    def __pay(self, _from, _to, _amount):
        if self.balances[_from] < _amount: return
        self.balances[_from] -= _amount
        self.balances[_to] += _amount

    def __init(self, _from, _amount):
        self.flag = 'OPEN'
        self.__deposit(_from, _amount)
        for i in range(self.n):
            msg = (i, 'channel open')
            self.write('f2p', msg)

    def __close(self):
        self.flag = 'CLOSED'
        for i in range(self.n):
            self.__withdraw(i, self.balances[i])
            msg = (i, 'channel closed')
            self.write('f2p', msg)

    def init_channel(self, _from, amount):
        if self.flag == 'CLOSED':
            delay = self.delta # on-chain communication delay
            codeblock = (
                'schedule'
                self.__init,
                (_from, amount),
                delay
            )
            self.write('f2w', codeblock)
            m = wait_for(self.channels['w2f']).msg
            assert m == ('OK',) # supposed to get this immediately, just to check if the message is successfully queued in wrapper

            leaked_msg = 'leaked msg (i don know what is the format of leaked message is look like, so a placeholder here)'
            self.leak(leaked_msg, 0) # leak msg to the adversary because this part simulates the msg being sent to the synchronous channel in the real world

    def close_channel(self, _from):
        if self.flag == 'OPEN':
            delay = self.delta # on-chain communication delay
            codeblock = (
                'schedule'
                self.__close,
                (),
                delay
            )
            self.write('f2w', codeblock)
            m = wait_for(self.channels['w2f']).msg
            assert m == ('OK',)

            leaked_msg = ('close channel', (_from))
            self.leak(leaked_msg, 0)

    def pay(self, _from, _to, amount):
        if self.flag == 'CLOSED': return # if there's no channel, cannot pay offchain

        delay = 1 # delay only 1 round because pay is supposed to be off-chain
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
        self.leak(leaked_msg, 0)

    def read_balance(self, _from):
        if self.flag == 'CLOSED': return # if there's no channel, cannot read balance

        amount = self.balances[_from]
        msg = (_from, 'balance: {}'.format(amount)) # msg format: (which party is gonna receive this message, the actual message)
        self.write('f2p', msg)
        # no need to leak to adversary because there's no communication via synchronous channel when reading balance

    def deposit(self, _from, amount):
        if self.flag == 'OPEN':
            delay = self.delta # on-chain communication delay
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
            self.leak(leaked_msg, 0)

    def withdraw(self, _from, amount):
        if self.flag == 'CLOSED': # can withdraw only after channel is closed
            delay = self.delta # on-chain communication delay
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
            self.leak(leaked_msg, 0)

    # p2f channel handler, handling message from parties
    def party_msg(sef, msg):
        log.debug('Party message in the ideal world {}'.format(msg))
        command = msg['msg']
        tokens = msg['imp'] # TODO: import tokens are skipped for now
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
            log.debug('F_payment/Command not found: {}'.format(command))
            self.pump.write("pump")

    # w2f channel handler, handling message from wrapper
    def wrapper_msg(self, msg):
        self.pump.write("dump")

    # a2f channel handler, handling message from adversary
    def adv_msg(self, msg):
        self.pump.write("dump")

    # e2f channel handler, handling message from environment
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

