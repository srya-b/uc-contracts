from itm import ProtocolWrapper, WrappedProtocolWrapper, WrappedPartyWrapper, wrappedPartyWrapper, wrappedProtocolWrapper
from adversary import DummyWrappedAdversary
from async_ours import Async_FWrapper, Async_Channel, Async_Bracha_Protocol
from async_ours.f_bracha import Async_RBC_Simulator, Async_Bracha_Functionality, asyncBrachaSimulator
#from execuc import execWrappedUC
from execuc import execWrappedUC
from utils import z_get_leaks, waits
import logging
import gevent
from numpy.polynomial.polynomial import Polynomial

log = logging.getLogger(__name__)
logging.basicConfig( level=50 )

def env1(static, z2p, z2f, z2a, z2w, a2z, p2z, f2z, w2z, pump):
    delta = 3
    n = 3
    sid = ('one', tuple(range(1,n+1)), delta)
    static.write( (('sid', sid), ('crupt',)) )

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

    z2p.write( ((sid,1), ('input', 2)), n*(4*n + 1))
    waits(pump)

    def channel_id(fro, to, r):
        s = ('one', (sid,fro), (sid,to), r, delta)
        return (s,'F_chan')

    z2a.write( ('A2W', ('get-leaks',)), n*(4*n+1))
    waits(pump)

    for _ in range(4):
        z2w.write( ('poll',), 1 )
        waits(pump)

    for _ in range(3):
        z2w.write( ('poll',), 1)
        waits(pump)

    for _ in range(3):
        z2w.write( ('poll',), 1)
        waits(pump)

    for _ in range(1):
        z2w.write( ('poll',), 1)
        waits(pump)

    for _ in range(3):
        z2w.write( ('poll',), 1)
        waits(pump)

    for _ in range(3):
        z2w.write( ('poll',), 1)
        waits(pump)

    for _ in range(3):
        z2w.write( ('poll',), 1)
        waits(pump)

    z2a.write( ('A2W', ('delay', 3)), 3)
    waits(pump)

    for _ in range(4):
        z2w.write( ('poll',), 1)
        waits(pump)

    z2w.write( ('poll',), 1)
    waits(pump)

    z2w.write( ('poll',), 1)
    waits(pump)

    z2w.write( ('poll',), 1)
    waits(pump)

    z2w.write( ('poll',), 1)
    waits(pump)

    z2w.write( ('poll',), 1)
    waits(pump)

    z2w.write( ('poll',), 1)
    waits(pump)

    z2w.write( ('poll',), 1)
    waits(pump)

    gevent.kill(g1)
    gevent.kill(g2)

    print('Transcript', transcript)
    return transcript

def distinguisher(t_ideal, t_real):
    print('\n\t\033[93m Ideal transcript\033[0m')
    for i in t_ideal: print(i)

    print('\n\t\033[93m real transcript\033[0m')
    for i in t_real: print(i)

    if t_ideal == t_real:
        print("\033[92m[Distinguisher] They're the same\033[0m")
    else:
        print("\033[91m[Distinguisher] They're different\033[0m")

if __name__=='__main__':
    print('\n\t\t\033[93m [IDEAL WORLD] \033[0m\n')
    t1 = execWrappedUC(
        env1, 
        [('F_bracha',Async_Bracha_Functionality)], 
        wrappedPartyWrapper('F_bracha'),
        Async_FWrapper, 
        asyncBrachaSimulator(Async_Bracha_Protocol),
        poly=Polynomial([100,2,3,4,5,6])
    )
    
    print('\n\t\t\033[93m [REAL WORLD] \033[0m\n')
    t2 = execWrappedUC(
        env1,  
        [('F_chan',Async_Channel)], 
        wrappedProtocolWrapper(Async_Bracha_Protocol),
        Async_FWrapper, 
        DummyWrappedAdversary, 
        poly=Polynomial([100,2,3,4,5,6,7])
    )

    distinguisher(t1, t2)
