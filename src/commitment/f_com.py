from itm import UCFunctionality
from comm import ishonest, isdishonest
import logging

log = logging.getLogger(__name__)

class F_Com(UCFunctionality):
    def __init__(self, k, bits, sid, pid, channels, pump, poly, importargs):
        print('pump', pump, 'poly', poly, 'importargs', importargs)
        self.ssid = sid[0]
        self.committer = (sid, sid[1])
        self.receiver = (sid, sid[2])
        UCFunctionality.__init__(self, k, bits, sid, pid, channels, poly, pump, importargs)
        self.bit = None
        self.state = 0 # wait to commit, 1: committed, 2: reveal

    def commit(self, bit):
        self.bit = bit
        self.write('f2p', (self.receiver, 'commit'))
        self.state = 1

    def reveal(self):
        self.write('f2p', (self.receiver, ('open', self.bit)))
        self.state = 2

    def party_msg(self, m):
        sender,msg = m.msg
        #print('party msg:', msg[0])
        #print('state', self.state is 0)
        #print('sender', sender is self.committer)
        #print('committer', self.committer)
        if self.state is 0 and sender == self.committer and msg[0] == 'commit':
            print('commit')
            _,bit = msg
            self.commit(bit)
        elif self.state is 1 and sender == self.committer and msg[0] == 'reveal':
            self.reveal()
        else:
            self.pump.write('')

