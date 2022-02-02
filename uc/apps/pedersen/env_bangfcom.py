from uc.utils import waits, collectOutputs
import os
import gevent
import secp256k1 as secp

def env_honest(k, static, z2p, z2f, z2a, a2z, f2z, p2z, pump):
    print('\033[94m[ env_honest ]\033[0m')

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

    for i in range(2):
        m = secp.uint256_from_str(os.urandom(32))
        print('\n commiting to the point: \n\t{}\n'.format(m))

        z2p.write( (1, ((str(i), "1,2"), ('commit', m))) )
        waits(pump)

    for i in range(2):
        z2p.write( (1, ((str(i), "1,2"),('reveal',))) )
        waits(pump)
    
    gevent.kill(g1)
    gevent.kill(g2)
    
    print('transcript', transcript)
    return transcript

def distinguisher(t_ideal, t_real):
    print('\n\t\033[93m ideal transcript\033[0m')
    for i in t_ideal: print(str(i))

    print('\n\t\033[93m real transcript\033[0m')
    for i in t_real: print(str(i))

    if t_ideal == t_real:
        print("\033[92m[distinguisher] they're the same\033[0m")
    else:
        print("\033[91m[distinguisher] they're different\033[0m")


from uc.adversary import DummyAdversary
from uc.protocol import DummyParty
from uc.execuc import execUC
from f_mcrs import F_MCRS
from f_com import F_com
from uc.multisession import bangP, bangF
from prot_com import Commitment_Prot

print('\nreal\n')
treal = execUC(
    128,
    env_honest,
    F_MCRS,
    bangP(Commitment_Prot),
    DummyAdversary
)

print('\nideal\n')
tideal = execUC(
    128,
    env_honest,
    bangF(F_com),
    DummyParty,
    DummyAdversary
)

distinguisher(tideal, treal)
