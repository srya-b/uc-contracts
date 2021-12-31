from uc.itm import UCFunctionality
from uc.utils import read_one, read
import logging 

log = logging.getLogger(__name__)

class F_Flip(UCFunctionality):
    def __init__(self, k, bits, crupt, sid, pid, channels, pump):
        self.flipper = (sid, sid[1])
        self.receiver = (sid, sid[2])
        UCFunctionality.__init__(self, k, bits, crupt, sid, pid, channels, pump)

        self.flip = None

        self.party_msg['flip'] = self.flip
        self.party_msg['getflip'] = self.getflip
    
    def flip(self, sender):
        if sender == self.flipper:
            self.flip = self.sample(1)
            self.write(
                ch='a2f',
                msg=('flip',)
            )
        else: self.pump.write('')

    def getflip(self, sender):
        m = self.write_and_wait_for(
            ch='a2f', msg=('askflip',sender).
            read='f2a'
        )

        if m == ('yes',):
            self.write(
                ch='f2p',
                msg=(sender, ('flip', self.flip))
            )
        elif m == ('no',):
            self.pump.write('')
        else:
            raise Exception('Unexpected message. Expected ("yes",) or ("no",), got: {}'.format(m))

