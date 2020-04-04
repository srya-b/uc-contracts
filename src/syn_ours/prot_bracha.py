import dump
from itm import UCWrappedProtocol, MSG
from math import ceil, floor
from utils import wait_for
from collections import defaultdict
from numpy.polynomial.polynomial import Polynomial

class Syn_Bracha_Protocol(UCWrappedProtocol):
    def __init__(self, sid, pid, channels):
        self.ssid = sid[0]
        self.parties = sid[1]
        self.delta = sid[2]
        self.n = len(self.parties)
        self.t = floor(self.n/3)
        UCWrappedProtocol.__init__(self, sid, pid, channels)

        self.prepared_value = None
        self.echoed = False
        self.readied = False
        self.committed = False
        self.num_echos = defaultdict(int)
        self.num_readys = defaultdict(int)

    def poly(self):
        #return Polynomial([1,2,3,4,5,6,7])
        return Polynomial([1])

    def except_me(self):
        return [p for p in self.parties if p != self.pid]

    def clock_round(self):
        self.tick( 1 ) # tick
        self.write('p2w', ('clock-round',), 0)
        rnd = wait_for(self.w2p).msg[1]
        return rnd

    def send_msg(self, to, msg, imp):
        r = self.clock_round()
        fchannelsid = (self.ssid, (self.sid,self.pid), (self.sid,to), r, self.delta)
        self.write('p2f', ((fchannelsid,'F_chan'), ('send',msg)), imp)
        m = wait_for(self.channels['f2p']); assert m.msg[1] == 'OK', str(m)

    def val_msg(self, sender, inp, imp):
        # Only if you haven't already prepared a value should you accept a VAL
        if not self.prepared_value and sender[1] == 1:
            self.prepared_value = inp
            print('sending ECHO')
            msg = ('ECHO', self.prepared_value)
            for pid in self.except_me():
                self.send_msg( pid, ('ECHO', self.prepared_value), 3 )
            self.num_echos[inp] += 1
        dump.dump()
   
    def echo_msg(self, inp, imp):
        n = len(self.parties)
        self.num_echos[inp] += 1
        if self.num_echos[inp] == ceil(n + (n/3))/2:
            #if not self.prepared_value:
            #    self.prepared_value = inp
            #    # send out ECHO
            #    for p in self.execpt_me():
            #        self.send_msg( p, ('ECHO', self.prepared_value), 0)
            if inp == self.prepared_value:
                # send out READY
                for p in self.except_me():
                    self.send_msg( p, ('READY', self.prepared_value), 0)
        dump.dump()

    def ready_msg(self, inp, imp):
        self.num_readys[inp] += 1
        if self.prepared_value and self.prepared_value == inp:
            if self.num_readys[inp] == floor(self.n/3) + 1 :
                for p in self.except_me():
                    self.send_msg( p, ('READY', self.prepared_value) )
        elif not self.prepared_value:
            if self.num_readys[inp] == floor(self.n/3) + 1:
                self.prepared_value = inp
                for p in self.except_me():
                    self.send_msg( p, ('ECHO', self.prepared_value) )
        dump.dump()

    def p2p_msg(self, sender, msg, imp):
        print('p2p msg', msg)
        _,msg = msg
        sid,pid = sender
        ssid,fro,to,r,d = sid
        
        if self.committed: dump.dump()
        elif msg[0] == 'VAL':
            self.val_msg( fro, msg[1], imp)
        elif msg[0] == 'ECHO':
            self.echo_msg(msg[1], imp)
        elif msg[0] == 'READY':
            self.ready_msg(msg[1], imp)
        else: print('Msg not recognized: {}'.format(msg)); dump.dump()

    def func_msg(self, d):
        msg = d.msg
        imp = d.imp
        sender,msg = msg
        if sender[1] == 'F_chan':
            self.p2p_msg(sender, msg, imp)
        else:
            dump.dump()

    def wrapper_msg(self, msg):
        dump.dump()
    def adv_msg(self, msg):
        dump.dump()

    def env_input(self, inp):
        if self.pid == 1:
            self.tick(self.n)
            for p in self.parties:
                self.send_msg( p, ('VAL', inp),  4*self.n)

    def env_msg(self, d):
        msg = d.msg
        imp = d.imp
        if msg[0] == 'input':
            self.env_input(msg[1])
        dump.dump()

from itm import ProtocolWrapper
from adversary import DummyWrappedAdversary
from syn_ours import Syn_FWrapper, Syn_Channel
from execuc import execWrappedUC
from utils import z_get_leaks

def env1(static, z2p, z2f, z2a, z2w, a2z, p2z, f2z, w2z):
    delta = 3
    n = 3
    #sid = ('one', (1,2,3), delta)
    sid = ('one', tuple(range(1,n+1)), delta)
    static.write( ('sid', sid) )

    z2p.write( ((sid,1), ('input', 2)), n*(4*n + 1) )
    wait_for(a2z)

    def channel_id(fro, to, r):
        s = ('one', (sid,fro), (sid,to), r, delta)
        return (s,'F_chan')

    # Get leaks from the channels fro=1, r=1, to=*
    # Expect to see VAL messages in channels
    (_sid,tag),msg = z_get_leaks( z2a, a2z, channel_id(1,2,1) ).msg
    print('\033[91m [Leaks] fro={}, to={}, msg={}\033[0m'.format(_sid[1][1],_sid[2][1],msg))
    (_sid,tag),msg = z_get_leaks( z2a, a2z, channel_id(1,3,1) ).msg
    print('\033[91m [Leaks] fro={}, to={}, msg={}\033[0m'.format(_sid[1][1],_sid[2][1],msg))
    (_sid,tag),msg = z_get_leaks( z2a, a2z, channel_id(1,1,1) ).msg
    print('\033[91m [Leaks] fro={}, to={}, msg={}\033[0m'.format(_sid[1][1],_sid[2][1],msg))

    # Force first pop from queue to deliver a VAL to first person
    for i in range(3):
        z2w.write( ('poll',), 1)
        m = wait_for(a2z).msg; assert m == ('poll',), str(m)
    z2w.write( ('poll',), 1 )
    wait_for(a2z)
    
    # Get leaks from the channels fro=1, r=2, to=*
    # Expect ECHO messages to all
    (_sid,tag),msg = z_get_leaks( z2a, a2z, channel_id(1,2,2)).msg
    print('fro={}, to={}, msg={}'.format(_sid[1][1],_sid[2][1],msg))
    (_sid,tag),msg = z_get_leaks( z2a, a2z, channel_id(1,3,2)).msg
    print('fro={}, to={}, msg={}'.format(_sid[1][1],_sid[2][1],msg))
    (_sid,tag),msg = z_get_leaks( z2a, a2z, channel_id(1,1,2)).msg
    print('fro={}, to={}, msg={}'.format(_sid[1][1],_sid[2][1],msg))

    # Deliver the second VAL message
    for i in range(2):
        z2w.write( ('poll',), 1)
        m = wait_for(a2z).msg; assert m == ('poll',), str(m)
    z2w.write( ('poll',), 1 )
    wait_for(a2z)
    print('*****')
#    
#    # Adversary execs the final VAL deliver
#    z2a.write( ('A2W', ('exec', 2, 0)) )
#    wait_for(a2z)
#
#    print('\n\033[1mBy this time all parties should have received a VAL message\033[0m\n')
#
#    z2a.write( ('A2W', ('delay', 5)) )
#    wait_for(a2z)
#
#    for i in range(9):
#        z2w.write( ('poll',) )
#        wait_for(a2z)
#    z2w.write( ('poll',) )
#    wait_for(a2z)
#    for _ in range(2):
#        z2w.write( ('poll',) )
#        wait_for(a2z)
#    z2w.write( ('poll',) )
#    wait_for(a2z)
#    for _ in range(2):
#        z2w.write( ('poll',) )
#        wait_for(a2z)
#    z2w.write( ('poll',) )
#    wait_for(a2z)
#    for _ in range(2):
#        z2w.write( ('poll',) )
#        wait_for(a2z)
#
#    for _ in range(10):
#        z2w.write( ('poll',) )
#        wait_for(a2z)


if __name__ == '__main__':
    execWrappedUC(env1, [('F_chan',Syn_Channel)], ProtocolWrapper, Syn_FWrapper, Syn_Bracha_Protocol, DummyWrappedAdversary)
