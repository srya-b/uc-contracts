from uc.utils import waits
import gevent

def env(k, static, z2p, z2f, z2a, a2z, f2z, p2z, pump):
    sid = ('one', "1, 2")
    static.write( (('sid',sid), ('crupt',)))

    transcript = []
    def _a2z():
        while True:
            m = waits(a2z)
            transcript.append('a2z: ' + str(m))
            pump.write('dump')

    def _p2z():
        while True:
            m = waits(p2z)
            transcript.append('p2z: ' + str(m))
            pump.write('dump')

    g1 = gevent.spawn(_a2z)
    g2 = gevent.spawn(_p2z)
   
    z2p.write( (1, ('flip',)) )
    waits(pump)

    z2p.write( (1, ('getflip',)) )
    waits(pump)

    z2p.write( (2, ('getflip',)) )
    waits(pump)

    gevent.kill(g1)
    gevent.kill(g2)

    print('transcript', transcript)
    return transcript

def env_flipper_crupt(k, static, z2p, z2f, z2a, a2z, f2z, p2z, pump):
    sid = ('one', "1, 2")
    static.write( (('sid',sid), ('crupt', 1)))

    transcript = []

    def _p2z():
        while True:
            m = waits(p2z)
            transcript.append('p2z: ' + str(m))
            print('p2z: ' + str(m))
            pump.write('dump')

    def adda2z(m):
        print('a2z: ' + str(m))
        transcript.append('a2z: ' + str(m))

    g2 = gevent.spawn(_p2z)

    z2a.write( ('A2F', ('hash', (123, 0))) )
    m = waits(a2z)
    adda2z(m)
    _,lasthash = m
    
    z2a.write( ('A2P', (1, ('sendmsg', 2, ('commit', lasthash)))) )
    m = waits(a2z)
    adda2z(m)

    z2a.write( ('A2P', (1, ('sendmsg', 2, 'yoyoyoy'))) )
    waits(pump)

    z2p.write( (2, ('getflip',)) )
    waits(pump)

    z2a.write( ('A2P', (1, ('sendmsg', 2, ('open', (123, 0))))) )
    waits(pump)

    z2p.write( (2, ('getflip',)) )
    waits(pump)

    gevent.kill(g2)

    return transcript

def env_flipper_crupt_bad_open(k, static, z2p, z2f, z2a, a2z, f2z, p2z, pump):
    sid = ('one', "1, 2")
    static.write( (('sid',sid), ('crupt', 1)))

    transcript = []

    def _p2z():
        while True:
            m = waits(p2z)
            transcript.append('p2z: ' + str(m))
            print('p2z: ' + str(m))
            pump.write('dump')

    def adda2z(m):
        print('a2z: ' + str(m))
        transcript.append('a2z: ' + str(m))

    g2 = gevent.spawn(_p2z)

    z2a.write( ('A2F', ('hash', (123, 0))) )
    m = waits(a2z)
    adda2z(m)
    _,lasthash = m
    
    z2a.write( ('A2P', (1, ('sendmsg', 2, ('commit', lasthash)))) )
    m = waits(a2z)
    adda2z(m)

    z2a.write( ('A2P', (1, ('sendmsg', 2, 'yoyoyoy'))) )
    waits(pump)

    z2p.write( (2, ('getflip',)) )
    waits(pump)

    z2a.write( ('A2P', (1, ('sendmsg', 2, ('open', (123, 1))))) )
    waits(pump)

    z2p.write( (2, ('getflip',)) )
    waits(pump)


    gevent.kill(g2)

    return transcript


def distinguisher(t_ideal, t_real):
    print('\n\t\033[93m Ideal transcript\033[0m')
    for i in t_ideal: print(str(i))

    print('\n\t\033[93m real transcript\033[0m')
    for i in t_real: print(str(i))

    if t_ideal == t_real:
        print("\033[92m[Distinguisher] They're the same\033[0m")
    else:
        print("\033[91m[Distinguisher] They're different\033[0m")

from uc.protocol import protocolWrapper, DummyParty
from uc import compose, sim_compose, execUC
from uc.apps.coinflip import Flip_Prot, F_Flip, Sim_Flip
from uc.apps.commitment import Commitment_Prot, Random_Oracle_and_Chan, Sim_Com
from uc.adversary import DummyAdversary

print('TReal \n')

treal = execUC(
    128,
    env_flipper_crupt_bad_open,
    Random_Oracle_and_Chan,
    compose(Flip_Prot, Commitment_Prot),
    DummyAdversary
)
print('\nTIdeal\n')

tideal = execUC(
    128,
    env_flipper_crupt_bad_open,
    F_Flip,
    DummyParty,
    sim_compose(Sim_Com, Sim_Flip)
)

distinguisher(tideal, treal)
