from uc.utils import waits, collectOutputs
import gevent

def env(k, static, z2p, z2f, z2a, a2z, f2z, p2z, pump):
    sid = ('one', 1, 2)
    static.write( (('sid',sid), ('crupt',)))

    transcript = []
    def _a2z():
        while True:
            m = waits(a2z)
            transcript.append('a2z: ' + str(m))
            print('a2z: ' + str(m))
            pump.write('dump')

    def _p2z():
        while True:
            m = waits(p2z)
            transcript.append('p2z: ' + str(m))
            print('p2z: ' + str(m))
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

    return transcript

def env_flipper_crupt(k, static, z2p, z2f, z2a, a2z, f2z, p2z, pump):
    sid = ('one', 1, 2)
    static.write( (('sid',sid), ('crupt', 1)))

    transcript = []
    def _a2z():
        while True:
            m = waits(a2z)
            transcript.append('a2z: ' + str(m))
            print('a2z: ' + str(m))
            pump.write('dump')

    def _p2z():
        while True:
            m = waits(p2z)
            transcript.append('p2z: ' + str(m))
            print('p2z: ' + str(m))
            pump.write('dump')

    g1 = gevent.spawn(_a2z)
    g2 = gevent.spawn(_p2z)

    z2a.write( ('A2P', (1, ('commit', 1))) )
    waits(pump)

    z2p.write( (2, ('getflip',)) )
    waits(pump)
    
    z2a.write( ('A2P', (1, ('sendmsg', ('yoyoyoy',)))) )
    waits(pump)

    z2p.write( (2, ('sendmsg', ('titititititit',))) )
    waits(pump)

    z2p.write( (2, ('getflip',)) )
    waits(pump)

    z2a.write( ('A2P', (1, ('reveal',))) )
    waits(pump)

    z2p.write( (2, ('getflip',)) )
    waits(pump)

    gevent.kill(g1)
    gevent.kill(g2)

    return transcript

def env_flipper_crupt_no_open(k, static, z2p, z2f, z2a, a2z, f2z, p2z, pump):
    sid = ('one', 1, 2)
    static.write( (('sid',sid), ('crupt', 1)))

    transcript = []
    def _a2z():
        while True:
            m = waits(a2z)
            transcript.append('a2z: ' + str(m))
            print('a2z: ' + str(m))
            pump.write('dump')

    def _p2z():
        while True:
            m = waits(p2z)
            transcript.append('p2z: ' + str(m))
            print('p2z: ' + str(m))
            pump.write('dump')

    g1 = gevent.spawn(_a2z)
    g2 = gevent.spawn(_p2z)

    z2a.write( ('A2P', (1, ('commit', 1))) )
    waits(pump)

    z2p.write( (2, ('getflip',)) )
    waits(pump)
    
    z2a.write( ('A2P', (1, ('sendmsg', ('yoyoyoy',)))) )
    waits(pump)

    z2p.write( (2, ('sendmsg', ('titititititit',))) )
    waits(pump)

    z2p.write( (2, ('getflip',)) )
    waits(pump)

    #z2a.write( ('A2P', (1, ('reveal',))) )
    #waits(pump)

    z2p.write( (2, ('getflip',)) )
    waits(pump)

    gevent.kill(g1)
    gevent.kill(g2)

    return transcript

def env_receiver_crupt(k, static, z2p, z2f, z2a, a2z, f2z, p2z, pump):
    sid = ('one', 1, 2)
    static.write( (('sid',sid), ('crupt', 2)))

    transcript = []
    def _a2z():
        while True:
            m = waits(a2z)
            transcript.append('a2z: ' + str(m))
            print('a2z: ' + str(m))
            pump.write('dump')

    def _p2z():
        while True:
            m = waits(p2z)
            transcript.append('p2z: ' + str(m))
            print('p2z: ' + str(m))
            pump.write('dump')

    g1 = gevent.spawn(_a2z)
    g2 = gevent.spawn(_p2z)

    z2a.write( ('A2P', (2, ('sendmsg', ('is this a real message',)))) )
    waits(pump)

    z2p.write( (1, ('flip',)) )
    waits(pump)

    z2p.write( (1, ('sendmsg', ('yea this is the honest message',))) )
    waits(pump)

    z2a.write( ('A2P', (2, ('sendmsg', ('notbit', 1)))) )
    waits(pump)

    z2p.write( (1, ('getflip',)) )
    waits(pump)

    z2a.write( ('A2P', (2, ('sendmsg', ('bit', 1)))) )
    waits(pump)

    z2p.write( (1, ('getflip',)) )
    waits(pump)

    gevent.kill(g1)
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

    

from uc.apps.coinflip import F_Flip, Flip_Prot, Sim_Flip
from uc.apps.commitment import F_Com_Channel
from uc.adversary import DummyAdversary
from uc import execUC
from uc.protocol import protocolWrapper, DummyParty


print('\n real \n')

treal = execUC(
    128,
    env_flipper_crupt_no_open,
    F_Com_Channel,
    Flip_Prot,
    DummyAdversary
)

print('\n ideal \n')

tideal = execUC(
    128,
    env_flipper_crupt_no_open,
    F_Flip,
    DummyParty,
    Sim_Flip
)

distinguisher(tideal, treal)
