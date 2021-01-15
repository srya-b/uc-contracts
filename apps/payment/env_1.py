from uc.utils import waits
import gevent
import logging

log = logging.getLogger(__name__)
logging.basicConfig(level=1)

def env1(k, static, z2p, z2f, z2a, z2w, a2z, p2z, f2z, w2z, pump):
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

    g1 = gevent.spawn(_a2z)
    g2 = gevent.spawn(_p2z)
    
    print('Status of pump before call', pump.is_set())
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

    z2w.write( ('poll',), 1 )
    waits(pump)

    z2p.write( ((sid, P_s), ('balance',)) )
    waits(pump)

    # close operation
    z2p.write( ((sid, P_s), ('close',)) )
    waits(pump)

    for _ in range(18):
        z2w.write( ('poll',), 1 )
        waits(pump)
   
    # z2a.write( ('A2W', ('exec', 13, 1), 0) )
    # waits(pump)
    # z2a.write( ('A2W', ('exec', 13, 0), 0) )
    # waits(pump)

    # z2w.write( ('poll',), 1 )
    # waits(pump)    

    gevent.kill(g1)
    gevent.kill(g2)

    print('Transcript', transcript)
    return transcript


def distinguisher(t_ideal, t_real):
    print('\n\t\033[93m Ideal transcript\033[0m')
    for i in t_ideal: print(i)

    print('\n\t\033[93m real transcript\033[0m')
    for i in t_real: print(i)

    if t_ideal == t_real:
        print("\033[92m[Distinguisher] They're the same\033[0m")
    else:
        print("\033[91m[Distinguisher] They're different\033[0m")


from uc.itm import wrappedPartyWrapper, wrappedProtocolWrapper
from uc.adversary import DummyWrappedAdversary
from contract_pay import Contract_Pay_and_bcast_and_channel
from f_pay import F_Pay, payment_simulator, Payment_Simulator
from prot_payment import Prot_Pay
from uc.syn_ours import Syn_FWrapper
from uc.execuc import execWrappedUC

if __name__=='__main__':
    print('\n\t\t\033[93m [IDEAL WORLD] \033[0m\n')
    print('env1 type', type(env1))
    
    t1 = execWrappedUC(
        128,
        env1,
        [('F_pay', F_Pay)],
        wrappedPartyWrapper('F_pay'),
        Syn_FWrapper,
        payment_simulator(Prot_Pay),
        None
    )
    
    print('\n\t\t\033[93m [REAL WORLD] \033[0m\n')
    t2 = execWrappedUC(
        128,
        env1,
        [('F_contract', Contract_Pay_and_bcast_and_channel)],
        wrappedProtocolWrapper(Prot_Pay),
        Syn_FWrapper,
        DummyWrappedAdversary,
        None
    )

    distinguisher(t1, t2)
