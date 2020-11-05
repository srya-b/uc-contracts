from itm import UCFunctionality
import logging

log = logging.getLogger(__name__)

class Random_Oracle_and_Chan(UCFunctionality):
    def __init__(self, k, bits, crupt, sid, pid, channels, pump, poly, importargs):
        self.table = {}
        UCFunctionality.__init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs)

    def hash(self, s):
        self.tick(1)
        if s in self.table: return self.table[s]
        else:
            self.table[s] = self.sample(self.k)
            return self.table[s]
            
    def send(self, to, msg, imp):
        self.tick(1)
        self.write('f2p', ((self.sid,to), ('send',msg)), imp)

    def party_msg(self, d):
        sender, msg = d.msg
        imp = d.imp
        if msg[0] == 'ro':
            self.write('f2p', (sender, ('ro', self.hash(msg[1]))))
        elif msg[0] == 'send':
            print('send msg', msg)
            self.send(msg[1], msg[2], msg[3])
        else:
            self.pump.write('')

    def adv_msg(self, d):
        msg = d.msg
        imp = d.imp
        self.write('f2a', (self.hash(msg),))

