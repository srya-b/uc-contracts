from uc.itm import UCWrappedFunctionality, ITM
from uc.utils import wait_for, waits
from numpy.polynomial.polynomial import Polynomial
import gevent
import logging

log = logging.getLogger(__name__)

class Syn_Bracha_Functionality(UCWrappedFunctionality):
    def __init__(self, k, bits, crupt, sid, pid, channels, pump, poly, importargs):
        self.ssid = sid[0]
        self.parties = sid[1]
        self.n = len(self.parties)
        self.round_upper_bound = 5
        self.delta = sid[2] * self.round_upper_bound
        UCWrappedFunctionality.__init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs)

    def send_output(self, to, msg):
        self.write('f2p', (to, msg) )

    '''Dealer, assumed to be pid=1 gives some input and invokes
    the synchronous wrapper around it to deliver the output to all
    of the parties in O(1) time.'''
    def party_input(self, pid, inp):
        if pid == 1:
            for p in self.parties:
                #self.f2w.write( ('schedule', self.send_output, ((self.sid,p), inp), self.delta), 0)
                print('scheduling input')
                self.write('f2w', ('schedule', self.send_output, ((self.sid,p), inp), self.delta), 0)
                m = wait_for(self.channels['w2f']).msg
                assert m == ('OK',)
            n = len(self.parties)
            self.leak( ('input', pid, inp), n*(4*n + 1))
        print('f2p channel', self.channels['f2p'])
        self.write('f2p', ((self.sid,pid), 'OK'))


    def party_msg(self, d):
        log.debug('Party msg in bracha {}'.format( d))
        msg = d.msg
        imp = d.imp
        sender,msg = msg
        sid,pid = sender
        if msg[0] == 'input':
            self.party_input(pid, msg[1])
        elif msg[0] == 'output':
            self.party_output(pid)
        else: self.pump.write("dump")

    def wrapper_msg(self, msg):
        self.pump.write("dump")
    def adv_msg(self, msg):
        self.pump.write("dump")
    def env_msg(self, msg):
        self.pump.write("dump")

