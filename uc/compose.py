from uc.protocol import UCProtocol
from uc.itm import GenChannel, wrapwrite, unwrapread
from uc.utils import waits
from uc.adversary import UCAdversary
import logging, gevent

log = logging.getLogger(__name__)

def compose(p1, p2):
    """ The composition operator that creates a new protocol by composing the protocols
    `p1` and `p2`. The composition works like this:

        Assumption:        pi
                    F_1 -------> F_2
        
            and
                          rho
                    F_2 -------> F_3

            then compose replaces F_2 with (pi, F_1):

                         compose(rho, pi)
                    F_1 ------------------> F_3

        Resulting in:

               +-----+  (p2f)   +----+  (p2f)  +-----+
        Z ---> | rho | -------> | pi | ------> | F_1 |
               |     | <------- |    | <------ |     |
               +-----+  (p2z)   +----+  (f2p)  +-----+

    Returns:
        Compose (UCProtocol): the composed protocol code that the party wrapper
            will spawn instances of.
    """
    class Compose(UCProtocol):
        """ A UC protocol that runs the two composed protocols and connects them
        together. The protocol `rho` sends output on its `p2f` channel which is given
        to the corresponding party of `pi` as input on its `z2p` channel. The `p2f`
        output from `pi` is what is sent to the functionality.
        
        Attributes:
            rho2pi (GenChannel): the p2f channel for `rho` and the z2p channel for `pi`
            pi2rho (GenChannel): the p2z channel for `pi` and the f2p channel for `rho`
            channels_for_rho (dict from str to GenChannel): the set of channels for `rho` 
                that includes the "fake" p2f channel that actually goes to `pi` and vice
                versa.
            channels_for_pi (dict from str to GenChannel): the set of channels for `pi`.
            rho (UCProtocol): the main protocol
            pi (UCProtocol): the protocol that replaces F_2 in the diagram above.
            env_msgs (dict from str to func): environment messages are handled by `rho`
            func_msgs (dict from str to func): functionality messages are handled by `pi`
        """
        def __init__(self, k, bits, sid, pid, channels, pump):
            """ 
            Args: 
                The standard set of args for all UCProtocols.
            """
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
            """ Instead of the usual `run` function which reads messages
            and hands them off, run the two protocols which will handle incoming
            messages, instead.
            """
            gevent.spawn(self.rho.run)
            gevent.spawn(self.pi.run)

    return Compose



def sim_compose(s1, s2):
    """ The complement of `compose` which composes the simulators for UC emulation in the assumptions:
                          pi
             S_pi : F_1 ------> F_2

                         rho
            S_rho : F_2 ------> F_3


                     +------+   a2p/a2f   +-------+  a2p/a2f 
            Z -----> | S_pi |  ---------> | S_rho | --------->  (dummy parties, F_3)
                     |      |  <--------- |       | <---------  
                     +------+     a2z     +-------+  p2a/f2a
    Returns:
        Comp_sim (UCAdversary): the simulator for the UC experiment of the composed protocol
    """

    class Comp_Sim(UCAdversary):
        """ The simulator for the composed protocol compose(rho, pi) to emulate F_3.

        Attributes:
            sim_pi2rho (GenChannel): the `z2a` channel for sim_rho
            sim_pi_f2a (GenChannel): the `f2a` channel for sim_pi written to by sim_rho's `a2z` channel 
                messages tagged with "F2A"
            sim_pi_p2a (GenChannel): the `p2a` channel for sim_pi written to by sim_rho's `a2z` channel
                messages tagged with "P2A" 
            sim_pi_a2p (GenChannel): the `a2p` channel for sim_pi that feeds into sim_rho's `z2a` channel with 
                "P2A" tag added with `wrapwrite()`
            sim_pi_a2f (GenChannel): the `a2f` channel for sim_pi that feeds into sim_thos' `z2z` channel with
                "F2A" tag added with `wrapwrite()`
            sim_rho2pi (GenChannel): sim_rho's `a2z` channel that feeds into either sim_pi_p2a or sim_pi_f2a 
                depenging on the tag "F2A" or "P2A"
            channels_for_sim_pi (dict from str to GenChannel): the channels for sim_pi
            channels_for_sim_rho (dict from str to GenChannel): the channels for sim_rho
            sim_pi (UCAdversary): the simulator for the replaced protocol
            sim_rho (UCAdversary): the simulator for the main protocol `rho`
        """

        def __init__(self, k, bits, crupt, sid, pid, channels, pump):
            """ The standar constructor parameters for UCAdversaries. """
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
            """ Run the two simulators """
            gevent.spawn(self.sim_pi.run)
            gevent.spawn(self.sim_rho.run)

    return Comp_Sim



