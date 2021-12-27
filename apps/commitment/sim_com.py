from uc.itm import ITM, UCAdversary

#class Sim_Com(ITM):
class Sim_Com(UCAdversary):
    def __init__(self, k, bits, crupt, sid, pid, channels, pump, poly, importargs):
        #self.crupt = crupt
        self.ssid = sid[0]
        self.committer = sid[1]
        self.receiver = sid[2]

        UCAdversary.__init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs)

        self.table = {}
        self.revtable = {}
        self.receiver_random = None
        self.receiver_state = 1

        self.a2f_msgs['hash'] = self.env_hash
        if self.is_dishonest(self.sid, self.receiver):
            self.party_msgs['commit'] = self.recv_commit
            self.party_msgs['open'] = self.recv_open
        elif self.is_dishonest(self.sid, self.committer):
            self.a2p_msgs['send'] = self.commit_send


    def hash(self, s):
        if s not in self.table:
            self.table[s] = self.sample(self.k)
            self.revtable[self.table[s]] = s
        return self.table[s]

    def env_hash(self, s):
        self.write(
            ch='a2z', msg=('F2A', (self.sid,self.hash(s)))
        )

    def commit_send(self, to, msg):
        rec, commitmsg, iprime = msg
        print('commit_send to={}, commitmsg={}'.format(to, commitmsg))
        if to == (self.sid, self.committer):
            b = self.sample(1)
            self.write(
                ch='a2p', msg=(to, ('commit', b))
            )
            self.a2p_msgs['send'] = self.open_send
        else: self.pump.write('')

    def open_send(self, to, msg):
        rec, (nonce, bit), iprime = msg
        if to == (self.sid, self.committer):
            self.write(
                ch='a2p', msg=(to, ('reveal',))
            )
        else: self.pump.write('')

    def recv_commit(self, sender):
        if sender == (self.sid, self.receiver) and self.receiver_state is 1:
            self.receiver_random = self.sample(self.k)
            self.write(
                ch='a2z',
                msg=('P2A', (sender, ('send', ((self.sid, self.committer), self.receiver_random))))
            )
            self.receiver_state = 2
        else: self.pump.write('')


    def recv_open(self, sender, bit):
        if sender == (self.sid, self.receiver) and self.receiver_state is 2:
            self.write(
                ch='a2z',
                msg=('P2A', (sender, ('send', ((self.sid, self.committer), (self.sample(self.k), bit))))),
            )
            self.receiver_state = 3
        else: self.pump.write('')
