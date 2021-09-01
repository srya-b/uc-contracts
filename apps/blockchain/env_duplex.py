from uc.utils import waits
import gevent
import logging
from ecdsa import VerifyingKey, SigningKey, NIST384p
from contract_state import Contract_State

log = logging.getLogger(__name__)
logging.basicConfig(level=1)


def env(k, static, z2p, z2f, z2a, z2w, a2z, p2z, f2z, w2z, pump):
    state_contract = Contract_State( lambda: 1 )

    contract = state_contract
    min_interval = 2
    max_interval = 5
    delta = 10
    
    sid = ('sid', contract, min_interval, max_interval, delta)
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

    def _w2z():
        while True:
            m = waits(w2z)
            transcript.append('w2z: ', str(m.msg))
            pump.write('')

    g1 = gevent.spawn(_a2z)
    g2 = gevent.spawn(_p2z)
  
    # generate a key
    sender_sk = SigningKey.generate()
    sender_vk = sender_sk.verifying_key
    receiver_sk = SigningKey.generate()
    receiver_vk = receiver_sk.verifying_key
    
    tx = (receiver_vk.to_string(), sender_vk.to_string(), 10, None)
    tx_sender_sig = sender_sk.sign(str(tx).encode())

    z2w.write( ((sid, 'G_Ledger'), ('balances',)) )
    waits(pump)

    #z2w.write( ((sid, 'Wrapper'), ('poll',)), 1 )
    #waits(pump)

    #print('send-tx')
    #z2p.write( ((sid,1), ('send-tx', (tx, tx_sender_sig))) )
    #waits(pump)
    #
    #print('select-tx')
    #z2a.write( ('A2F', ((sid, 'G_Ledger'), ('select-tx', [(tx, tx_sender_sig)])), 0) )
    #waits(pump)

    #error = False
    #if error:
    #    z2a.write( ('A2W', ('callme', 1), 0) )
    #    waits(pump)

    #    z2w.write( ('poll',), 1)
    #    waits(pump)
    #    z2w.write( ('poll',), 1)
    #    waits(pump)
    #    z2w.write( ('poll',), 1)
    #    waits(pump)

    #    z2a.write( ('A2W', ('exec', 6, 0), 0) )
    #    waits(pump)
    #else:
    #    z2a.write( ('A2W', ('callme', 3), 0) )
    #    waits(pump)

    #    z2w.write( ('poll',), 1)
    #    waits(pump)
    #    z2w.write( ('poll',), 1)
    #    waits(pump)
    #    z2w.write( ('poll',), 1)
    #    waits(pump)

    #    z2a.write( ('A2W', ('exec', 6, 0), 0) )
    #    waits(pump)

    #tx = ('contract', sender_vk.to_string(), 1, ('evidence', (1, 2, 3, 4) ))
    #tx_sender_sig = sender_sk.sign(str(tx).encode()) 

    #z2p.write( ((sid,1), ('send-tx', (tx, tx_sender_sig))) )
    #waits(pump)

    #z2a.write( ('A2F', ((sid, 'G_Ledger'), ('select-tx', [(tx, tx_sender_sig)])), 0) )
    #waits(pump)

    #z2w.write( ('poll',), 1)
    #waits(pump)
    #z2w.write( ('poll',), 1)
    #waits(pump)

    #    
    #print('tx_sender_sig', tx_sender_sig)

    return transcript

from uc.itm import wrappedPartyWrapper, DuplexWrapper
from uc.adversary import DummyWrappedAdversary
from g_ledger import G_Ledger
from uc.syn_ours import Syn_FWrapper
from uc.execuc import execWrappedUC

t1 = execWrappedUC(
    128,
    env,
    [('G_Ledger', G_Ledger)],
    wrappedPartyWrapper('G_Ledger'),
#    Syn_FWrapper,
    #DuplexWrapper(Syn_FWrapper, 'Wrapper', G_Ledger, "G_Ledger"),
    GlobalFWrapper([Syn_FWrapper, G_Ledger], ['F_Wrapper', 'G_Ledger'])
    DummyWrappedAdversary,
    None, 
)

print('\nTranscript')
for i in t1:
    print(i)

