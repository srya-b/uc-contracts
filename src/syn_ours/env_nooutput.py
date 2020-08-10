from itm import ProtocolWrapper, WrappedProtocolWrapper, WrappedPartyWrapper, wrappedPartyWrapper, wrappedProtocolWrapper
from adversary import DummyWrappedAdversary
from syn_ours import Syn_FWrapper, Syn_Channel, Syn_Bracha_Protocol#, RBC_Simulator, Syn_Bracha_Functionality
from syn_ours.f_bracha import Syn_Bracha_Functionality, RBC_Simulator, brachaSimulator
from syn_ours.broken_prot_bracha import Broken_Bracha_Protocol
from execuc import execWrappedUC
from utils import z_get_leaks, waits
import logging
import gevent
from numpy.polynomial.polynomial import Polynomial

log = logging.getLogger(__name__)
logging.basicConfig( level="DEBUG")

def env(k, static, z2p, z2f, z2a, z2w, a2z, p2z, f2z, w2z, pump):
    delta = 3
    n = 4
    sid = ('one', tuple(range(1,n+1)), delta)
    static.write( (('sid', sid), ('crupt',(sid,1), (sid,10))) )

    transcript = []
    def _a2z():
        while True:
            m = waits(a2z)
            transcript.append('a2z: ' + str(m.msg))
            pump.write('dump')

    def _p2z():
        while True:
            m = waits(p2z)
            transcript.append('p2z: ' + str(m.msg))
            pump.write('dump')

    g1 = gevent.spawn(_a2z)
    g2 = gevent.spawn(_p2z)

    def t(s):
        transcript.append('cmd: ' + str(s))

    def channel_id(fro, to, r):
        s = ('one', (sid,fro), (sid,to), r, delta)
        return (s,'F_chan')
    
    z2a.write( ('A2P', ((sid,1), ('P2F', ((channel_id(1,2,1)), ('send', ('VAL', 1))))), 4*n), 4*n)
    waits(pump)
    z2a.write( ('A2P', ((sid,1), ('P2F', ((channel_id(1,3,1)), ('send', ('VAL', 1))))), 4*n), 4*n)
    waits(pump)

    z2a.write( ('A2W', ('get-leaks',), n*(4*n+1)), n*(4*n+1))
    waits(pump)

    for _ in range(4):
        z2w.write( ('poll',), 1)
        waits(pump)

    z2a.write( ('A2P', ((sid,1), ('P2W', ('clock-round',))), 0) )
    waits(pump)

    z2a.write( ('A2W', ('exec', 4, 0), 0) )
    waits(pump)

    for _ in range(6):
        z2a.write( ('A2W', ('exec', 7, 0), 0) )
        waits(pump)

    z2a.write( ('A2P', ((sid,1), ('P2F', ((channel_id(1,2,7)), ('send', ('ECHO',1))))), 3), 3)
    waits(pump)
    z2a.write( ('A2P', ((sid,1), ('P2F', ((channel_id(1,3,7)), ('send', ('ECHO',1))))), 3), 3)
    waits(pump)

    for _ in range(3):
        z2w.write( ('poll',), 1)
        waits(pump)

    for _ in range(8):
        z2a.write( ('A2W', ('exec', 7 , 0), 0) )
        waits(pump)

    z2a.write( ('A2P', ((sid,1), ('P2F', ((channel_id(1,2,7)), ('send', ('READY',1))))), 0), 0)
    waits(pump)

    z2a.write( ('A2W', ('exec', 7 , 0), 0) )
    waits(pump)

    z2a.write( ('A2P', ((sid,1), ('P2F', ((channel_id(1,3,7)), ('send', ('READY',1))))), 0), 0)
    waits(pump)

    z2a.write( ('A2W', ('exec', 7 , 0), 0) )
    waits(pump)

    for _ in range(77):
        z2w.write( ('poll',), 1)
        waits(pump)
    
    gevent.kill(g1)
    gevent.kill(g2)

    return transcript


def distinguisher(t_ideal, t_real):
    print('\n\t\033[93m \033[1m[Ideal Transcript] \033[0m')
    for i in t_ideal: print(i)

    print('\n\t\033[93m \033[1m [Real Transcript] \033[0m')
    for i in t_real: print(i)

    if t_ideal == t_real:
        print("\033[92m[Distinguisher] They're the same\033[0m")
    else:
        print("\033[91m[Distinguisher] They're different\033[0m")

if __name__=='__main__':
    print('\n\t\t\033[93m [IDEAL WORLD] \033[0m\n')
    t1 = execWrappedUC(
        128,
        env,
        [('F_bracha',Syn_Bracha_Functionality)],
        wrappedPartyWrapper('F_bracha'),
        Syn_FWrapper, 
        brachaSimulator(Broken_Bracha_Protocol),
        poly=Polynomial([100,2,3,4,5,6,7])
    )
 
    print('\n\t\t\033[93m [REAL WORLD] \033[0m\n')
    t2 = execWrappedUC(
        128,
        env, 
        [('F_chan',Syn_Channel)], 
        wrappedProtocolWrapper(Broken_Bracha_Protocol),
        Syn_FWrapper, 
        DummyWrappedAdversary, 
        poly=Polynomial([100,2,3,4,5,6,7])
    )

    distinguisher(t1, t2)
