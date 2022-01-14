from uc import UCAdversary
from ast import literal_eval

class Sim_Com(UCAdversary):
    def __init__(self, k, bits, crupt, sid, pid, channels, pump):
        self.ssid,rest = sid
        rest = literal_eval(rest)
        self.committer = rest[0]
        self.receiver = rest[1]

        UCAdversary.__init__(self, k, bits, crupt, sid, pid, channels, pump)

        self.table = {}
        self.revtable = {}
        self.receiver_random = None
        self.receiver_state = 1
        self.committed_bit = None
        self.dont_open = False

        self.z2a2f_msgs['hash'] = self.env_hash
        self.party_msgs['recvmsg'] = self.recvmsg
        if self.is_dishonest(self.receiver):
            self.party_msgs['commit'] = self.recv_commit
            self.party_msgs['open'] = self.recv_open
        elif self.is_dishonest(self.committer):
            self.z2a2p_msgs['sendmsg'] = self.commit_send

    def set_entry(self, key, value):
        self.table[key] = value
        self.revtable[value] = key
    
    def hash(self, s):
        """Compute the deterministic hash of input `s`.

        Args:
            s: the pre-image to generate hash of
        
        Returns: hash of `s`
        """
        if s not in self.table:
            self.set_entry(s, self.sample(self.k))
        return self.table[s]

    def env_hash(self, s):
        """React to Z hash request.
        Sim acts as F_ro and sends Z the hash for its query
        
        Msg:
            From Z: ('A2F', ('hash', s))

        Args:
            s: the preimage
        """
        self.write( ch='a2z', msg=('F2A', self.hash(s)) )

    def commit_send(self, to, recv, msg):
        """Check wait for sendmsgs from Z until you see the commit message (msg[0] == 'commit').
        If it's a commitment wasn't seen before in F_ro then use some random bit and don't
        open the commitment for the receiver. Otherwise, set handler of `sendmsg` to 
        open_send().

        Msg:
            From Z: ('A2P, (to, ('sendmsg', recv, msg)) 

        Args:
            to: which crutp party Z wants A to send to
            recv: which party is the receiver of this message
            msg: the message for `to` to send to `recv`
        """
        b = self.sample(1)
        if msg[0] == 'commit' and to == self.committer and recv == self.receiver:
            if msg[1] in self.revtable:
                try:
                    n,b = self.revtable[msg[1]]
                except:
                    self.dont_open = True
            else: self.dont_open = True
            self.write( ch='a2p', msg=(to, ('commit', b)) )
            self.committed_bit = b
            self.z2a2p_msgs['sendmsg'] = self.open_send
        else: 
            self.write( ch='a2p', msg=(to, ('sendmsg', msg)) )

    def open_send(self, to, recv, msg):
        """Receive sendmsgs until an Open happens (if msg[0] == 'reveal'. If the Open is bad make
        sure to not open the commitment in the ideal world at any more requests.

        Msg:
            From Z: ('A2P', to, ('sendmsg', recv, msg)

        Args:
            to: which crupt party Z wants A to give input to
            recv: the party receiving this message from `to`
            msg: the message
        """
        #if msg[0] == 'open' and to == (self.sid, self.committer) and not self.dont_open:
        if msg[0] == 'open' and to == self.committer and not self.dont_open:
            try: 
                rec, (nonce, bit) = msg
                assert bit == self.committed_bit
                self.write( ch='a2p', msg=(to, ('reveal',)) )
            except: 
                self.dont_open = True
                self.pump.write('')
        else:
            self.write( ch='a2p', msg=(to, ('sendmsg', msg)) )

    def recvmsg(self, sender, msg):
        """Receive message from party from F_com.
        Nothing to do but forward the message to the environment.

        Msg:
            From P: ('recvmsg', msg)

        Args:
            sender: the party sending the message
            msg: the message received
        """
        if sender == self.committer:
            self.write( ch='a2z', msg=('P2A', (sender, ('recvmsg', self.receiver, msg))) )
        else:
            self.write( ch='a2z', msg=('P2A', (sender, ('recvmsg', self.committer, msg))) )

    def recv_commit(self, sender):
        """RECEIVER CRUPT: wait for the receiver to get a commit from F_com.
        Simulate a commit message with some random commitment for Z.

        Msg:
            From P: ('commit',)

        Args:
            sender: the party sending this message to A
        """
        self.receiver_random = self.sample(self.k)
        self.write( ch='a2z', msg=('P2A', (sender, ('recvmsg', (self.committer, ('commit', self.receiver_random))))) )


    def recv_open(self, sender, bit):
        """RECEIVER CRUPT: when open is received from F_com,
        Store the entry (nonce, bit) = fake randdomness, and send open message
        to Z.

        Msg:
            From P: ('open', it)

        Arg:
            sender: sender of the message
            bit: bit committer committed to
        """
        nonce = self.sample(self.k)
        self.set_entry((nonce,bit), self.receiver_random)
        self.write( ch='a2z', msg=('P2A', (sender, ('recvmsg', (self.committer, ('open', (nonce, bit)))))) )
