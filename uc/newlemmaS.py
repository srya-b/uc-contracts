from itm import ITM, UCAdversary, GenChannel
from utils import wait_for, waits
import gevent
import logging

log = logging.getLogger(__name__)

def lemmaS(dummyS, adv):
    def f(k, bits, sid, pid, channels, pump, poly, importargs):
        return Lemma_Simulator(k, bits, sid, pid, channels, dummyS, adv, pump, poly, importargs)
    return f

class Lemma_Simulator(UCAdversary):
    '''     +--------+
            | lemmaS |
            +--------+-------------------+
       z2a  | +---+  (a2f,a2p)  +-----+  | a2p,a2f
     ------>| | A | ----------> | S_D |  |--------->
            | +---+             +-----+  |
            +----------------------------+
    '''
    def __init__(self, k, bits, sid, pid, channels, dummyS, adv, pump, poly, importargs):
        UCAdversary.__init__(self, k, bits, sid, pid, channels, poly, pump, importargs)


        channels['a2pfS'] = GenChannel()

        # channels for adv and dummy simulator
        self.advchannels = {
            'a2p' : GenChannel(), 'p2a' : GenChannel(),
            'a2f' : GenChannel(), 'f2a' : GenChannel(),
            'a2z' : channels['a2z'], 'z2a' : channels['z2a'],
        } 
        self.dSchannels = {
            'a2p' : channels['a2p'], 'p2a' : channels['p2a'],
            'a2f' : channels['a2f'], 'f2a' : channels['f2a'],
            'a2z' : GenChannel(), 'z2a' : GenChannel(),
        }
        self.sim_pump = GenChannel()
    
        self.dS = dummyS(k, self.bits, sid, -1, self.dSchannels, self.sim_pump, poly, importargs={'ctx': self.ctx, 'impflag':False})
        self.adv = adv(k, self.bits, sid, -2, self.advchannels, self.sim_pump, poly, importargs={'ctx': self.ctx, 'impflag':False})

        gevent.spawn(self.dS.run)
        gevent.spawn(self.adv.run)
        gevent.spawn(self.fwda2s)
        gevent.spawn(self.f2ds2_out)

    def fwdimport(self, n):
        return self.poly(self.imp_in) - self.poly(self.imp_in - n)
       
    def fwda2s(self):
        while True:
            r = gevent.wait([self.advchannels['a2p'],
                             self.advchannels['a2f'],
                             self.advchannels['a2z']],
                             count=1)
            r = r[0]
            d = r.read()
            if r == self.advchannels['a2p']:
                self.advchannels['a2p'].reset()
                self.dSchannels['z2a'].write(
                    ('A2P', d.msg, d.imp),
                    self.fwdimport(d.imp)
                )
            elif r == self.advchannels['a2f']:
                self.advchannels['a2f'].reset()
                self.dSchannels['z2a'].write(
                    ('A2F', d.msg, d.imp),
                    self.fwdimport(d.imp)
                )
            elif r == self.advchannels['a2z']:
                self.advchannels['a2z'].reset()
                self.write('a2z', d.msg, 0)
            else:
                self.pump.write('dump')

    def f2ds2_out(self):
        while True:
            r = gevent.wait([self.dSchannels['a2p'],
                             self.dSchannels['a2f'],
                             self.dSchannels['a2z']],
                             count=1)
            r = r[0]
            d = r.read()
            if r == self.dSchannels['a2p']:
                self.dSchannels['a2p'].reset()
                self.write( 'a2p', d.msg, d.imp )
            elif r == self.dSchannels['a2f']:
                self.dSchannels['a2f'].reset()
                self.write( 'a2f', d.msg, d.imp )
            elif r == self.dSchannels['a2z']:
                self.dSchannels['a2z'].reset()
                #self.write('a2z', d.msg, d.imp )
                # TODO: only for commitment 
                self.advchannels['p2a'].write(d.msg, 0)
            else:
                self.pump.write('dump')

    def env_msg(self, d):
        msg = d.msg
        imp = d.imp
        self.advchannels['z2a'].write( msg, imp ) 

    def party_msg(self, d):
        msg = d.msg
        imp = d.imp
        print('\t lemma s party msg', d)
        self.dSchannels['p2a'].write( d.msg, d.imp )

    def func_msg(self, d):
        msg = d.msg
        imp = d.imp
        self.dSchannels['f2a'].write( d.msg, d.imp )


