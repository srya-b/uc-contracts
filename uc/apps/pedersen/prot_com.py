import os 
from ast import literal_eval
from uc import UCProtocol
from uc.utils import waits, wait_for
from collections import defaultdict
import secp256k1 as secp
import logging

log = logging.getLogger(__name__)

class Commitment_Prot(UCProtocol):
    def __init__(self, k, bits, sid, pid, channels, pump):
        UCProtocol.__init__(self, k, bits, sid, pid, channels, pump) 
        self.ssid,sid = sid
        parties = literal_eval(sid)
        self.committer = parties[0]
        self.receiver = parties[1]
        self.iscommitter = pid == self.committer

        self.env_msgs['commit'] = self.env_commit
        self.env_msgs['reveal'] = self.env_reveal
        self.func_msgs['recvmsg'] = self.func_receive

        #self.msg = None
        self.msg = {}
        #self.randomness = None
        self.randomness = {}
        #self.commitment = None
        self.commitment = {}

        self.first = True
        self.state = defaultdict(int)

    def env_commit(self, cid, to_commit):
        if self.first:
            m = self.write_and_wait_for('p2f', ('value',), 'f2p')[0]
            self.g = m[0]
            self.h = m[1]
            self.first = True

        if self.iscommitter and self.state[cid] == 0:
            self.msg[cid] = to_commit
            self.randomness[cid] = secp.uint256_from_str(os.urandom(32))
            
            self.commitment[cid] = secp.ser((self.g * self.msg[cid]) + (self.h * self.randomness[cid]))
            self.write('p2f', ('sendmsg', self.receiver, ('commit', cid, secp.deser(self.commitment[cid]))))
            self.state[cid] = 1
        else:
            self.pump.write('')

    def env_reveal(self, cid):
        if self.iscommitter and self.state[cid] == 1:
            self.write( 'p2f', ('sendmsg', self.receiver, ('open', cid, self.msg[cid], self.randomness[cid])) )
            self.state[cid] = 2
        else:
            self.pump.write('')

    def check_commit(self, cid, preimage, randomness):
        self.g, self.h = self.write_and_wait_for('p2f', ('value',), 'f2p')[0]
        recv_commit = (self.g * preimage) + (self.h * randomness)
        if secp.deser(self.commitment[cid]) == recv_commit:
            self.write( 'p2z', ('open', cid, preimage) )
        else:
            self.pump.write('')

    def func_receive(self, fro, msg):
        #if not self.iscommitter and self.state == 1 and msg[0] == 'commit':
        if not self.iscommitter and self.state[msg[1]] == 0 and msg[0] == 'commit':
            self.write('p2z', msg=('commit', msg[1]))
            self.commitment[msg[1]] = secp.ser(msg[2])
            self.state[msg[1]] = 1
        elif not self.iscommitter and self.state[msg[1]] == 1 and msg[0] == 'open':
            self.check_commit(msg[1], msg[2], msg[3])
            self.state[msg[1]] = 2
        else:
            self.write( 'p2z', ('recvmsg', msg) )
