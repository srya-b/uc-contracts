import dump
from itm import UCWrappedFunctionality, ITM
from utils import wait_for, waits
from numpy.polynomial.polynomial import Polynomial

class Syn_Bracha_Functionality(UCWrappedFunctionality):
    def __init__(self, sid, pid, channels, pump):
        self.ssid = sid[0]
        self.parties = sid[1]
        self.n = len(self.parties)
        self.pump = pump
        UCWrappedFunctionality.__init__(self, sid, pid, channels)

    def poly(self):
        return Polynomial([1])

    def send_output(self, to, msg):
        self.tick(0)
        self.f2p.write( (to, msg) )

    '''Dealer, assumed to be pid=1 gives some input and invokes
    the synchronous wrapper around it to deliver the output to all
    of the parties in O(1) time.'''
    def party_input(self, pid, inp):
        if pid == 1:
            for p in self.parties:
                self.f2w.write( ('schedule', self.send_output, (p, inp), 5), 0)
                m = wait_for(self.w2f).msg
                assert m == ('OK',)
            n = len(self.parties)
            #self.leak( ('input', pid, inp), n*(4*n+1) )
            self.leak( ('input', pid, inp), 0)
        self.pump.write("dump")
        #dump.dump() 


    def party_msg(self, d):
        print('Party msg in bracha', d)
        msg = d.msg
        imp = d.imp
        sender,msg = msg
        sid,pid = sender
        if msg[0] == 'input':
            self.party_input(pid, msg[1])
        elif msg[0] == 'output':
            self.party_output(pid)
        else: self.pump.write("dump")#dump.dump()

    def wrapper_msg(self, msg):
        self.pump.write("dump")
    def adv_msg(self, msg):
        self.pump.write("dump")
    def env_msg(self, msg):
        self.pump.write("dump")

from itm import ProtocolWrapper
from exuc import createWrappedUC
from syn_ours import Syn_Channel, Syn_Bracha_Protocol
class RBC_Simulator(ITM):
    def __init__(self, sid, pid, channels, pump):
        self.ssid = sid[0]
        self.parties = sid[1]
        self.delta = sid[2]
        self.pump = pump

        self.internal_run_queue = {}
        self.internal_delay = 0
    
        # TODO change the SID to be the same so that the leaks are the same sid stupid!
        print('Simulated')
        self.sim_channels,static,_pump = createWrappedUC([('F_chan',Syn_Channel)], ProtocolWrapper, Syn_FWrapper, Syn_Bracha_Protocol, DummyWrappedAdversary)
        self.sim_sid = (sid[0], sid[1], sid[2])
        self.sim_pump = _pump
        static.write( ('sid', self.sim_sid) )
        
        handlers = {
            channels['p2a']: self.party_msg,
            channels['z2a']: self.env_msg,
            channels['w2a']: self.wrapper_msg,
            channels['f2a']: self.func_msg,
            self.sim_channels['p2z']: self.sim_party_msg,
            self.sim_channels['a2z']: self.sim_adv_msg,
            self.sim_channels['f2z']: self.sim_func_msg,
            self.sim_channels['w2z']: self.sim_wrapper_msg,
        }

        ITM.__init__(self, sid, pid, channels, handlers)

    def poly(self):
        return Polynomial([1])

    def sim_party_msg(self, d):
        #dump.dump()
        self.pump.write("dump")

    def sim_adv_msg(self, d):
        #dump.dump()
        self.pump.write("dump")
    
    def sim_func_msg(self, d):
        #dump.dump()
        self.pump.write("dump")

    def sim_wrapper_msg(self, d):
        #dump.dump()
        self.pump.write("dump")

    def party_msg(self, d):
        msg = d.msg
        imp = d.imp
        self.tick(1)
        self.channels['a2z'].write( msg, imp)
   
    def env_get_leaks(self):
        self.tick(1)
        self.channels['a2w'].write( ('get-leaks',) )
        m = wait_for( self.channels['w2a'] )
        msg = m.msg

        wrapper_leaks = []
        for leak in msg:
            sender,msg,imp = leak
            print('msg', msg)
            
            # This must be the dealer leaked input
            if sender == (self.sid, 'F_bracha'):
                if msg[0] == 'input':
                    n = len(self.parties)
                    #assert imp == n*(4*n+1), 'imp: ' + str(imp)
                    self.tick(0)    # wrapper doesn't get anything because it's just writing back
                    print('\n\t\t\033[1m Simulation beginning\033[0m\n')

                    # write ('input', x) to z2p in the locl emulation
                    self.sim_channels['z2p'].write( ((self.sim_sid,1), ('input', msg[2])), imp )
                    m = waits(self.sim_pump, self.sim_channels['a2z'])
                    assert m.msg == 'dump'
                    #m = wait_for(self.sim_channels['p2z'])
                    print('\n\t\t\033[1m Simulation ending\033[0m\n')

                    # check for new messages in the internal wrapper

                else:
                    print('Just some schedules.')

        # Get leaks from the internal wrapper
        self.sim_channels['z2a'].write( ('A2W', ('get-leaks',)) )
        leaks = waits(self.sim_pump, self.sim_channels['a2z'])
        assert len(leaks.msg)
        n = 0

        # update internal copy of runqueue
        for x in leaks.msg:
            fro,s,i = x
            if s[0] == 'schedule': 
                n += 1
                _,rnd,idx,fname = s
                if rnd not in self.internal_run_queue:
                    self.internal_run_queue[rnd] = []
                self.internal_run_queue[rnd].insert( idx, s )
                self.internal_delay += 1
            else: print('COOKIES!')

        # add delay to wrapper
        print('Add n={} delay to ideal world wrapper'.format(n))
        self.write('a2w', ('delay', n))
        m = waits(self.pump, self.channels['w2a'])
        assert m.msg == "OK", str(m.msg)

        # send emulated leaks to Z. Go on, fool the ol bastard.
        self.write('a2z', leaks.msg, leaks.imp)

    def env_exec(self, rnd, idx):
        # pass the exec onto the internel wrapper and check for output by some party
        self.sim_channels['z2a'].write( ('A2W', ('exec', rnd, idx)) )
        m = waits(self.sim_pump, self.sim_channels['a2z'], self.sim_channels['p2z'])
        if m:
            self.write( 'a2z', m )
        else:
            self.pump.write("dump")

    def env_delay(self, d):
        # first send this to the emulated wrapper
        self.sim_channels['z2a'].write( ('A2W', ('delay', d)) )
        assert waits(self.sim_pump, self.sim_channels['a2z']).msg == 'OK'

        # now send it to the ideal world wrapper
        self.write( 'a2w', ('A2W', ('delay',d)) )
        assert waits(self.pump, self.channels['w2a']).msg == 'OK'

        self.pump.write("dump")

    def env_msg(self, d):
        msg = d.msg
        imp = d.imp
        if msg[0] == 'A2F':
            t,msg = msg
            #self.tick(1)
            self.channels['a2f'].write( msg, imp )
        elif msg[0] == 'A2P':
            t,msg = msg
            #self.tick(1)
            self.channels['a2p'].write( msg, imp )
        elif msg[0] == 'A2W':
            t,msg = msg
            print('A2W msg', msg)
            if msg[0] == 'get-leaks':
                self.env_get_leaks()
            elif msg[0] == 'exec':
                self.env_exec(self, r, idx)
            elif msg[0] == 'delay':
                self.env_delay(self, d)
            else:
                #self.tick(1)
                self.channels['a2w'].write( msg, imp )
        elif msg[0] == 'corrupt':
            self.input_corrupt(msg[1])
        else:
            #dump.dump()
            self.pump.write("dump")

    def wrapper_poll(self):
        self.internal_delay -= 1
        print("YAY")
        #self.write( 'a2z', ('YAY',))
        # simulate the 'poll' call
        self.sim_channels['z2w'].write( ('poll',) )
        m = waits(self.sim_pump, self.sim_channels['a2z'])
        assert m.msg == ('poll',)
        self.pump.write( m.msg, m.imp)

    def wrapper_msg(self, d):
        msg = d.msg
        imp = d.imp
        #self.tick(1)

        if msg[0] == 'poll':
            self.wrapper_poll()
        else:
            self.channels['a2z'].write( msg, imp )
        #dump.dump()

    def func_msg(self, d):
        msg = d.msg
        imp = d.imp
        self.channels['a2z'].write( msg, imp )



from itm import WrappedPartyWrapper, PartyWrapper
from adversary import DummyWrappedAdversary
from syn_ours import Syn_FWrapper
from exuc import execWrappedUC
def env1(static, z2p, z2f, z2a, z2w, a2z, p2z, f2z, w2z, pump):
    n = 3
    sid = ('one', (1,2,3), 3)
    static.write( ('sid', sid) )

    z2p.write( ((sid,1), ('input',1)), n*(4*n + 1) )
    waits(pump, a2z)#wait_for(a2z)

    z2a.write( ('A2W', ('get-leaks',)) )
    m = waits(a2z, pump)#wait_for(a2z)

#    z2w.write( ('poll',) )
#    m = wait_for(a2z).msg; assert m == ('poll',), str(m)
#    z2w.write( ('poll',) )
#    wait_for(a2z)
#    z2w.write( ('poll',) )
#    wait_for(a2z)
#
#    z2a.write( ('A2W', ('callme', 3)) )
#    m = wait_for(a2z).msg; assert m == ('OK',)
#    z2w.write( ('poll',) )
#    m = wait_for(a2z).msg; assert m == ('shoutout',)
#
#    z2a.write( ('A2W', ('exec', 6, 1)) ) 
#    m = wait_for(p2z).msg
#    assert m[1] == 1, str(m)


if __name__=='__main__':
    #execWrappedUC(env1, [('F_bracha',Syn_Bracha_Functionality)], PartyWrapper, Syn_FWrapper, 'F_bracha', DummyWrappedAdversary)
    execWrappedUC(env1, [('F_bracha',Syn_Bracha_Functionality)], WrappedPartyWrapper, Syn_FWrapper, 'F_bracha', RBC_Simulator)

