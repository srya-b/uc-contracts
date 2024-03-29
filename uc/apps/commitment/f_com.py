from ast import literal_eval
from uc import UCFunctionality
from uc.utils import read_one, read
import logging

log = logging.getLogger(__name__)

class F_Com_Channel(UCFunctionality):
    def __init__(self, k, bits, crupt, sid, channels, pump):
        UCFunctionality.__init__(self, k, bits, crupt, sid, channels, pump)
        self.ssid,sid = sid
        sid = literal_eval(sid)
        self.committer = sid[0]
        self.receiver = sid[1]

        self.bit = None
        self.state = 0 # wait to commit, 1: committed, 2: reveal

        self.party_msgs['commit'] = self.commit
        self.party_msgs['reveal'] = self.reveal
        self.party_msgs['sendmsg'] = self.sendmsg

    def commit(self, sender, bit):
        if self.state == 0 and sender == self.committer and (bit == 0 or bit == 1):
            self.bit = bit

            self.write( ch='f2p', msg=(self.receiver, ('commit',)) )

            self.state = 1
        else: self.pump.write('')

    def reveal(self, sender):
        if self.state == 1 and sender == self.committer:
            self.write( ch='f2p', msg=(self.receiver, ('open', self.bit)) )
            self.state = 2
        else: self.pump.write('')

    def sendmsg(self, sender, msg):
        if sender == self.committer:
            self.write( ch='f2p', msg=(self.receiver, ('recvmsg', msg)) )
        else:
            self.write( ch='f2p', msg=(self.committer, ('recvmsg', msg)) )
            
