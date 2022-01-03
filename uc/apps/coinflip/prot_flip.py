from uc.itm import UCProtocol
from uc.utils import waits, wait_for
import logging

log = logging.getLogger(__name__)

class Flip_Prot(UCProtocol):
    def __init__(self, k, bits, sid, pid, channels, pump):
        self.ssid = sid[0]
        self.flipper = sid[1]
        self.receiver = sid[2]
        self.isflipper = pid == self.flipper
        UCProtocol.__init__(self, k, bits, sid, pid, channels, pump)
        
        self.env_msgs['flip'] = self.env_flip
        self.env_msgs['getflip'] = self.env_getflip
        self.env_msgs['sendmsg'] = self.env_sendmsg

        self.mybit = None
        self.theirbit = None
        self.flip = None

        self.func_msgs['recvmsg'] = self.func_recvmsg
        if not self.isflipper:
            self.func_msgs['commit'] = self.func_commit
            self.func_msgs['open'] = self.func_open

    #
    # The flipper's part of the code 
    #
    def env_flip(self):
        """FLIPPER: Z message telling flipper to do flip. 
        Flipper commits to a bit `b`.

        Msg:
            From Z: ('flip',)

        Sends:
            To F_Com: ('commit' bit)
        """
        self.mybit = self.sample(1)
        self.write( ch='p2f', msg=('commit', self.mybit) )

    #
    # The receiver's part of the code
    #
    def func_commit(self):
        """RECEIVER: F_com outputs to the receiver that the flipper
        init'd a commitment. Receiver responds with a random bit.

        Msg:
            From F_Com: ('commit',)

        Sends:
            To F_com: ('sendmsg', msg)
        """
        self.mybit = self.sample(1)
        self.write( ch='p2f', msg=('sendmsg', ('bit', self.mybit)) )

    def func_open(self, b):
        """RECEIVER: F_com putputs open and committed bit b to the receiver.
        The receiver computs the flip = committed bit xor random bit.

        Msg:
            From F_Com: ('open', bit)

        Args:
            b: the bit committed in F_Com
        """
        self.theirbit = b
        self.flip = self.mybit ^ self.theirbit 
        self.pump.write('')

    # 
    # Both party's code
    #
    def func_recvmsg(self, msg):
        """Receiving a message from F_Com. If it's part of the protocol (the bit received by
        the flipper). If it's the bit compute the flip and open the commitment. No messages 
        received by the receiver for protocol so forward all of them to Z.

        Msg:
            From F_Com: ('recvmsg', msg)

        Sends:
            To F_com: ('reveal',)
            To Z: ('recvmsg', msg)

        Args:
            msg: the message received from F_com
        """
        if self.isflipper and msg[0] == 'bit' and self.mybit is not None and self.flip is None:
            self.theirbit = msg[1]
            self.flip = self.mybit ^ self.theirbit
            self.write( ch='p2f', msg=('reveal',) )
        else:
            self.write( ch='p2z', msg=('recvmsg', msg))

    def env_getflip(self):
        """Z trying to get the flip outcome from either party. If the flip is computed output
        it to Z otherwise don't do anything.

        Msg:
            From Z: ('getflip',)

        Sends:
            To Z: ('flip', f)
        """
        if self.flip is not None:
            self.write( ch='p2z', msg=('flip', self.flip) )
        else:
            self.pump.write('')

    def env_sendmsg(self, msg):
        """Z telling the party to send a message to the other party. Forward whatever message
        Z tells us to. Unrelated to the flip protocol.

        Msg:
            From Z: ('sendmsg', msg)

        Sends:
            To F_Com: ('sendmsg', msg)

        Args: 
            msg: the message Z wants the party to send.
        """
        self.write( ch='p2f', msg=('sendmsg', msg))

    
        
       
