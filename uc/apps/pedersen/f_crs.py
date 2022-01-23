from ast import literal_eval
from uc import UCFunctionality
from uc.utils import read_one, read
import logging

log = logging.getLogger(__name__)


class F_CRS(UCFunctionality):
    def __init__(self, k, bits, crupt, sid, channels, pump):
        UCFunctionality.__init__(self, k, bits, crupt, sid, channels, pump)
        self.ssid,sid = sid
        self.output_value = sid[1]

        self.bit = None
        self.state = 0 # wait to commit, 1: committed, 2: reveal

        self.party_msgs['value'] = self.value
        self.party_msgs['sendmsg'] = self.sendmsg


    def value(self, sender):
        self.write('f2p', (sender, (self.output_value,)))

    def sendmsg(self, sender, to, msg):
        self.write(
            ch='f2p',
            msg=(to, ('recvmsg', sender, msg)),
        )
