import dump
from itm import UCWrappedFunctionality
from utils import wait_for
import logging
log = logging.getLogger(__name__)

class Async_Channel(UCWrappedFunctionality):
    def __init__(self, sid, pid, channels, pump, poly, importargs):
        self.ssid = sid[0]
        self.sender = sid[1]
        self.receiver = sid[2]
        self.round = sid[3]
        self.pump = pump
        UCWrappedFunctionality.__init__(self, sid, pid, channels, poly, importargs)
        self.leakbuffer = None

    def leak(self, msg):
        self.write('f2w', ('leak', msg) )

    def send_message(self, msg, imp):
        log.debug('\033[91m [F_channel to={}, from={}] {}\033[0m'.format(self.receiver[1], self.sender[1], msg))
        self.write('f2p', (self.receiver, msg), imp)

    def party_send(self, sender, msg, imp):
        print('Party send', msg)
        if sender == self.sender:
            log.debug('import: {}'.format(imp))
            self.write( 'f2w', ('schedule', self.send_message, (msg,imp)), 0)
            assert wait_for(self.w2f).msg == ('OK',)
            self.leak( msg )
            self.write('f2p', (self.sender, 'OK'))
        else:
            self.pump.write("dump")

    def party_fetch(self, sender, msg):
        if sender == self.receiver and self.M:
            #self.f2p.write( (self.receiver, ('sent', self.M)) )
            # TODO sent import too 
            self.write( 'f2p', (self.receiver, ('sent', self.M)) )
        else:
            self.pump.write("dump")

    def party_msg(self, d):
        msg = d.msg
        imp = d.imp
        sender,msg = msg
        if msg[0] == 'send':
            self.party_send(sender, msg, imp)
        elif msg[0] == 'fetch':
            self.party_fetch(sender, msg)
        else:
            self.pump.write("dump")

    def adv_get_leaks(self):
        #self.f2a.write( self.leakbuffer, 0 )
        self.write( 'f2a', write( self.leakbuffer, 0 ))
        self.leakbuffer = []

    def adv_msg(self, d):
        msg = d.msg
        imp = d.imp
        if msg[0] == 'get-leaks':
            self.adv_get_leaks()
        else:
            self.pump.write("dump")
    def env_msg(self, msg):
        self.pump.write("dump")
    def wrapper_msg(self, msg):
        self.pump_write("dump")
