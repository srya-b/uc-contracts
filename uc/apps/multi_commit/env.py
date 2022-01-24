from uc.utils import waits
import gevent

def env(k, static, z2p, z2f, z2a, a2z, f2z, p2z, pump):
    sid = "('one', 1, 2)"
    static.write( (('sid', sid), ('crupt',)) )

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

    z2p.write( (1, ("('two', 1, 2)", ('commit', 0))) )
    waits(pump)

    z2p.write( (1, ("('two', 1, 2)", ('reveal',))) )
    waits(pump)

    gevent.kill(g1)
    gevent.kill(g2)

    print('transcript', transcript)
    return transcript

from uc.adversary import DummyAdversary
from uc.apps.commitment import F_Com_Channel
from uc.execuc import execUC
from uc.protocol import DummyParty
from uc.multisession import bangF

tideal = execUC(
    128,
    env,
    bangF(F_Com_Channel),
    DummyParty,
    DummyAdversary
)
