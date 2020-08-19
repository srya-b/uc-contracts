from itm import ITM
from comm import ishonest, isdishonest

class Sim_Com(ITM):
    def __init__(self, k, bits, sid, pid, channels, pump, poly, importargs):
        self.ssid = sid[0]
        self.committer = sid[1]
        self.receiver = sid[2]
        self.table = {}
        self.revtable = {}

        self.receiver_random = None
        self.receiver_state = 1

        handlers = {
            channels['p2a'] : self.party_msg,
            channels['f2a'] : self.func_msg,
            channels['z2a'] : self.env_msg,
        }

        ITM.__init__(self, k, bits, sid, pid, channels, handlers, poly, pump, importargs)

    def hash(self, s):
        if k not in self.table:
            self.table[s] = self.sample(self.k)
            self.revtable[self.table[s]] = s
        return self.table[s]

    def env_msg(self, m):
        msg = m.msg
        imp = d.imp
        if msg[0] == 'A2F':
            t,msg,iprime = msg
            if msg[0] == 'ro':
                self.write('a2z', ('ro', self.hash(msg[1])))
            else:
                self.pump.write('')
        elif isdishonest(self.sid, self.committer):
            if msg[0] == 'A2P':
                _,to,msg = msg
                assert to == (self.sid, self.committer)
                if msg[0] == 'commit':
                    # env gives some hash value
                    if msg[1] in self.revtable:
                        self.write('a2p', (to, ('commit', self.revtable[msg[1]])))
                    else:
                        b = self.sample(1)
                        self.write('a2p', (to, ('commit', b)))
                else: 
                    self.pump.write('')
        else:
            self.pump.write('')

    def party_msg(self, m):
        msg = m.msg
        imp = m.imp
        fro,msg = msg
        print('adv party message')
        if isdishonest(self.sid, self.receiver) and fro == (self.sid, self.receiver):
            if msg == 'commit' and self.receiver_state == 1:
                self.receiver_random = self.sample(self.k)
                self.write('a2z', (fro, ((self.sid, 'F_ro'),('send', self.receiver_random))))
                self.receiver_state = 2
            elif msg[0] == 'open' and self.receiver_state == 2 :
                bit = msg[1]
                self.write('a2z', (fro, ((self.sid,'F_ro'),('send', (self.sample(self.k), bit)))))
                self.receiver_state = 3
            else:
                self.pump.write('')
        else:
            self.pump.write('')

    def func_msg(self, m):
        self.pump.write('')
