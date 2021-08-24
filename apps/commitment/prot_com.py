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

        self.env_msgs['commit'] = self.env_commit
        self.env_msgs['reveal'] = self.env_reveal
        self.func_msgs['send'] = self.receive

        self.bit = None
        self.nonce = None
        self.state = 1
        self.commitment = -1

    def env_commit(self, bit):
        if self.bit is None and self.iscommitter:
            self.nonce = self.sample(self.k)
            self.bit = bit
            m = self.write_and_wait_for(
                ch='p2f', msg=('hash', (self.nonce, self.bit)),
                read='f2p'
            )
            
            self.write(
                ch='p2f', 
                msg=('send', self.receiver, m.msg, 0)
            )
        else: self.pump.write('')


    def env_reveal(self):
        self.write(
            ch='p2f',
            msg=('send', self.receiver, (self.nonce, self.bit), 0)
        )

    def check_commit(self, preimage):
        m = self.write_and_wait_expect(
            ch='p2f', msg=('hash', preimage),
            read='f2p', expect=self.commitment
        )
        nonce,bit = preimage
        self.write(
            ch='p2z',
            msg=('open', bit)
        )
 
    def receive(self, fro, msg):
        if not self.iscommitter and self.state is 1:
            self.write(
                ch='p2z',
                msg=('commit',)
            )
            self.commitment = msg
            self.state = 2
        elif not self.iscommitter and self.state is 2:
            self.check_commit(msg)
        else:
            self.pump.write('')

