from uc.utils import waits, collectOutputs
import os
import gevent
import secp256k1 as secp

def env_honest(k, static, z2p, z2f, z2a, a2z, f2z, p2z, pump):
    print('\033[94m[ env_honest ]\033[0m')

    sid = ('one', ("1, 2",))
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

    m = secp.uint256_from_str(os.urandom(32))
    print('\n commiting to the point: \n\t{}\n'.format(m))

    z2p.write( (1, ('commit', m)) )
    waits(pump)

    z2p.write( (1, ('reveal',)) )
    waits(pump)
    
    gevent.kill(g1)
    gevent.kill(g2)
    
    print('transcript', transcript)
    return transcript

from uc.adversary import DummyAdversary
from uc.protocol import DummyParty
from uc.execuc import execUC
from f_crs import F_CRS
from prot_com import Commitment_Prot

tideal = execUC(
    128,
    env_honest,
    F_CRS,
    Commitment_Prot,
    DummyAdversary
)
    
