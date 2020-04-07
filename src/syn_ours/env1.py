from itm import ProtocolWrapper, WrappedProtocolWrapper, WrappedPartyWrapper
from adversary import DummyWrappedAdversary
from syn_ours import Syn_FWrapper, Syn_Channel, Syn_Bracha_Protocol, RBC_Simulator, Syn_Bracha_Functionality
#from execuc import execWrappedUC
from exuc import execWrappedUC
from utils import z_get_leaks, waits

def env1(static, z2p, z2f, z2a, z2w, a2z, p2z, f2z, w2z, pump):
    delta = 3
    n = 3
    #sid = ('one', (1,2,3), delta)
    sid = ('one', tuple(range(1,n+1)), delta)
    static.write( ('sid', sid) )

    z2p.write( ((sid,1), ('input', 2)), n*(4*n + 1) )
    #wait_for(p2z)
    waits(pump, p2z)

    def channel_id(fro, to, r):
        s = ('one', (sid,fro), (sid,to), r, delta)
        return (s,'F_chan')

    z2a.write( ('A2W', ('get-leaks',)) )
    msgs = waits(pump, a2z)
    print('\033[91m [Leaks] \033[0m', '\n'.join(str(m) for m in msgs.msg))

    z2w.write( ('poll',) )
    print('\n**\n', waits(pump, a2z))

if __name__=='__main__':
    print('\n\t\t\033[1m [IDEAL WORLD] \033[0m\n')
    execWrappedUC(env1, [('F_bracha',Syn_Bracha_Functionality)], WrappedPartyWrapper, Syn_FWrapper, 'F_bracha', RBC_Simulator)
    print('\n\t\t\033[1m [REAL WORLD] \033[0m\n')
    execWrappedUC(env1, [('F_chan',Syn_Channel)], WrappedProtocolWrapper, Syn_FWrapper, Syn_Bracha_Protocol, DummyWrappedAdversary)
