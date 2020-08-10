import dump
import gevent

from collections import defaultdict

from itm import UCAsyncWrappedFunctionality

from enum import Enum

from utils import MessageTag

from honeybadgermpc.polywrapper import PolyWrapper
from honeybadgermpc.elliptic_curve import Subgroup
from honeybadgermpc.field import GF
        
class OfflinePhaseFunctionality(UCAsyncWrappedFunctionality):
    def __init__(self, sid, pid, channels, pump, poly):
        self.ssid, self.parties = sid # TODO: define sid with party list
        self.n = len(self.parties)
        
        self.poly_wrapper = PolyWrapper(self.n)
        
        self.poly_dict = defaultdict(self.poly_wrapper.random)
        self.triple_poly_dict = defaultdict(self.rand_triple)
        
        self.pump = pump

        UCAsyncWrappedFunctionality.__init__(self, sid, pid, channels, poly)

    def rand_triple(self):
        a = self.poly_wrapper.random()
        b = self.poly_wrapper.random()
        ab = self.poly_wrapper.random_with_secret(self.poly_wrapper.secret(a) * self.poly_wrapper.secret(b))
        return (a,b,ab)
        
    def adv_msg(self, msg):
        self.pump.write("pump") # ignore any adversarial messages

    def party_msg(self, msg):
        imp = msg.imp
        msg = msg.msg
        sender, msg = msg
        sid, pid = sender
        # need to convert pid to [0, n-1]
        if msg[0] == MessageTag.RAND:
            idx = max(list([idx for (dealer, idx) in self.poly_dict.keys() if dealer==sender])+[-1])+1
            #self.write('f2p', (sender, (MessageTag.RAND, self.poly_wrapper.secret(self.poly_dict[idx]), idx)) ) 
            self.write('f2p', (sender, (MessageTag.RAND, self.poly_wrapper.secret(self.poly_dict[(sender, idx)]), idx)) ) 
        if msg[0] == MessageTag.LABEL and isinstance(msg[1], tuple):
            self.write('f2p', (sender, (MessageTag.LABEL, self.poly_wrapper.share(self.poly_dict[msg[1]], pid))) ) 
        if msg[0] == MessageTag.TRIPLE:
            a, b, ab = self.triple_poly_dict[msg[1]]
            points = (self.poly_wrapper.share(a, pid), self.poly_wrapper.share(b, pid), self.poly_wrapper.share(ab, pid))
            self.write('f2p', (sender, (MessageTag.TRIPLE, points)) )

    def env_msg(self, msg):
        self.pump.write("pump") # environment should not attempt to contact functionality

    def wrapper_msg(self, msg):
        self.pump.write("pump") # ignore any activation by wrapper
