import gevent
from uc.itm import ITM, UCAdversary
from gevent.queue import Queue, Channel, Empty
from gevent.event import AsyncResult
from collections import defaultdict

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
        self.channels['a2z'].write( ('P2A', msg) )

    def func_msg(self, msg):
        """
        Forward messages from the functionality to the environment.

        Args:
            msg (tuple): message from the functionality
        """
        self.channels['a2z'].write( ('F2A', msg) )

