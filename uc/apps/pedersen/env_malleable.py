from uc.utils import waits, collectOutputs
import os
import gevent
import secp256k1 as secp

def env_crupt_receiver_malleability(k, static, z2p, z2f, z2a, a2z, f2z, p2z, pump):
    sid = ('one', ("1, 2",))
    static.write( (('sid',sid), ('crupt', 2)))

    transcript = []

    def _p2z():
        while True:
            m = waits(p2z)
            transcript.append('p2z: ' + str(m))
            pump.write('dump')

    g2 = gevent.spawn(_p2z)

    m = secp.uint256_from_str(os.urandom(32))
   
    z2p.write( (1, ('commit', m)) )
    msg = waits(a2z)
    transcript.append('a2z: ' + str(msg))
    _,(fro,(_,_,(_, commitment))) = msg

    z2a.write( ('A2P', (2, ('value',))) )
    msg = waits(a2z)
    transcript.append('a2z: ' + str(msg))
    _,(fro,((g,h),)) = msg

    commitmentplus1 = commitment + g

    z2p.write( (1, ('reveal',)) )
    msg = waits(a2z)
    transcript.append('a2z: ' + str(msg))
    _,(fro,(_,_,(_,msg,randomness))) = msg

    checkcommitmentplus1 = (g * (msg+1)) + (h * randomness)

    print('\nPredicted Commitment:\n\t{}'.format(commitmentplus1))
    print('\nActual commitment of m+1 given committer randomness:\n\t{}'.format(checkcommitmentplus1))

    gevent.kill(g2)
    
    print('\ntranscript:\n\t{}'.format(transcript))
    return transcript

from uc.adversary import DummyAdversary
from uc.protocol import DummyParty
from uc.execuc import execUC
from f_crs import F_CRS
from prot_com import Commitment_Prot

tideal = execUC(
    128,
    env_crupt_receiver_malleability,
    F_CRS,
    Commitment_Prot,
    DummyAdversary
)
    
