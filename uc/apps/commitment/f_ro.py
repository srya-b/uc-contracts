from uc import UCFunctionality
import logging

log = logging.getLogger(__name__)

class Random_Oracle_and_Chan(UCFunctionality):
    def __init__(self, k, bits, crupt, sid, pid, channels, pump):
        self.table = {}
        UCFunctionality.__init__(self, k, bits, crupt, sid, pid, channels, pump)
        self.party_msgs['hash'] = self.phash
        self.party_msgs['sendmsg'] = self.sendmsg

        self.adv_msgs['hash'] = self.ahash 

    def _hash(self, x):
        if x not in self.table:
            self.table[x] = self.sample(self.k)
        return self.table[x]

    def phash(self, sender, s):
        print('Hash request from: {}'.format(sender))
        self.write(
            ch='f2p',
            msg=(sender, self._hash(s))
        )

    def ahash(self, s):
        self.write(
            ch='f2a',
            msg=self._hash(s)
        )

    def sendmsg(self, sender, to, msg):
        print('Party sendmsg from {} to {}'.format(sender, to))
        self.write(
            ch='f2p',
            msg=(to, ('recvmsg', sender, msg)),
        )


