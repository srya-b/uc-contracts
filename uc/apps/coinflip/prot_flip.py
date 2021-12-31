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
        self.mybit = self.sample(1)
        self.write( ch='p2f', msg=('commit', self.mybit) )

    #
    # The receiver's part of the code
    #
    def func_commit(self):
        self.mybit = self.sample(1)
        self.write( ch='p2f', msg=('sendmsg', ('bit', self.mybit)) )

    def func_open(self, b):
        self.theirbit = b
        self.flip = self.mybit ^ self.theirbit 
        self.pump.write('')

    # 
    # Both party's code
    #
    def func_recvmsg(self, msg):
        if self.isflipper and msg[0] == 'bit' and self.mybit is not None and self.flip is None:
            self.theirbit = msg[1]
            self.flip = self.mybit ^ self.theirbit
            self.write( ch='p2f', msg=('reveal',) )
        else:
            self.write( ch='p2z', msg=('recvmsg', msg))

    def env_getflip(self):
        if self.flip is not None:
            self.write( ch='p2z', msg=('flip', self.flip) )
        else:
            self.pump.write('')

    def env_sendmsg(self, msg):
        self.write( ch='p2f', msg=('sendmsg', msg))

    
        
       
