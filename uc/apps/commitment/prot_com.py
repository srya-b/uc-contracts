from uc.itm import UCProtocol
from uc.utils import waits, wait_for
import logging

log = logging.getLogger(__name__)

class Commitment_Prot(UCProtocol):
    def __init__(self, k, bits, sid, pid, channels, pump):
        self.ssid = sid[0]
        self.committer = sid[1]
        self.receiver = sid[2]
        self.iscommitter = pid == self.committer
        UCProtocol.__init__(self, k, bits, sid, pid, channels, pump) 

        self.env_msgs['commit'] = self.env_commit
        self.env_msgs['reveal'] = self.env_reveal
        self.env_msgs['sendmsg'] = self.env_sendmsg 
        self.func_msgs['recvmsg'] = self.func_receive

        self.bit = None
        self.nonce = None
        self.state = 1
        self.commitment = -1

    def env_commit(self, bit):
        if self.bit is None and self.iscommitter:
            self.nonce = self.sample(self.k)
            self.bit = bit

            m = self.write_and_wait_for( ch='p2f', msg=('hash', (self.nonce, self.bit)), read='f2p' )
            self.write( ch='p2f', msg=('sendmsg', self.receiver, ('commit', m)) )

        else: self.pump.write('')

    def env_reveal(self):
        self.write( ch='p2f', msg=('sendmsg', self.receiver, ('open', (self.nonce, self.bit))) )

    def env_sendmsg(self, msg):
        if self.iscommitter:
            self.write( ch='p2f', msg=('sendmsg', self.receiver, msg) )
        else:
            self.write( ch='p2f', msg=('sendmsg', self.committer, msg) )

    def check_commit(self, preimage):
        try:
            m = self.write_and_expect_msg( ch='p2f', msg=('hash', preimage), read='f2p', expect=self.commitment )
            nonce,bit = preimage
            self.write( ch='p2z', msg=('open', bit) )
        except AssertionError:
            self.state = 3
            self.pump.write('')
 
    def func_receive(self, fro, msg):
        if not self.iscommitter and self.state == 1 and msg[0] == 'commit':
            self.write( ch='p2z', msg=('commit',) )
            self.commitment = msg[1]
            self.state = 2
        elif not self.iscommitter and self.state == 2 and msg[0] == 'open':
            self.check_commit(msg[1])
        else:
            self.write( ch='p2z', msg=('recvmsg', msg) )

