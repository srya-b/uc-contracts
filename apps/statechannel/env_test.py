from uc.utils import waits
import gevent
import logging

logging.basicConfig(level=1)

def update_f(state, inputs, aux_in):
    state_ = state
    if state_ is None: state_ = 0
    print('\nstate', state_)
    print('\ninputs', inputs)
    for pid in inputs:
        if inputs[pid]: state_ += inputs[pid]
    return state_, []

def env(k, static, z2p, z2f, z2a, z2w, a2z, p2z, f2z, w2z, pump):
    delta = 2
    P_1 = 1
    P_2 = 2
    P_3 = 3
    sid = ('sid', update_f, None, (P_1, P_2, P_3), delta)
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

    z2p.write( ((sid,P_1), ('input', 12)) )
    waits(pump)

    z2a.write( ('A2W', ('callme', 4), 0) )
    waits(pump)
    
    for _ in range(3):
        z2w.write( ('poll',), 1 )
        waits(pump)

    z2a.write( ('A2W', ('exec', 7, 0,), 0) )
    waits(pump)

    z2a.write( ('A2W', ('callme', 6), 0) )
    waits(pump)

    z2p.write( ((sid, P_3), ('input', 1)) )
    waits(pump)

    for _ in range(3):
        z2w.write( ('poll',), 1 )
        waits(pump)
   
    z2a.write( ('A2W', ('exec', 7, 0,), 0) )
    waits(pump)
   
    for _ in range(2):
        z2w.write( ('poll',), 1)
        waits(pump)

    return transcript

from uc.itm import wrappedPartyWrapper
from uc.adversary import DummyWrappedAdversary
from f_state import F_State
from uc.syn_ours import Syn_FWrapper
from uc.execuc import execWrappedUC


t1 = execWrappedUC(
    128,
    env,
    [('F_state', F_State)],
    wrappedPartyWrapper('F_state'),
    Syn_FWrapper,
    DummyWrappedAdversary,
    None
)

print('\nTranscript')
for i in t1:
    print(i)
