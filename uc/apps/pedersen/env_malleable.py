from uc.utils import waits, collectOutputs
import os
import gevent
import secp256k1 as secp

def env_crupt_receiver_malleability(k, static, z2p, z2f, z2a, a2z, f2z, p2z, pump):
    sid = ('one', "1, 2")
    static.write( (('sid',sid), ('crupt', 2)))

    transcript = []

    def _p2z():
        while True:
            m = waits(p2z)
            transcript.append('p2z: ' + str(m))
            pump.write('dump')

    g2 = gevent.spawn(_p2z)

    m = secp.uint256_from_str(os.urandom(32))
   
    z2p.write( (1, ('commit', 1, m)) )
    msg = waits(a2z)
    transcript.append('a2z: ' + str(msg))
    _,(fro,(_,_,(_,cid,commitment))) = msg

    z2a.write( ('A2P', (2, ('value',))) )
    msg = waits(a2z)
    transcript.append('a2z: ' + str(msg))
    _,(fro,((g,h),)) = msg

    commitmentplus1 = commitment + g

    z2p.write( (1, ('reveal', 1)) )
    msg = waits(a2z)
    transcript.append('a2z: ' + str(msg))
    _,(fro,(_,_,(_,cid,msg,randomness))) = msg

    checkcommitmentplus1 = (g * (msg+1)) + (h * randomness)

    print('\nPredicted Commitment:\n\t{}'.format(commitmentplus1))
    print('\nActual commitment of m+1 given committer randomness:\n\t{}'.format(checkcommitmentplus1))

    gevent.kill(g2)
    
    print('\ntranscript:\n\t{}'.format(transcript))
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

from uc.adversary import DummyAdversary
from uc.protocol import DummyParty
from uc.execuc import execUC
from f_crs import F_CRS
from f_mcom import F_Mcom
from sim_mcom import Sim_Mcom
from prot_com import Commitment_Prot

treal = execUC(
    128,
    env_crupt_committer,
    F_CRS,
    Commitment_Prot,
    DummyAdversary
)

tideal = execUC(
    128,
    env_crupt_committer,
    F_Mcom,
    DummyParty,
    Sim_Mcom
) 

distinguisher(tideal, treal)
