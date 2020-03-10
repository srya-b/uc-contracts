import dump
import gevent

from itm import UCAsyncWrappedFunctionality

class AsyncBroadcastFunctionality(UCAsyncWrappedFunctionality):
    def __init__(self, sid, pid, channels):
        self.ssid, self.sender, self.receiver = sid
        UCAsyncWrappedFunctionality.__init__(self, sid, pid, channels)
    def adv_msg(self, msg):
        pass # ignore any adversarial messages

    def party_msg(self, msg):
        sender, msg = msg
        if sender == self.sender:
            self.eventually(self.send_msg, [msg])

    def env_msg(self, msg):
        dump.dump() # environment should not attempt to contact functionality

    def wrapper_msg(self, msg):
        pass # ignore any activation by wrapper
        
    def send_msg(self, msg):
         self.f2p.write( (self.receiver, ('sent', msg)) )