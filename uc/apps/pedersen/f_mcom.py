from ast import literal_eval
from uc import UCFunctionality
from collections import defaultdict

class F_Mcom(UCFunctionality):
    def __init__(self, k, bits, crupt, sid, channels, pump):
        UCFunctionality.__init__(self, k, bits, crupt, sid, channels, pump)
        self.ssid = sid[0]
        sid = literal_eval(sid[1])
        self.committer = sid[0]
        self.receiver = sid[1]

        self.msg = {}
        self.state = defaultdict(int)
        
        self.party_msgs['commit'] = self.commit
        self.party_msgs['reveal'] = self.reveal

    def commit(self, sender, cid, msg):
        if self.state[cid] == 0 and sender == self.committer:
            self.msg[cid] = msg
            self.write('f2p', (self.receiver, ('commit', cid)))
            self.state[cid] = 1
        else: self.pump.write('')

    def reveal(self, sender, cid):
        if self.state[cid] == 1 and sender == self.committer:
            self.write('f2p', (self.receiver, ('open', cid, self.msg[cid])))
            self.state[cid] = 2
        else: self.pump.write('')

