from uc.utils import waits
import gevent

def env(k, static, z2p, z2f, z2a, z2g, a2z, p2z, f2z, g2z, pump):
    sid = 'hellsid'
    gsid = '#' + sid
    static.write( (('sid', sid), ('gsid', gsid), ('ssids', (('ledgersid', 2, 7, 3), 'wrappersid')), ('crupt',)))

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

    z2p.write( ((sid, 1), ('ledger', ('accounts',))) )
    waits(pump)

    z2a.write( ('A2G', (gsid, ('mineblock',))))
    waits(pump)

    return transcript

from uc.itm import gucProtocolWrapper, GUCDummyParty, duplexGUCWrapper 
from uc.adversary import GUCDummyAdversary
from f_dummy import GUCDummyFunctionality
from g_ledger import Ganache_Ledger
from uc.execuc import execGUC
from uc.syn_ours import Syn_FWrapper

t = execGUC(
    128,
    env,
    GUCDummyFunctionality,
    gucProtocolWrapper(GUCDummyParty),
    #Ganache_Ledger,
    duplexGUCWrapper(Ganache_Ledger, Syn_FWrapper),
    GUCDummyAdversary,
    None
)

print('\nTranscript')
for i in t:
    print(i)

