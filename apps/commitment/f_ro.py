from uc.itm import UCFunctionality
import logging

log = logging.getLogger(__name__)

class Random_Oracle_and_Chan(UCFunctionality):
    def __init__(self, k, bits, crupt, sid, pid, channels, pump, poly, importargs):
        self.table = {}
        UCFunctionality.__init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs)
        self.party_msgs['hash'] = self.phash
        self.party_msgs['send'] = self.send

        self.adv_msgs['hash'] = self.ahash 

    def _hash(self, x):
        if x not in self.table:
            self.table[x] = self.sample(self.k)
        return self.table[x]

    def phash(self, imp, sender, s):
        self.write(
            ch='f2p',
            msg=(sender, self._hash(s))
        )

    def ahash(self, s):
        self.write(
            ch='f2a',
            msg=self._hash(s)
        )

    def send(self, imp, sender, to, msg, imp_to_send):
        self.write(
            ch='f2p',
            msg=((self.sid,to), ('send', sender, msg)),
            imp=imp_to_send
        )


