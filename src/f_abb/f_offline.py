import dump
import gevent

from collections import defaultdict

from itm import UCAsyncWrappedFunctionality

from honeybadgermpc.polywrapper import PolyWrapper
from honeybadgermpc.elliptic_curve import Subgroup
from honeybadgermpc.field import GF

class OfflinePhaseFunctionality(UCAsyncWrappedFunctionality):
    def __init__(self, sid, pid, channels):
        self.parties = [] # TODO: define sid with party list
        self.n = len(self.parties)
        
        self.poly_wrapper = PolyWrapper(self.n)
        
        self.poly_dict = defaultdict(lambda: self.poly_wrapper.random())
        self.triple_poly_dict = defaultdict(lambda: (self.poly_wrapper.random(), self.poly_wrapper.random(), self.poly_wrapper.random()))

        UCAsyncWrappedFunctionality.__init__(self, sid, pid, channels)

    def adv_msg(self, msg):
        pass # ignore any adversarial messages

    def party_msg(self, msg):
        sender, msg = msg
        # need to convert sender to [0, n-1]
        if msg[0] == 'rand':
            self.idx = max(keys(self.poly_dict))+1
            self.f2p.write( (sender, ('rand', self.polynomial_dict[self.idx][sender])) ) 
        if msg[0] == 'label' and isinstance(msg[1], int):
            self.f2p.write( (sender, ('rand', self.polynomial_dict[msg[1]][sender])) ) 
        if msg[0] == 'triple':
            a, b, ab = self.polynomial_dict[msg[1]]
            points = (a[sender], b[sender], c[sender])
            self.f2p.write( (sender, ('rand', points)) )

    def env_msg(self, msg):
        dump.dump() # environment should not attempt to contact functionality

    def wrapper_msg(self, msg):
        pass # ignore any activation by wrapper
