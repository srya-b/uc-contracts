from itm import UCFunctionality
from comm import ishonest, isdishonest
import logging

log = logging.getLogger(__name__)

class Random_Oracle_and_Chan(UCFunctionality):
    def __init__(self, k, bits, sid, pid, channels, pump, poly, importargs):
        self.table = {}
        UCFunctionality.__init__(self, k, bits, sid, pid, channels, pump, poly, importargs)

    def hash(self, s):
        if s in self.table: return self.table[s]
        else:
            self.table[s] = self.sample(self.k)
            return self.table[s]
            
    def send(self, to, msg):
        self.write('f2p', ((self.sid,to), ('send',msg)))

    def party_msg(self, d):
        sender, msg = d.msg
        imp = d.imp
        if msg[0] == 'ro':
            self.write('f2p', (sender, ('ro', self.hash(msg[1]))))
        elif msg[0] == 'send':
            self.send(msg[1], msg[2])
        else:
            self.pump.write('')

    def adv_msg(self, d):
        msg = d.msg
        imp = d.imp
        self.write('f2a', (self.hash(msg),))

