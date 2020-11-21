from uc.itm import UCWrappedFunctionality, ITM
from uc.utils import wait_for, waits
import gevent
import logging

class F_Pay(UCWrappedFunctionality):
    def __init__(self, k, buts, crupt, sid, pid, channels, pump, poly, importargs):
        self.ssid = sid[0]
        self.P_s = sid[1]
        self.P_r = sid[2]
        self.b_s = sid[3]
        self.b_r = sid[4]
        self.delta = sid[5]
        self.r = 3
        UCWrappedFunctionality.__init__(self, k, buts, crupt, sid, pid, channels, poly, pump, importargs)

        self.flag = "OPEN"

    def process_pay(self, v):
        if self.flag == "OPEN" and self.b_s >= v:
            self.b_s -= v
            self.b_r += v
            self.write('f2p', ((self.sid, self.P_r), ('pay', v)))
        else:
            self.pump.write('')

    def pay(self, v):
        self.leak( ("pay", v), 0 )
        self.write('f2w',  ('schedule', 'process_pay', (v,), 1), 0)
        assert wait_for(self.channels['w2f']).msg == ('OK',)
        self.write( 'f2p', ((self.sid, self.P_s), 'OK') )

    def send_to(self, to, msg, imp):
        self.write('f2p', ((self.sid, to), msg), imp)

    def process_close(self):
        if self.flag == "OPEN":
            self.flag = "CLOSE"
            msg = ('close', self.b_s, self.b_r)
            self.write( 'f2w',
                ('schedule', 'send_to', (self.P_s, msg, 0), 1), 0)
            assert wait_for(self.channels['w2f']).msg == ('OK',)
            self.write( 'f2w',
                ('schedule', 'send_to', (self.P_r, msg, 0), 1), 0)
            assert wait_for(self.channels['w2f']).msg == ('OK',)
        self.pump.write('')

    def close(self, sender):
        if sender == self.P_r:
            self.write('f2w', ('schedule', 'process_close', (), self.delta), 0)
            assert wait_for(self.channels['w2f']).msg == ('OK',)
            self.write( 'f2p', ((self.sid, sender), 'OK') )
        else: # sender == self.P_s
            self.write('f2w', ('schedule', 'process_close', (), self.r * self.delta), 0)
            assert wait_for(self.channels['w2f']).msg == ('OK',)
            self.write('f2p', ((self.sid, self.P_s), 'OK') )


    def party_msg(self, d):
        msg = d.msg
        imp = d.imp
        (_sid, sender), msg = msg
        
        if sender != self.P_s and sender != self.P_r: self.pump.write('')
        if msg[0] == 'pay' and sender == self.P_s:
            _, v = msg
            self.pay(v)
        elif msg[0] == 'close':
            self.close( sender )
        elif msg[0] == 'balance':
            if sender == self.P_s: self.write('f2p', ((_sid, sender), ('balance',self.b_s)))
            else: self.write('f2p', ((_sid, sender), ('balance',self.b_r)))
        else:
            self.pump.write('')


    def wrapper_msg(self, d):
        msg = d.msg
        imp = d.imp

        if msg[0] == 'exec':
            _, name, args = msg
            f = getattr(self, name)
            f(*args)
        else:
            self.pump.write('')


