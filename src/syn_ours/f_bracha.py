import dump
from itm import UCWrappedFunctionality, ITM
from utils import wait_for

class Syn_Bracha_Functionality(UCWrappedFunctionality):
    def __init__(self, sid, pid, channels):
        self.ssid = sid[0]
        self.parties = sid[1]
        UCWrappedFunctionality.__init__(self, sid, pid, channels)

    def send_output(self, to, msg):
        self.f2p.write( (to, msg) )

    '''Dealer, assumed to be pid=1 gives some input and invokes
    the synchronous wrapper around it to deliver the output to all
    of the parties in O(1) time.'''
    def party_input(self, pid, inp):
        if pid == 1:
            for p in self.parties:
                self.f2w.write( ('schedule', self.send_output, (p, inp), 5) )
                m = wait_for(self.w2f).msg
                assert m == ('OK',)
        dump.dump() 

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
        else: dump.dump()

    def wrapper_msg(self, msg):
        dump.dump()
    def adv_msg(self, msg):
        dump.dump()
    def env_msg(self, msg):
        dump.dump()

from itm import ProtocolWrapper
from execuc import createWrappedUC
from syn_ours import Syn_Channel, Syn_Bracha_Protocol
class RBC_Simulator(ITM):
    def __init__(self, sid, pid, channels):
        self.ssid = sid[0]
        self.parties = sid[1]
        #self.delta = sid[2]

        self.sim_channels,static = createWrappedUC([('F_chan',Syn_Channel)], ProtocolWrapper, Syn_FWrapper, Syn_Bracha_Protocol, DummyWrappedAdversary)
        static.write( ('sid', sid) )

        print('ID', channels['w2a'].i)
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

        self.sim_channels['z2p'].write( ('

    def sim_party_msg(self, d):
        dump.dump()

    def sim_adv_msg(self, d):
        dump.dump()
    
    def sim_func_msg(self, d):
        dump.dump()

    def sim_wrapper_msg(self, d):
        dump.dump()

    def party_msg(self, d):
        msg = d.msg
        imp = d.imp
        self.channels['a2z'].write( msg, imp)
    
    def env_msg(self, d):
        msg = d.msg
        imp = d.imp
        if msg[0] == 'A2F':
            t,msg = msg
            if msg[0] == 'get-leaks':
                self.get_leaks(msg[1])
            else:
                self.channels['a2f'].write( msg, imp )
        elif msg[0] == 'A2P':
            t,msg = msg
            self.channels['a2p'].write( msg, imp )
        elif msg[0] == 'A2W':
            t,msg = msg
            print('A2W msg', msg)
            self.a2w.write( msg, imp )
        elif msg[0] == 'corrupt':
            self.input_corrupt(msg[1])
        else:
            dump.dump()

    def wrapper_msg(self, d):
        msg = d.msg
        imp = d.imp
        self.channels['a2z'].write( msg, imp )
        #dump.dump()

    def func_msg(self, d):
        msg = d.msg
        imp = d.imp
        self.channels['a2z'].write( msg, imp )



from itm import PartyWrapper
from adversary import DummyWrappedAdversary
from syn_ours import Syn_FWrapper
from execuc import execWrappedUC
def env1(static, z2p, z2f, z2a, z2w, a2z, p2z, f2z, w2z):
    sid = ('one', (1,2,3))
    static.write( ('sid', sid) )

    z2p.write( ((sid,1), ('input',1)) )
    wait_for(a2z)

    z2w.write( ('poll',) )
    m = wait_for(a2z).msg; assert m == ('poll',), str(m)
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
    execWrappedUC(env1, [('F_bracha',Syn_Bracha_Functionality)], PartyWrapper, Syn_FWrapper, 'F_bracha', RBC_Simulator)

