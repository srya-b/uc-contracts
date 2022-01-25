from ast import literal_eval
from uc import UCFunctionality
from uc.utils import read_one, read
from secp256k1 import make_random_point
import logging

log = logging.getLogger(__name__)


class F_CRS(UCFunctionality):
    def __init__(self, k, bits, crupt, sid, channels, pump):
        UCFunctionality.__init__(self, k, bits, crupt, sid, channels, pump)
        self.ssid,sid = sid

        self.output_value = None
        self.bit = None
        self.state = 0 # wait to commit, 1: committed, 2: reveal

        self.party_msgs['value'] = self.value
        self.party_msgs['sendmsg'] = self.sendmsg

    def value(self, sender):
        if self.output_value is None:
            g = make_random_point(lambda x: self.sample(8*x).to_bytes(x,'little') )
            h = make_random_point(lambda x: self.sample(8*x).to_bytes(x,'little') )
            self.output_value = (g,h)
        self.write( 'f2p', (sender, (self.output_value,)) )

    def sendmsg(self, sender, to, msg):
        self.write(
            ch='f2p',
            msg=(to, ('recvmsg', sender, msg)),
        )
