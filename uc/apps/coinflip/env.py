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

    z2p.write( ((sid,1), ('flip',)) )
    waits(pump)

    z2p.write( ((sid,1), ('getflip',)) )
    waits(pump)

    z2p.write( ((sid,2), ('getflip',)) )
    waits(pump)
    gevent.kill(g1)
    gevent.kill(g2)

    return transcript

from uc.apps.coinflip import F_Flip, Flip_Prot
from uc.apps.commitment import F_Com_Channel
from uc.adversary import DummyAdversary
from uc import execUC
from uc.itm import protocolWrapper, DummyParty

tideal = execUC(
    128,
    env,
    F_Com_Channel,
    protocolWrapper(Flip_Prot),
    DummyAdversary
)
