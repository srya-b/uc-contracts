from uc.itm import UCWrappedFunctionality
from uc.utils import wait_for
import logging
log = logging.getLogger(__name__)

class Contract_Pay(UCWrappedFunctionality):
    def __init__(self, k, bits, sid, pid, channels, pump, poly, importargs):    
        self.ssid = sid[0]
        self.P_s = sid[1]
        self.P_r = sid[2]
        self.b_s = sid[3]
        self.b_r = sid[4]
        self.delta = sid[5]
        UCWrappedFunctionality.__init__(self, k, buts, crupt, sid, pid, channels, poly, pump, importargs)
        self.leakbuffer = None
        self.flag = 'OffChain'
        self.nonce = 0
        self.T_settle = 2 * self.delta
        self.T_deadline = -1
        self.state = (self.b_s, self.b_r, self.nonce)

    def clock_round(self):
        self.write('f2w', ('clock-round',), 0)
        rnd = wait_for(self.channels['w2f']).msg[1]
        return rnd

    def check_sig(self, _sig, _state):
        return True
    
    def close(self, _sender, _state, _sig):
        if self.flag == "OffChain" and self.check_sig(_sig, _state):
            _b_s, _b_r, _nonce = _state
            if _nonce >= self.nonce and _b_s + _b_r == self.b_s + self.b_r and _b_r >= self.b_r:
                self.nonce = _nonce
                self.state = _state
                if _sender is self.P_r:
                    self.flag = "Closed"
                    self.broadcast( ("Closed", self.state), 0 )
                else:
                    self.flag = "UnCoopClose"
                    self.T_deadline = self.clock_round() + self.T_settle
                    self.broadcast( ("UnCoopClose", self.state, self.T_deadline), 0)
        else:
            self.pump.write('')

    def challenge(self, _sender, _state, _sig):
        if _sender is self.P_r and self.flag is "UnCoopClose" and self.check_sig(_sig, _state):
            _b_s, _b_r, _nonce = _state
            if _nonce >= self.nonce:
                self.flag = "Closed"
                self.state = _state
                self.nonce = _nonce
                self.broadcsat( ("Closed", self.state), 0 )
            else:
                self.pump.write('')
        else:
            self.pump.write('')

    def route_party_msg(sender, msg, imp):
        if msg[0] == 'close':
            _, _state, _sig = msg
            self.close(sender, _state, _sig)
        elif msg[0] == 'challenge':
            _, _state, _sid = msg
            self.challenge(sender, _state, _sig)
        else:
            self.pump.write('dump')

    def party_msg(self, d):
        msg = d.msg
        imp = d.imp
        (_sid, _sender),msg = msg
        
        self.write( 'f2w',
            ('schedule',
            self.route_party_msg,
            (_sender, msg, imp),
            self.delta),
            0
        )
        assert wait_for(self.channels['w2f']).msg == ('OK',)
        self.leak(msg)
        self.pump.write('dump')
    
    def send_to(self, to, msg, imp):
        self.write('f2p', (to, msg), imp)

    def broadcast(self, msg, imp):
        self.leak(msg)
        self.write( 'f2w',
            ('schedule',
            self.send_to,
            ((self.sid, self.P_s), msg, imp),
            1),
            0
        )
        assert wait_for(self.channels['w2f']).msg == ('OK',)
        self.write('f2w',
            ('schedule',
            self.send_to,
            ((self.sid, self.P_r), msg, imp),
            1),
            0
        )
        assert wait_for(self.channels['w2f']).msg == ('OK',)
        self.leak(('bcast', msg))
        self.pump.write('dump')



