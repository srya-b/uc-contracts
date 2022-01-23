from uc.utils import waits, collectOutputs
import os
import gevent
import secp256k1 as secp

def env_test_fcrs(k, static, z2p, z2f, z2a, a2z, f2z, p2z, pump):
    g = secp.make_random_point()
    h = secp.make_random_point()

    sid = ('one', ("1, 2", (g,h)))
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

    print('\ng:\n\t{}'.format(g))
    print('\nh:\n\t{}'.format(h))

    z2p.write( (1, ('value',)) )
    waits(pump)

    gevent.kill(g1)
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
    env_test_fcrs,
    F_CRS,
    DummyParty,
    DummyAdversary
)
    
