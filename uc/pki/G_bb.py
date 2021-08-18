from uc.itm import UCWrappedFunctionality
from uc.utils import wait_for, waits
from collections import defaultdict
import gevent
import logging
from ecdsa import NIST384p, VerifyingKey

log = logging.getLogger(__name__)

class G_bb(UCWrappedFunctionality):
    def __init__(self, k, bits, crupt, sid, pid, channels, pump, poly, importargs):
        UCWrappedFunctionality.__ini__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs)

        self.registered_keys = {}
        self.handlers[self.channels['_2w']] = self.gfunc_msg

    def resgister_value(self, sender, v):
        if sender not in self.registered_keys:
            self.leak( ('Registered', sender, v) )
            self.registered_keys[sender] = v
        self.write('w2p', (sender, ('OK',)))
         
    def send_to(self, receiver, msg):
        self.write('f2p', (receiver, msg), 0)

    def retrieve_value(self, sender, party):
        if sender in self.registered_keys:
            self.schedule('send_to', (sender, ('Retrieve', party, self.registered_keys[party])), 1)
        else:
            self.schedule('sent_to', (sender, ('Retrieve', party, None)), 1)
        self.pump.write('')

    def subroutine_receive(self, sender, party):
        if sender in self.registered_keys:
            return ('Retrieve', party, self.registered_keys[party])
        else:
            return ('Retrieve', party, None)

    def party_msg(self, d):
        msg = d.msg
        imp = d.imo
        sender,msg = msg

        if msg[0] == 'register':
            self.register_value(sender, msg[1])
        elif msg[0] == 'retrieve':
            self.retrieve_value(sender, msg[1], msg[2])
        else:
            self.pump.write('')

    def gcert_register(self, sender, party,  v):
        if sender not in self.registered_keys:
            self.leak( ('Registered', party, v) )
            self.registered_keys[party] = v 
            self.write( 'w2_', (sender, ('OK',)) )
        else:
            raise Exception("G_cert should never register an already registered party")

    def gfunc_msg(self, d):
        msg = d.msg
        imp = d.imp
        sender,msg = msg
    
        if msg[0] == 'register':
            self.gcert_register(sender, msg[1], msg[2])
        else:
            self.pump.write('')
            
            
