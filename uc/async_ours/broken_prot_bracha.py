import dump
from itm import UCWrappedProtocol, MSG
from math import ceil, floor
from utils import wait_for, waits
from collections import defaultdict
from numpy.polynomial.polynomial import Polynomial
import logging

log = logging.getLogger(__name__)

class Broken_Bracha_Protocol(UCWrappedProtocol):
    def __init__(self, sid, pid, channels, pump, poly, importargs):
        self.ssid = sid[0]
        self.parties = sid[1]
        self.n = len(self.parties)
        self.t = floor(self.n/3)
        self.pump = pump
        UCWrappedProtocol.__init__(self, sid, pid, channels, poly, importargs)

        self.prepared_value = None
        self.echoed = False
        self.readied = False
        self.committed = False
        self.num_echos = defaultdict(int)
        self.num_readys = defaultdict(int)
        self.num_sent = dict((p,0) for p in self.parties)
        self.halt = False

    def except_me(self):
        return [p for p in self.parties if p != self.pid]

    def send_msg(self, to, msg, imp):
        fchannelsid = (self.ssid, (self.sid,self.pid), (self.sid,to), self.num_sent[to])
        self.num_sent[to] += 1
        log.debug("\nsending import: {}".format(imp))
        self.write('p2f', ((fchannelsid,'F_chan'), ('send',msg)), imp)
        m = wait_for(self.channels['f2p'])
        assert m.msg[1] == 'OK', str(m)

    def val_msg(self, sender, inp, imp):
        # Only if you haven't already prepared a value should you accept a VAL
        if sender[1] == 1:
            self.prepared_value = inp
            msg = ('ECHO', self.prepared_value)
            for pid in self.except_me():
                self.send_msg( pid, ('ECHO', self.prepared_value), 3)
            self.num_echos[inp] += 1
        self.pump.write("dump")
   
    def echo_msg(self, inp, imp):
        n = len(self.parties)
        self.num_echos[inp] += 1
        log.debug('[{}] Num echos {}, required: {}'.format(self.pid, self.num_echos[inp], ceil(n+(n/3))/2))
        if self.num_echos[inp] == floor((n + (n/3))/2):
            self.num_readys[inp] += 1
            # send out READY
            for p in self.except_me():
                self.send_msg( p, ('READY', self.prepared_value), 0)
        self.pump.write("dump")

    def ready_msg(self, inp, imp):
        self.num_readys[inp] += 1
        assert imp == 0
        log.debug('[{}] Num readys {}'.format(self.pid, self.num_readys[inp]))
        log.debug('required {}'.format(floor(2*(self.n/3))))
        if self.num_readys[inp] == floor(2*(self.n/3)):
            print('\033[92m [{}] Accepted input {}\033[0m'.format(self.pid, self.prepared_value))
            self.write( 'p2z', self.prepared_value )
            self.halt = True
            return
        self.pump.write("dump")

    def p2p_msg(self, sender, msg, imp):
        _,msg = msg
        sid,pid = sender
        print('sid', sid)
        ssid,fro,to,d = sid
        
        if self.committed: self.pump.write("dump")# dump.dump()
        elif msg[0] == 'VAL':
            self.val_msg( fro, msg[1], imp)
        elif msg[0] == 'ECHO':
            self.echo_msg(msg[1], imp)
        elif msg[0] == 'READY':
            self.ready_msg(msg[1], imp)
        else: print('Msg not recognized: {}'.format(msg)); self.pump.write("dump")#dump.dump()

    def func_msg(self, d):
        if self.halt: self.pump.write('dump'); return
        msg = d.msg
        imp = d.imp
        sender,msg = msg
        if sender[1] == 'F_chan':
            self.p2p_msg(sender, msg, imp)
        else:
            #dump.dump()
            self.pump.write("dump")

    def wrapper_msg(self, msg):
        self.pump.write("dump")
    def adv_msg(self, msg):
        self.pump.write("dump")

    def env_input(self, inp):
        if self.halt: self.pump.write('dump'); return
        if self.pid == 1:
            for p in self.parties:
                self.send_msg( p, ('VAL', inp), 4*len(self.parties))
        #self.pump.write("dump")
        self.write('p2z', 'OK')

    def env_msg(self, d):
        if self.halt: self.pump.write('dump'); return
        msg = d.msg
        imp = d.imp
        if msg[0] == 'input':
            self.env_input(msg[1])
        else:
            self.pump.wite("done")

