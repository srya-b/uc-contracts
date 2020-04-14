from itm import WrappedProtocolWrapper, WrappedPartyWrapper
from adversary import DummyWrappedAdversary
from prot_online import OnlineMPCProtocol
from asyncwrapper import AsyncWrapper
from f_atomic import AtomicBroadcastFunctionality
from f_offline import OfflinePhaseFunctionality
from f_async import AsyncBroadcastFunctionality
from f_abb import AsyncABBFunctionality
from prot_online import Functionalities as F
from contract import ExampleContract
from execuc import execWrappedUC
from utils import z_get_leaks, waits, MessageTag

import logging

log = logging.getLogger(__name__)
logging.basicConfig(level="INFO")


def env(static, z2p, z2f, z2a, z2w, a2z, p2z, f2z, w2z, pump):
    n = 5
    sid = ('ssid', tuple(range(n)))
    static.write( (('sid', sid), ('crupt',)) )
    z2p.write( ((sid, 1), (MessageTag.CREATE_CONTRACT, ExampleContract)) )
    
    log.info(waits(pump, a2z, p2z))
    for _ in range(30):
        z2w.write( (MessageTag.ADVANCE,) )
        log.info(waits(pump, a2z, p2z))
        
    z2a.write(('A2W', (MessageTag.SEND_LEAKS,)))
    log.info(waits(pump, a2z, p2z))
    input("")
    
    z2a.write(('A2W', (MessageTag.SEND_LEAKS,)))
    log.info(waits(pump, a2z, p2z))
    input("")

    for pid in range(n):
        z2p.write( ((sid, pid), (MessageTag.INPUT_VAL, 2**pid, 0)))
        log.info(waits(pump, a2z, p2z))
        
    for _ in range(170):
        z2w.write( (MessageTag.ADVANCE,) )
        log.info(waits(pump, a2z, p2z))
if __name__ == '__main__':
    print('\n\t\t\033[93m [IDEAL WORLD] \033[0m\n')
    execWrappedUC(env, [('F_abb', AsyncABBFunctionality)], WrappedPartyWrapper, AsyncWrapper, 'F_abb', DummyWrappedAdversary)
    print('\n\t\t\033[93m [REAL WORLD] \033[0m\n')
    execWrappedUC(env, [(F.F_ATOMIC, AtomicBroadcastFunctionality), (F.F_OFFLINE, OfflinePhaseFunctionality), (F.F_ASYNC, AsyncBroadcastFunctionality)], WrappedProtocolWrapper, AsyncWrapper, OnlineMPCProtocol, DummyWrappedAdversary)
