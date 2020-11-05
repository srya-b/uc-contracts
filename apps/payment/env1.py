from uc.utils import waits
import logging
import gevent

def env1(k, static, z2p, z2f, z2a, z2w, a2z, p2a, f2z, w2z, pump):
    delta = 3
    n = 3
    sid = ('one', 1, 2, 10, 10, delta)
    static.write( (('sid', sid), ('crupt',)) )

    transcript = []
    def _a2z():
        while True:
            m = waits(a2z)
            transcript.append('a2z: ' + str(m.msg))
            pump.write('dump')

    def _p2z():
        while True:
            m = waits(p2z)
            transcript.append('p2z: ' + str(m.msg))
            pump.write('dump')

    g1 = gevent.spawn(_a2z)
    g2 = gevent.spawn(_p2z)

    z2p.write( ((sid,1), ('close', (6, 14, 1), '')) )
    waits(pump)

from uc.itm import wrappedPartyWrapper
from uc.adversary import DummyWrappedAdversary
from contract_pay import Contract_Pay
from uc.syn_ours import Syn_FWrapper
from uc.execuc import execWrappedUC

t1 = execWrappedUC(
    128,
    env1,
    [('F_contract', Contract_Pay)],
    wrappedPartyWrapper('F_contract'),
    Syn_FWrapper,
    DummyWrappedAdversary,
    None
)
