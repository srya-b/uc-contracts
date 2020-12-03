from uc.utils import waits
import gevent
import logging

logging.basicConfig(level=1)

def env(k, static, z2p, z2f, z2a, z2w, a2z, p2z, f2z, w2z, pump):
    delta = 3
    P_s = 1
    P_r = 2
    b_s = 5
    b_r = 8
    sid = ('sid', P_s, P_r, b_s, b_r, delta)
    static.write( (('sid', sid), ('crupt',)) )

    transcript = []
    def _a2z():
        while True:
            m = waits(a2z)
            transcript.append('a2z: ' + str(m.msg))
            pump.write('')

    def _p2z():
        while True:
            m = waits(p2z)
            transcript.append('p2z: ' + str(m.msg))
            pump.write('')

    gevent.spawn(_a2z)
    gevent.spawn(_p2z)

    z2a.write(('',), 100)
    waits(pump)

    z2p.write( ((sid,P_s), ('balance',)) )
    waits(pump)

    # Should suceed
    z2p.write( ((sid,P_s), ('pay', 3)) )
    waits(pump)

    z2w.write( ('poll',), 1 )
    waits(pump)

    # P_r will output ("pay", 3)
    z2w.write( ('poll',), 1 )
    waits(pump)

    z2p.write( ((sid,P_s), ('balance',)) )
    waits(pump)

    # shoul fail
    z2p.write( ((sid, P_s), ('pay', 10)) )
    waits(pump)

    z2w.write( ('poll',), 1 )
    waits(pump)

    # z2w.write( ('poll',), 1 )
    # waits(pump)

    # z2p.write( ((sid, P_s), ('balance',)) )
    # waits(pump)

    # # close operation
    # z2p.write( ((sid, P_s), ('close',)) )
    # waits(pump)

    # z2w.write( ('poll',), 1 )
    # waits(pump)
    # z2w.write( ('poll',), 1 )
    # waits(pump)
    # z2w.write( ('poll',), 1 )
    # waits(pump)
    # z2w.write( ('poll',), 1 )
    # waits(pump)
   
    # z2a.write( ('A2W', ('exec', 13, 1), 0) )
    # waits(pump)
    # z2a.write( ('A2W', ('exec', 13, 0), 0) )
    # waits(pump)

    # z2w.write( ('poll',), 1 )
    # waits(pump)



    return transcript


from uc.itm import wrappedPartyWrapper
from uc.adversary import DummyWrappedAdversary
from f_pay import F_Pay, payment_simulator, Payment_Simulator
from prot_payment import Prot_Pay
from uc.syn_ours import Syn_FWrapper
from uc.execuc import execWrappedUC

t1 = execWrappedUC(
    128,
    env,
    [('F_pay', F_Pay)],
    wrappedPartyWrapper('F_pay'),
    Syn_FWrapper,
    payment_simulator(Prot_Pay),
    None
)

print('\nTranscript')
for i in t1:
    print(i)
