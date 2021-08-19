from uc.itm import UCFunctionality, fork, forever, GenChannel
from uc.utils import read_one, read
import logging

log = logging.getLogger(__name__)

class F_Com(UCFunctionality):
    def __init__(self, k, bits, crupt, sid, pid, channels, pump, poly, importargs):
        self.ssid = sid[0]
        self.committer = (sid, sid[1])
        self.receiver = (sid, sid[2])
        UCFunctionality.__init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs)
        self.bit = None
        self.state = 0 # wait to commit, 1: committed, 2: reveal

    def commit(self, bit):
        self.tick(1)
        self.bit = bit
        self.write('f2p', (self.receiver, 'commit'), 0)
        self.state = 1

    def reveal(self):
        self.tick(1)
        self.write('f2p', (self.receiver, ('open', self.bit)), 0)
        self.state = 2

    def party_msg(self, m):
        print('F_com: party msg:', m.msg)
        sender,msg = m.msg
        if self.state is 0 and sender == self.committer and msg[0] == 'commit':
            _,bit = msg
            self.commit(bit)
        elif self.state is 1 and sender == self.committer and msg[0] == 'reveal':
            self.reveal()
        else:
            self.pump.write('')

