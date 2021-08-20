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

        self.party_msgs['commit'] = self.commit
        self.party_msgs['reveal'] = self.reveal

    def commit(self, sender, bit):
        if self.state is 0 and sender == self.committer:
            print('commit')
            self.bit = bit
            self.write(
                ch='f2p', 
                msg=(self.receiver, 'commit')
            )
            self.state = 1
        else: self.pump.write('')

    def reveal(self, sender):
        if self.state is 1 and sender == self.committer:
            self.write(
                ch='f2p',
                msg=(self.receiver, ('open', self.bit))
            )
            self.state = 2
        else: self.pump.write('')

