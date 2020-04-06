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
        msg = msg.msg
        imp = msg.imp
        if sender == self.sender:
            self.eventually(self.send_msg, [msg])
            self.write('f2a', ('sent'))

    def env_msg(self, msg):
        dump.dump() # environment should not attempt to contact functionality

    def wrapper_msg(self, msg):
        pass # ignore any activation by wrapper
        
    def send_msg(self, msg):
         self.write('f2p', (self.receiver, ('sent', msg)) )