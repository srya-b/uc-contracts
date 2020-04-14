import dump
import gevent

from enum import Enum

from itm import UCAsyncWrappedFunctionality
from utils import wait_for, MessageTag

class AtomicBroadcastFunctionality(UCAsyncWrappedFunctionality):
    def __init__(self, sid, pid, channels, pump):
        self.ssid, self.parties = sid
        self.pid = pid
        self.BC = []
        self.pump = pump
        UCAsyncWrappedFunctionality.__init__(self, sid, pid, channels)
        
    def adv_msg(self, msg):
        self.pump.write("pump") # ignore any adversarial messages

    def party_msg(self, msg):
        imp = msg.imp
        msg = msg.msg
        dealer, msg = msg
        # need to convert sender to [0, n-1]
        if msg[0] == MessageTag.TX:
            tx = msg[1]
            self.eventually(self.append_tx, [tx, dealer])
        self.write('f2p', (dealer, (MessageTag.OK,)))

    def env_msg(self, msg):
        self.pump.write("pump") # environment should not attempt to contact functionality
        
    def append_tx(self, tx, dealer):
        self.BC.append((tx, dealer))
        pos = len(self.BC)
        for party in self.parties:
            self.eventually(lambda j, pid: self.write('f2p', ((self.sid, pid), ('blockchain', self.BC[:j])) ), [pos, party])
        self.pump.write("pump")