from uc.utils import waits
import logging
import gevent
from numpy.polynomial.polynomial import Polynomial

log = logging.getLogger(__name__)
logging.basicConfig( level=1)

def env1(k, static, z2p, z2f, z2a, z2w, a2z, p2z, f2z, w2z, pump):
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
    
    def channel_id(fro, to, r):
        s = ('one', (sid,fro), (sid,to), r, delta)
        return (s,'F_chan')

    z2p.write( ((sid,1), ('input', 2)), n*(4*n + 1))
    waits(pump)

    z2a.write( ('A2W', ('get-leaks',), 0))
    waits(pump)

    log.debug('\033[91m send first VAL, get +2 ECHO messages \033[0m')
    i = 1
    for _ in range(4):
        print('Poll #{}'.format(i))
        i+=1
        z2w.write( ('poll',), 1 )
        waits(pump)

    log.debug('\033[91m +2 ECHO + 1 = 3 polls to send next VAL message +2 ECHO msgs \033[0m')
    i = 1
    for _ in range(3):
        print('Poll #{}'.format(i))
        i+=1
        z2w.write( ('poll',), 1)
        waits(pump)

    log.debug('\033[91m +2 ECHO + 1 = 3 polls to send last VAL message +2 ECHO msgs \033[0m')
    i=1
    for _ in range(3):
        print('Poll #{}'.format(i))
        i+=1
        z2w.write( ('poll',), 1)
        waits(pump)

    log.debug('\033[91m +2 ECHO +1 = 3 polls to send 1 -> 2 ECHO msg, +2 READY msgs \033[0m')
    i=1
    for _ in range(3):
        print('Poll #{}'.format(i))
        i+=1
        z2w.write( ('poll',), 1)
        waits(pump)

    log.debug('\033[91m +2 READY +1 = 3 polls to send 1 -> 3 ECHO msg, +2 READY msgs \033[0m')
    i=1
    for _ in range(3):
        print('Poll #{}'.format(i))
        i+=1
        z2w.write( ('poll',), 1)
        waits(pump)

    log.debug('\033[91m +2 READY +1 = 3 polls to send 2 -> 1 ECHO msg, +2 READY msgs \033[0m')
    i=1
    for _ in range(3):
        print('Poll #{}'.format(i))
        i+=1
        z2w.write( ('poll',), 1)
        waits(pump)

    log.debug('\033[91m +2 READY +1 = 3 polls to send 2 -> 3 ECHO msg, +0 READY msgs \033[0m')
    i=1
    for _ in range(3):
        print('Poll #{}'.format(i))
        i+=1
        z2w.write( ('poll',), 1)
        waits(pump)

    log.debug('\033[91m DELAYING \033[0m')
    z2a.write( ('A2W', ('delay', 3), 3), 3)
    waits(pump)

    log.debug('\033[91m +0 READY +1 = 3 polls to send 3 -> 1 ECHO msg, +0 msgs \033[0m')
    i=1
    for _ in range(4):
        print('Poll #{}'.format(i))
        i+=1
        z2w.write( ('poll',), 1)
        waits(pump)

    log.debug('\033[91m +0 READY +1 = 3 polls to send 3 -> 2 ECHO msg, +0 msgs \033[0m')
    z2w.write( ('poll',), 1)
    waits(pump)

    log.debug('\033[91m +0 READY +1 = 3 polls to send 2 -> 1 READY msg, +0 msgs \033[0m')
    z2w.write( ('poll',), 1)
    waits(pump)

    log.debug('\033[91m +0 READY +1 = 3 polls to send 2 -> 3 READY msg, +0 msgs \033[0m')
    z2w.write( ('poll',), 1)
    waits(pump)

    log.debug('\033[91m +0 READY +1 = 3 polls to send 3 -> 1 READY msg, 1 ACCEPTS\033[0m')
    z2w.write( ('poll',), 1)
    waits(pump)

    log.debug('\033[91m +0 READY +1 = 3 polls to send 3 -> 2 READY msg, 2 Doesnt accept \033[0m')
    z2w.write( ('poll',), 1)
    waits(pump)

    log.debug('\033[91m +0 READY +1 = 3 polls to send 1 -> 2 READY msg, 2 ACCEPTS\033[0m')
    z2w.write( ('poll',), 1)
    waits(pump)

    #log.debug('\033[91m +0 READY +1 = 3 polls to send 1 -> 3 READY msg, 3 ACCEPTS\033[0m')
    #z2w.write( ('poll',), 1)
    #waits(pump)

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

from uc.itm import ProtocolWrapper, WrappedProtocolWrapper, WrappedPartyWrapper, wrappedPartyWrapper, wrappedProtocolWrapper
from uc.adversary import DummyWrappedAdversary
from uc.syn_ours import Syn_FWrapper, Syn_Channel
from prot_bracha import Syn_Bracha_Protocol
from f_bracha import Syn_Bracha_Functionality
from sim_bracha import RBC_Simulator, brachaSimulator
from uc.execuc import execWrappedUC

if __name__=='__main__':
    print('\n\t\t\033[93m [IDEAL WORLD] \033[0m\n')
    print('env1 type', type(env1))
    t1 = execWrappedUC(
        128,
        env1, 
        [('F_bracha',Syn_Bracha_Functionality)], 
        wrappedPartyWrapper('F_bracha'),
        Syn_FWrapper, 
        brachaSimulator(Syn_Bracha_Protocol),
        poly=Polynomial([100,2,3,4,5,6])
    )

    
    print('\n\t\t\033[93m [REAL WORLD] \033[0m\n')
    t2 = execWrappedUC(
        128,
        env1,  
        [('F_chan',Syn_Channel)], 
        wrappedProtocolWrapper(Syn_Bracha_Protocol),
        Syn_FWrapper, 
        DummyWrappedAdversary, 
        poly=Polynomial([100,2,3,4,5,6,7])
    )

    distinguisher(t1, t2)
