import dump
import gevent

from collections import defaultdict

from itm import UCAsyncWrappedFunctionality

from enum import Enum

from honeybadgermpc.polywrapper import PolyWrapper
from honeybadgermpc.elliptic_curve import Subgroup
from honeybadgermpc.field import GF

class OfflinePhaseFunctionality(UCAsyncWrappedFunctionality):
    def MessageType(Enum):
        RAND = 1
        LABEL = 2
        TRIPLE = 3
    def __init__(self, sid, pid, channels):
        self.ssid, self.parties = sid # TODO: define sid with party list
        self.n = len(self.parties)
        
        self.poly_wrapper = PolyWrapper(self.n)
        
        self.poly_dict = defaultdict(lambda: self.poly_wrapper.random())
        self.triple_poly_dict = defaultdict(lambda: (self.poly_wrapper.random(), self.poly_wrapper.random(), self.poly_wrapper.random()))

        UCAsyncWrappedFunctionality.__init__(self, sid, pid, channels)

    def adv_msg(self, msg):
        pass # ignore any adversarial messages

    def party_msg(self, msg):
        sender, msg = msg
        msg = msg.msg
        imp = msg.imp
        # need to convert sender to [0, n-1]
        if msg[0] == MessageType.RAND:
            self.idx = max(keys(self.poly_dict))+1
            self.write('f2p', (sender, (MessageType.RAND, self.polynomial_dict[self.idx][sender])) ) 
        if msg[0] == MessageType.LABEL and isinstance(msg[1], int):
            self.write('f2p', (sender, (MessageType.LABEL, self.polynomial_dict[msg[1]][sender])) ) 
        if msg[0] == MessageType.TRIPLE:
            a, b, ab = self.polynomial_dict[msg[1]]
            points = (a[sender], b[sender], c[sender])
            self.write('f2p', (sender, (MessageType.TRIPLE, points)) )

    def env_msg(self, msg):
        dump.dump() # environment should not attempt to contact functionality

    def wrapper_msg(self, msg):
        pass # ignore any activation by wrapper
