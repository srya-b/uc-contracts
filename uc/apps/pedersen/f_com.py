from ast import literal_eval
from uc import UCFunctionality
from collections import defaultdict

class F_com(UCFunctionality):
    def __init__(self, k, bits, crupt, sid, channels, pump):
        UCFunctionality.__init__(self, k, bits, crupt, sid, channels, pump)
        self.ssid = sid[0]
        sid = literal_eval(sid[1])
        self.committer = sid[0]
        self.receiver = sid[1]

        self.msg = None
        self.state = 0

        self.party_msgs['commit'] = self.commit
        self.party_msgs['reveal'] = self.reveal

    def commit(self, sender, msg):
        if self.state == 0 and sender == self.committer:
            self.msg = msg
            self.write('f2p', (self.receiver, ('commit',)))
            self.state = 1
        else: self.pump.write('')

    def reveal(self, sender):
        if self.state == 1 and sender == self.committer:
            self.write('f2p', (self.receiver, ('open', self.msg)))
            self.state = 2
        else: self.pump.write('')

