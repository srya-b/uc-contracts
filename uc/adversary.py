import gevent
from uc.itm import ITM
from gevent.queue import Queue, Channel, Empty
from gevent.event import AsyncResult
from collections import defaultdict

class UCAdversary(ITM):
    def __init__(self, k, bits, crupt, sid, pid, channels, pump):
        self.crupt = crupt
        self.handlers = {
            channels['p2a'] : self.party_msg,
            channels['f2a'] : self.func_msg,
            channels['z2a'] : self.env_msg
        }
        ITM.__init__(self, k, bits, sid, pid, channels, self.handlers, pump)
        self.env_msgs = {}
        self.func_msgs = {}
        self.party_msgs = {}
        
        self.z2a2f_msgs = {}
        self.z2a2p_msgs = {}

        self.f = lambda x: x[0]
        self.fparse = lambda x: x[1:]

    def is_dishonest(self, pid):
        return pid in self.crupt

    def party_msg(self, d):
        sender, msg = d
        if msg[0] in self.party_msgs:
            self.party_msgs[msg[0]](sender, *msg[1:])
        else:
            self.pump.write('')

    def func_msg(self, msg):
        if self.f(msg) in self.func_msgs:
            self.func_msgs[self.f(msg)](*self.fparse(msg))
        else:
            self.pump.write('')

    def env_msg(self, m):
        t,msg = m
        if t == 'A2F' and msg[0] in self.z2a2f_msgs:
            self.z2a2f_msgs[msg[0]](*msg[1:])
        elif t == 'A2P' and msg[1][0] in self.z2a2p_msgs:
            self.z2a2p_msgs[msg[1][0]](msg[0], *msg[1][1:])
        elif t in self.env_msgs:
            self.env_msgs[t](msg)
        else:
            raise Exception('Message {} not handled by adversary'.format(msg))
            self.pump.write('')


class DummyAdversary(UCAdversary):
    """
    Inherits from parent class UCAdversary
    The dummy adversary that forwards the environment's inputs to the functionality 
    and protocol parties.
    """
    def __init__(self, k, bits, crupt, sid, pid, channels, pump):
        """
        Args:
            k (int): the security parameters
            bits (random.Random): source of randomness
            sid (tuple): the session id of this machine
            pid (int): the process id of this machine
            channels (dict from str to GenChannel): the channels of this ITM keyed by a string:
                {'p2f': GenChannel, 'z2a': GenChannel, ....}
            handlers (dict from GenChannel to function): maps a channel to the function handling
                messages on it
            pump (GenChannel): channel to give control back to the environment
        """
        UCAdversary.__init__(self, k, bits, crupt, sid, pid, channels, pump)
        self.env_msgs['A2F'] = self.a2f
        self.env_msgs['A2P'] = self.a2p
        
    
    def __str__(self):
        return str(self.F)

    def a2f(self, msg):
        """
        Receive messages for the functionalitt from the environment and forward
        it to the functiuonality.

        Args:
            msg (tuple): message from the environment
        """
        self.write(
            ch='a2f',
            msg=msg,
        )

    def a2p(self, msg):
        """
        Read messages for the protocol parties from the environment and forward
        them to the ProtocolWrapper.

        Args:
            msg (tuple): message from the environment
        """
        self.write(
            ch='a2p',
            msg=msg,
        )

    def party_msg(self, msg):
        """
        Forward messags from protocol parties to the environment.

        Args:
            msg (tuple): message from a protocol party
        """
        self.write(
            ch='a2z',
            msg=('P2A', msg)
        )

    def func_msg(self, msg):
        """
        Forward messages from the functionality to the environment.

        Args:
            msg (tuple): message from the functionality
        """
        self.write(
            ch='a2z',
            msg=('F2A', msg)
        )

