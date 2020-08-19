from itm import UCProtocol
from utils import waits, wait_for
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
        self.write('p2f', ((self.sid, 'F_ro'), ('ro', (self.nonce, self.bit))))
        m = wait_for(self.channels['f2p'])
        fro,(_,msg) = m.msg
        self.write('p2f', ((self.sid, 'F_ro'), ('send', self.receiver, msg)))

    def reveal(self):
        self.write('p2f', ((self.sid, 'F_ro'), ('send', self.receiver, (self.nonce, self.bit))))

    def env_msg(self, m):
        if self.bit is None and self.iscommitter and m.msg[0] == 'commit':
            _,bit = m.msg
            self.commit(bit)
        elif self.bit is not None and self.iscommitter and m.msg[0] == 'reveal':
            self.reveal()
        else:
            self.pump.write('')

    def check_commit(self, preimage):
        self.write('p2f', ((self.sid,'F_ro'), ('ro', preimage)))
        m = wait_for(self.channels['f2p'])
        fro,(_,msg) = m.msg
        assert self.commitment == msg
        nonce,bit = preimage
        self.write('p2z', ('open', bit) )

    def func_msg(self, m):
        fro,msg = m.msg
        if not self.iscommitter and msg[0] == 'send' and self.state is 1:
            self.channels['p2z'].write( 'commit' )
            self.commitment = msg[1]
            self.state = 2
        elif not self.iscommitter and msg[0] == 'send' and self.state is 2:
            self.check_commit(msg[1])
        else:
            self.pump.write('')
