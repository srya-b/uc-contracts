from uc.itm import ITM


class UCFunctionality(ITM):
    """ Base class for functionalities. Helpers for `p2f`, `f2p`, `a2f`, `f2a` channels.

    Attributes:
        party_msgs (dict from str to func): handlers for message types from a party
        adv_msgs (dict from str to func): handlers for message types from A
    """
    def __init__(self, k, bits, crupt, sid, channels, pump):
        """
        Args:
            k (int): the security parameters
            bits (random.Random): source of randomness
            crupt (set[int]): set of corrupt PIDs
            sid (tuple): the session id of this machine
            pid (int): the process id of this machine
            channels (dict from str to GenChannel): the channels of this ITM keyed by a string:
                {'p2f': GenChannel, 'f2p': GenChannel, ....}
            handlers (dict from GenChannel to function): maps a channel to the function handling
                messages on it
            pump (GenChannel): channel to give control back to the environment
        """
        self.crupt = crupt
        self.handlers = {
            channels['p2f'] : self.party_msg,
            channels['a2f'] : self.adv_msg,
        }

        to_write = ['f2p', 'f2a']
        ITM.__init__(self, k, bits, sid, -1, channels, self.handlers, to_write, pump)

        self.party_msgs = {}
        self.adv_msgs = {}

        self.p_msg = lambda x: x[0]
        self.p_parse = lambda x: x[1:]

    def is_honest(self, sid, pid):
        """Check if a party `pid` is corrupt or not.

        Args:
            pid (int): party pid to check if corrupt
        """
        return (sid,pid) not in self.crupt

    def is_dishonest(self, sid, pid):
        """Handle messages from parties. Parse the `pid` of the sender and the `msg` and tee
        off to the handler for the message type.

        Args:
            d (tuple(pid, msg)): message from the partywrapper for a corrupt party
        """
        return not self.is_honest(sid, pid)

    def wrapwrite(self, msg):
        """ A function to alter all outgoing message from the functionality. By default,
        it does nothing to the message.

        Args:
            msg (tuple): message being sent out by the functionality.
        """
        return msg

    def adv_msg(self, msg):
        """ Handle messages from the channel a2f. Tee it off to the msg handler.

        Args:
            msg (tuple): message from the adversary.
        """
        if msg[0] in self.adv_msgs:
            self.adv_msgs[msg[0]](*msg[1:])
        else:
            self.pump.write('')

    def party_msg(self, m):
        """ Handle messages from the channel p2f. Tee if off to the msg handler.
        
        Args:
            msg (tuple(pid,msg)): message from protocol party with `pid`.
        """
        sender,msg = m
        if self.p_msg(msg) in self.party_msgs:
            self.party_msgs[self.p_msg(msg)](sender, *self.p_parse(msg))
        else:
            raise Exception('unknown message', msg)
            self.pump.write('')

    def env_msg(self, msg):
        """ Functionality has a f2z and z2f channel just for completeness but should 
        never get any input on them """
        Exception("env_msg needs to be defined")


