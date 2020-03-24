import dump
from itm import UCWrappedFunctionality
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

    def party_msg(self, msg):
        print('Party msg in bracha', msg)
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
    z2w.write( ('poll',) )
    wait_for(a2z)
    z2w.write( ('poll',) )
    wait_for(a2z)

    z2a.write( ('A2W', ('callme', 3)) )
    m = wait_for(a2z).msg; assert m == ('OK',)
    z2w.write( ('poll',) )
    m = wait_for(a2z).msg; assert m == ('shoutout',)

    z2a.write( ('A2W', ('exec', 6, 1)) ) 
    m = wait_for(p2z).msg
    assert m[1] == 1, str(m)


if __name__=='__main__':
    execWrappedUC(env1, [('F_bracha',Syn_Bracha_Functionality)], PartyWrapper, Syn_FWrapper, 'F_bracha', DummyWrappedAdversary)

