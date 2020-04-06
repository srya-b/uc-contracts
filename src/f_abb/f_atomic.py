import dump
import gevent

from itm import UCAsyncWrappedFunctionality

class AtomicBroadcastFunctionality(UCAsyncWrappedFunctionality):
    def __init__(self, sid, pid, channels):
        self.sid = sid
        self.parties = None # TODO: define sid to include parties
        self.pid = pid
        self.BC = []
        UCAsyncWrappedFunctionality.__init__(self, sid, pid, channels)
        
    def adv_msg(self, msg):
        pass # ignore any adversarial messages

    def party_msg(self, msg):
        dealer, msg = msg
        msg = msg.msg
        imp = msg.imp
        # need to convert sender to [0, n-1]
        if msg[0] == 'tx':
            tx = msg[1]
            self.eventually(append_tx, [tx, dealer])

    def env_msg(self, msg):
        dump.dump() # environment should not attempt to contact functionality

    def wrapper_msg(self, msg):
        pass # ignore any activation by wrapper
        
    def append_tx(self, tx, dealer):
        self.BC.append((tx, dealer))
        pos = len(self.BC)
        for party in self.parties:
            self.eventually(lambda j: self.write('f2p', ((self.sid, party), ('blockchain', self.BC[1:j])) ), [pos])