from uc import UCAdversary
from ast import literal_eval
from collections import defaultdict
import secp256k1 as secp
import os

class Sim_Mcom(UCAdversary):
    def __init__(self, k, bits, crupt, sid, pid, channels, pump):
        UCAdversary.__init__(self, k, bits, crupt, sid, pid, channels, pump)
        self.ssid = sid[0]
        sid = literal_eval(sid[1])
        self.committer = sid[0]
        self.receiver = sid[1]

        self.state = defaultdict(int)
        self.bit = {}

        self.g,self.h = None,None
        self.receiver_commitment = None

        self.party_msgs['recvmsg'] = self.recvmsg
        self.z2a2p_msgs['value'] = self.value
        if self.is_dishonest(self.receiver):
            self.party_msgs['commit'] = self.recv_commit
            self.party_msgs['open'] = self.recv_open
        elif self.is_dishonest(self.committer):
            self.z2a2p_msgs['sendmsg'] = self.commit_send

    def value(self, to):
        self.sample_g_h()
        self.write('a2z', ('P2A', (to, ((self.g,self.h),))))

    def make_random_point(self):
        return secp.make_random_point(lambda x: self.sample(8*x).to_bytes(x, 'little'))

    def sample_g_h(self):
        if self.g is None:
            self.g = self.make_random_point()
            self.h = self.make_random_point()

    def commit_send(self, to, recv, msg):
        if msg[0] == 'commit':
            _,cid,commitment = msg
            if self.state[cid] == 0:
                self.bit[cid] = secp.uint256_from_str(os.urandom(32))
                self.write( 'a2p', (to, ('commit', cid, self.bit[cid])) )
                self.z2a2p_msgs['sendmsg'] = self.open_send
                self.state[cid] = 1
            else: self.pump.write('')
        else: self.pump.write('')

    def open_send(self, to, recv, msg):
        if msg[0] == 'open':
            _,cid,m,r = msg
            if self.state[cid] == 1:
                self.write( 'a2p', msg=(to, ('reveal',cid)) )
            else: self.pump.write()
        else: self.pump.write('')

    def recvmsg(self, sender, msg):
        if sender == self.committer:
            self.write('a2z', ('P2A', (sender, ('recvmsg', self.receiver, msg))) )
        else:
            self.write('a2z', ('P2A', (sender, ('recvmsg', self.committer, msg))) )

    def recv_commit(self, sender, cid):
        self.sample_g_h()
        self.receiver_commitment = (self.g * secp.uint256_from_str(os.urandom(32))) + (self.h * secp.uint256_from_str(os.urandom(32)))
        self.write('a2z', msg=('P2A', (sender, ('recvmsg', self.committer, ('commit', cid, self.receiver_commitment)))))

    def recv_open(self, sender, cid, m):
        self.receiver_randomness = secp.uint256_from_str(os.urandom(32))
        self.write( 'a2z', ('P2A', (sender, ('recvmsg', self.committer, ('open', cid, m, self.receiver_randomness)))) )
