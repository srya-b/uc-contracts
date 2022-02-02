from uc.itm import ITM, GenChannel
import logging
import gevent

class UCProtocol(ITM):
    """ Inherits from the basic ITM and implements common functionality to all protocol parties.
    It expects the channels for a protocol party and functions to assign handlers to specific
    messages.

    Attributes:
        f (lambda): func to parse out the message type from a functionality message
        parse (lambda): func to parse ou the rest of the message from a functionality
        env_msgs (dict from str to func): handlers for specific message types from Z
        func_msgs (dict from str to func): handlers for specific message typed from A
            example: ('testmsg', msgcontent) from Z is handled by `self.env_msgs['testmsf] = self.some_function`
    """
    def __init__(self, k, bits, sid, pid, channels, pump):
        """
        Args: 
            k (int): the security parameters
            bits (random.Random): source of randomness
            sid (tuple): the session id of this machine
            pid (int): the process id of this machine
            channels (dict from str to GenChannel): the channels for the protocol party only:
                {'p2f': ..., 'f2p': ..., 'z2p': ... , 'p2z': ...}
            handlers (dict from GenChannel to function): maps a channel to the function handling
                messages on it
            pump (GenChannel): channel to give control back to the environment
        """
        self.handlers = {
            channels['z2p'] : self.env_msg,
            channels['f2p'] : self.func_msg,
        }
        ITM.__init__(self, k, bits, sid, pid, channels, self.handlers, pump)
        self.f = lambda x: x[0]
        self.parse = lambda x: x[1:]
        self.env_msgs = {}
        self.adv_msgs = {}
        self.func_msgs = {}

    def adv_msg(self, msg):
        """ Protocol is never written to by the adversary. The party wrapper forwards 
        messages for corrupt parties itself. It never spawns corrupt parties.

        Throws:
            Exception: UCProtocol is only for honest parties, not corrupt parties
        """
        Exception("adv_msg needs to be defined")

    def func_msg(self, msg):
        """ Handlers for messages from the functionality. `self.f` gets the message type
        and tees it off to the handler for that message type

        Args:
            msg (tuple): message from functionality
        """

        # tee message to handler for this message type or do nothing
        if self.f(msg) in self.func_msgs:
            self.func_msgs[self.f(msg)](*(self.parse(msg)))
        else:
            self.pump.write('')

    def env_msg(self, msg):
        """ Handlers for messages from Z. msg[0] is the type of the message
        and tees it off to the handler for that message type

        Args:
            msg (tuple): message from Z
        """
        if msg[0] in self.env_msgs:
            self.env_msgs[msg[0]](*msg[1:])
        else:
            self.pump.write('')

class DummyParty(ITM):
    """ The dummy party that passes through all the messages directly to the functionality and back to
    the environment. Ideal world parties are dummy parties.
    """
    def __init__(self, k, bits, sid, pid, channels, pump):
        """ Same as UCProtocol """
        self.handlers = {
            channels['z2p'] : self.env_msg,
            channels['a2p'] : self.adv_msg,
            channels['f2p'] : self.func_msg
        }
        ITM.__init__(self, k, bits, sid, pid, channels, self.handlers, pump)

    def adv_msg(self, msg):
        self.write('p2f', msg)
        raise Exception('Adv cant write to an honest party')

    def env_msg(self, msg):
        """ Pass environment messages to the functionality.
        Args:
            msg (tuple): message from Z.
        """
        self.write('p2f', msg)

    def func_msg(self, msg):
        """ Pass functionality messages to Z.
        Args:
            msg (tuple): message from the functionality
        """
        self.write('p2z', msg)

def protocolWrapper(prot):
    """ Return a protocol wrapper parameterized with the required protocol. Its
    done this way to keep the interface of the ProtocolWrapper for the same as 
    UCProtocol.
    """
    def f(k, bits, crupt, sid, channels, pump):
        return ProtocolWrapper(k, bits, crupt, sid, channels, pump, prot)
    return f

from collections import defaultdict
class ProtocolWrapper(ITM):
    """ This wrapper handles all messages intended for protocol parties in the UC execution.
    It spawns new protocol parties when the first message arrives for a particular pid for 
    the first time. It routes messages to/from the protocol parties it runs internally.

    Attributes:
        z2pid (dict from pid to GenChannel): the z2p channel for a particular pid
        f2pid (dict from pid to GenChannel): the f2p channel for a particular pid
        a2pid (dict from pid to GenChannel): the a2p channel for a particular pid (channel is never actually used)
        prot (UCProtocol): instance of the protocol to spawn as new parties.
    """
    def __init__(self, k, bits, crupt, sid, channels, pump, prot):
        self.crupt = crupt
        self.z2pid = {}
        self.f2pid = {}
        self.a2pid = {}
        self.prot = prot
        self.log = logging.getLogger('ProtocolWrapper')
        self.handlers = {
            channels['z2p'] : self.env_msg,
            channels['a2p'] : self.adv_msg,
            channels['f2p'] : self.func_msg,
        }
        ITM.__init__(self, k, bits, sid, None, channels, self.handlers, pump)

    def is_dishonest(self, pid):
        """ Check is party `pid` is corrupt.

        Args:
            pid (int): the party to check
        """
        return pid in self.crupt

    def is_honest(self, sid, pid):
        """ Check if `pid` is honest.

        Args:
            pid (int): party to check.
        """
        return not self.is_dishonest(pid)

    def _newPID(self, pid, _2pid, p2_, tag):
        """ Creates two channels for a protocol party to a specific other ITM. For example,
        for the environment this function creates the party's its z2p and p2z channels.
        It also spawns an intermediate channel for one of a party's outgoing channels (p2z), and
        runs it through _translate which appends the party's pid to it. Message from 
        pid=1 on it's p2z channel arrives in _translate as msg (tuple) and is sent out 
        on the party wrapper's p2z channel as (pid, msg). It saves the channel in the appropriate
        dictionary to route messages to/from the party.

        Args:
            pid (int): the pid of the party
            _2pid (dict from pid to GenChannel): the dictionary that stores the incoming channels
                for each party (in this example, this is `self.z2pid`)
            p2_ (GenChannel): the protocol wrapper's real outgoing channel (for the example `p2z`)
            tag (str): a name to give the spawned channels
        """

        # create the intermediate outgoing channel for the party that is intercepted
        # and has pid appended to it
        pp2_ = GenChannel(('write-translate-{}'.format(tag),self.sid,pid)) 

        # an incoming channel for the party
        _2pp = GenChannel(('read-{}'.format(tag),self.sid,pid)) 

        def _translate():
           while True:
                # intercept outgoing messages
                r = gevent.wait(objects=[pp2_],count=1)
                msg = r[0].read()
                pp2_.reset()

                # and append `pid` to it
                p2_.write( (pid, msg) )
        gevent.spawn(_translate)

        # put the outgoing channel dictionary for it
        _2pid[pid] = _2pp
        return (_2pp, pp2_) 

    def newPID(self, pid):
        """ Instantiate a new party with pid `pid`. Create new channels for the party
        and store all the channels in the appropriate functions. Outgoing channels from the
        parties pass through `_translate` in `_newPID` which appends the pid of the sending party 
        to the message.

        Args:
            pid (int): pid instance to create.
        """
        print('\033[1m[{}]\033[0m Creating new party with pid: {}'.format('PWrapper', pid))

        # create all the internal channels for this protocol instance and wrap outgoing channels
        # with _translate in _newPID
        _z2p,_p2z = self._newPID(pid, self.z2pid, self.channels['p2z'], 'p2z')
        _f2p,_p2f = self._newPID(pid, self.f2pid, self.channels['p2f'], 'p2f')
        _a2p,_p2a = self._newPID(pid, self.a2pid, self.channels['p2a'], 'p2a')
       
        # spawn the protocol
        p = self.prot(self.k, self.bits, self.sid, pid, {'a2p':_a2p,'p2a':_p2a, 'z2p':_z2p,'p2z':_p2z, 'f2p':_f2p, 'p2f':_p2f}, self.pump)
        gevent.spawn(p.run)

    def getPID(self, _2pid, pid):
        """ Gets the incoming channel for the party with `pid` from _2pid.

        Args:
            _2pdid (dict from pid to GenChannel): either `z2pid` or `f2pid` to query the channel for `pid`.

        Returns:
            (GenChannel): the corresponding incoming channel for the party `pid`.
        """
        if (pid) in _2pid: return _2pid[pid]
        else:
            self.newPID(pid)
            return _2pid[pid]

    def env_msg(self, msg):
        """Handle messages incoming from z2p. Get the z2p channel for the party and write on it
        or create the party first if it doesn't exist.

        Args
            msg (tuple(pid,tuple)): the message from the environment to a particular `pid`.

        Throws:
            Exception: if Z is trying to give input to a corrupt party.
        """
        pid,msg = msg
        if self.is_dishonest(pid): raise Exception("Environment writing to corrupt party")
        _pid = self.getPID(self.z2pid,pid)
        _pid.write(msg)
    
    def func_msg(self, msg):        
        """Handle messages incoming from f2p. Get the f2p channel for the party and write on it
        or create the party first if it doesn't exist. If the party is corrupt it just forwards
        the message to the adversary, instead.

        Args
            msg (tuple(topid,tuple)): the message from the functionality to a particular `pid`.
        """
        topid, msg = msg
        if self.is_dishonest(topid):
            self.write('p2a', (topid, msg))
        else:
            _pid = self.getPID(self.f2pid, topid)
            _pid.write( msg)

    def adv_msg(self, msg):
        """ Handle messages incoming from a2p for a corrupt party. If the party is corrupt
        forward the message to the functionality unaltered. 

        Args:
            msg (tuple(pid,tuple)): the message from the adversary for party `pid`.

        Throws:
            Exception: if the adversary is giving input to an honest party.
        """
        pid, msg = msg
        if self.is_honest(self.sid, pid): raise Exception("adv writing to an honest party: {}. Cruptset: {}".format((self.sid,pid), self.crupt))
        self.write( 'p2f', (pid, msg))
