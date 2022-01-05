from uc import UCFunctionality
from uc.utils import read_one, read
import logging 

log = logging.getLogger(__name__)

class F_Flip(UCFunctionality):
    def __init__(self, k, bits, crupt, sid, pid, channels, pump):
        self.flipper = sid[1]
        self.receiver = sid[2]
        UCFunctionality.__init__(self, k, bits, crupt, sid, pid, channels, pump)

        self.flip = None

        self.party_msgs['flip'] = self.party_flip
        self.party_msgs['getflip'] = self.party_getflip
        self.party_msgs['sendmsg'] = self.party_sendmsg

    def party_flip(self, sender):
        if sender == self.flipper:
            self.flip = self.sample(1)
            self.write( ch='f2a', msg=('flip',) )
        else: self.pump.write('')

    def party_getflip(self, sender):
        if self.flip is None: self.pump.write('')
        else:
            m = self.write_and_wait_for( ch='f2a', msg=('askflip',sender), read='a2f' )
            if m == ('yes',):
                self.write( ch='f2p', msg=(sender, ('flip', self.flip)) )
            elif m == ('no',):
                self.pump.write('')
            else:
                raise Exception('Unexpected message. Expected ("yes",) or ("no",), got: {}'.format(m))

    def party_sendmsg(self, sender, msg):
        if sender == self.flipper:
            self.write( ch='f2p', msg=(self.receiver, ('recvmsg', msg)) )
        else:
            self.write( ch='f2p', msg=(self.flipper, ('recvmsg', msg)) )
