import dump
import gevent

from itm import UCAsyncWrappedFunctionality
from utils import MessageTag

class AsyncBroadcastFunctionality(UCAsyncWrappedFunctionality):
    def __init__(self, sid, pid, channels, pump):
        self.ssid, self.sender, self.receiver, self.msg_id = sid
        self.used = False
        UCAsyncWrappedFunctionality.__init__(self, sid, pid, channels)
    def adv_msg(self, msg):
        pass # ignore any adversarial messages

    def party_msg(self, msg):
        imp = msg.imp
        msg = msg.msg
        sender, msg = msg
        if sender == self.sender and not self.used:
            self.eventually(self.send_msg, [msg])
            self.used = True
            self.leak(('sent',))
            self.write('f2p', (self.sender, (MessageTag.OK,)))

    def env_msg(self, msg):
        dump.dump() # environment should not attempt to contact functionality
        
    def send_msg(self, msg):
        self.write('f2p', (self.receiver, ('sent', self.sender[1], msg)) )