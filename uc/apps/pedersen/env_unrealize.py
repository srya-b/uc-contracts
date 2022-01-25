
from uc.utils import waits, collectOutputs
import os
import gevent
import secp256k1 as secp

def env_crupt_committer(k, static, z2p, z2f, z2a, a2z, f2z, p2z, pump):
    sid = ('one', "1, 2")
    static.write( (('sid',sid), ('crupt', 1)))

    transcript = []

    def _p2z():
        while True:
            m = waits(p2z)
            transcript.append('p2z: ' + str(m))
            pump.write('dump')

    g2 = gevent.spawn(_p2z)


    # TODO: control the corrupt committer

    gevent.kill(g2)
    
    print('\ntranscript:\n\t{}'.format(transcript))
    return transcript

def env_crupt_receiver(k, static, z2p, z2f, z2a, a2z, f2z, p2z, pump):
    sid = ('one', "1, 2")
    static.write( (('sid',sid), ('crupt', 2)))

    transcript = []

    def _p2z():
        while True:
            m = waits(p2z)
            transcript.append('p2z: ' + str(m))
            pump.write('dump')

    g2 = gevent.spawn(_p2z)

    # TODO (optional): do the receiver portion too (it's trivial)

    gevent.kill(g2)
    
    print('\ntranscript:\n\t{}'.format(transcript))
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
from f_crs import F_CRS
from f_mcom import F_Mcom
from sim_mcom import Sim_Mcom
from prot_com import Commitment_Prot

print('\nreal\n')
treal = execUC(
    128,
    env_crupt_receiver,
    F_CRS,
    Commitment_Prot,
    DummyAdversary
)

print('\nideal\n')
tideal = execUC(
    128,
    env_crupt_receiver,
    F_Mcom,
    DummyParty,
    Sim_Mcom
) 

distinguisher(tideal, treal)
