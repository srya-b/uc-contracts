from uc.protocol import UCProtocol
from uc.itm import GenChannel, wrapwrite, unwrapread
from uc.utils import waits
from uc.adversary import UCAdversary
import logging, gevent

log = logging.getLogger(__name__)

#def compose(p1, p2):
#    def f(k, bits, sid, pid, channels, pump):
#        return Compose(k, bits, sid, pid, channels, pump, p1, p2)
#    return f

def compose(p1, p2):
    class Compose(UCProtocol):
        def __init__(self, k, bits, sid, pid, channels, pump):
            UCProtocol.__init__(self, k, bits, sid, pid, channels, pump)
            self.rho2pi = GenChannel('rho2pi')
            self.pi2rho = GenChannel('pi2rho')
            
            self.channels_for_rho = channels.copy()
            self.channels_for_rho['p2f'] = self.rho2pi
            self.channels_for_rho['f2p'] = self.pi2rho
    
            self.channels_for_pi = channels.copy()
            self.channels_for_pi['z2p'] = self.rho2pi
            self.channels_for_pi['p2z'] = self.pi2rho
    
            self.rho = p1(k, bits, sid, pid, self.channels_for_rho, pump)
            self.pi = p2(k, bits, sid, pid, self.channels_for_pi, pump)
    
            self.env_msgs = self.rho.env_msgs
            self.func_msgs = self.pi.func_msgs 

        def run(self):
            gevent.spawn(self.rho.run)
            gevent.spawn(self.pi.run)

    return Compose



def sim_compose(s1, s2):
    class Comp_Sim(UCAdversary):
        def __init__(self, k, bits, crupt, sid, pid, channels, pump):
            UCAdversary.__init__(self, k, bits, crupt, sid, pid, channels, pump)

            self.sim_pi2rho = GenChannel('simpi2rho')
            self.sim_pi_f2a = GenChannel('simpif2a')
            self.sim_pi_p2a = GenChannel('simpip2a')

            self.sim_pi_a2p = wrapwrite( self.sim_pi2rho, lambda x: ('A2P', x))
            self.sim_pi_a2f = wrapwrite( self.sim_pi2rho, lambda x: ('A2F', x))
            self.sim_rho2pi = unwrapread( [self.sim_pi_p2a, self.sim_pi_f2a], lambda x: self.sim_pi_p2a if x[0] == 'P2A' else self.sim_pi_f2a, lambda x: x[1] )

            self.channels_for_sim_pi = channels.copy()
            self.channels_for_sim_pi['a2f'] = self.sim_pi_a2f
            self.channels_for_sim_pi['f2a'] = self.sim_pi_f2a
            self.channels_for_sim_pi['a2p'] = self.sim_pi_a2p
            self.channels_for_sim_pi['p2a'] = self.sim_pi_p2a

            self.channels_for_sim_rho = channels.copy()
            self.channels_for_sim_rho['z2a'] = self.sim_pi2rho
            self.channels_for_sim_rho['a2z'] = self.sim_rho2pi

            self.sim_pi = s1(k, bits, crupt, sid, pid, self.channels_for_sim_pi, pump)
            self.sim_rho = s2(k, bits, crupt, sid, pid, self.channels_for_sim_rho, pump)

        def run(self):
            gevent.spawn(self.sim_pi.run)
            gevent.spawn(self.sim_rho.run)
    return Comp_Sim



