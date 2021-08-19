from uc.itm import UCProtocol
from uc.utils import waits, wait_for
import logging

log = logging.getLogger(__name__)

class Commitment_Prot(UCProtocol):
    def __init__(self, k, bits, sid, pid, channels, poly, pump, importargs):
        self.ssid = sid[0]
        self.committer = sid[1]
        self.receiver = sid[2]
        self.iscommitter = pid == self.committer
        UCProtocol.__init__(self, k, bits, sid, pid, channels, poly, pump, importargs) 

        self.bit = None
        self.nonce = None
        self.state = 1

        self.commitment = -1

    def commit(self, bit):
        self.nonce = self.sample(self.k)
        self.bit = bit
        #self.write('p2f', ('ro', (self.nonce, self.bit)), 2)
        self.write('p2f', ('hash', (self.nonce, self.bit)), 2)

        m = wait_for(self.channels['f2p'])
        print('\nsending\n')
        
        self.write('p2f', ('send', self.receiver, m.msg, 1), 1)

    def reveal(self):
        self.write('p2f', ('send', self.receiver, (self.nonce, self.bit), 0), 1)

    def env_msg(self, m):
        if self.bit is None and self.iscommitter and m.msg[0] == 'commit':
            _,bit = m.msg
            self.commit(bit)
        elif self.bit is not None and self.iscommitter and m.msg[0] == 'reveal':
            self.reveal()
        else:
            self.pump.write('')

    def check_commit(self, preimage):
        print('writing to ro', (self.sid,self.pid))
        #self.write('p2f', ('ro', preimage), 1)
        self.write('p2f', ('hash', preimage), 1)
        m = wait_for(self.channels['f2p'])
        assert self.commitment == m.msg
        nonce,bit = preimage
        self.write('p2z', ('open', bit), 0)

    def func_msg(self, m):
        if not self.iscommitter and m.msg[0] == 'send' and self.state is 1:
            self.channels['p2z'].write( 'commit', 0 )
            self.commitment = m.msg[1]
            self.state = 2
        elif not self.iscommitter and m.msg[0] == 'send' and self.state is 2:
            print('\n***checking commit**\n')
            self.check_commit(m.msg[1])
        else:
            self.pump.write('')
