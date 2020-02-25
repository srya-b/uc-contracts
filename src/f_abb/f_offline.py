import dump
import gevent
from collections import defaultdict

from itm import UCFunctionality

from honeybadgermpc.field import GF
from honeybadgermpc.elliptic_curve import Subgroup
from honeybadgermpc.polynomial import polynomials_over

class OfflinePhaseFunctionality(UCFunctionality):
    def __init__(self, sid, pid, channel_wrapper):
        self.degree = 0 # sid needs to contain t
        self.field = GF(Subgroup.BLS12_381)
        self.Poly = polynomials_over(self.field)

        self.polynomial_dict = defaultdict(lambda: self.Poly.random(degree=self.degree))

        UCFunctionality.__init__(self, sid, pid, channel_wrapper)

    def adv_msg(self, msg):
        pass

    def party_msg(self, msg):
        pass

    def env_msg(self, msg):
        pass

    def wrapper_return(self, msg):
        pass
