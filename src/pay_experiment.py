import gevent
import dump
import comm
from itm import ITMFunctionality, ITMPassthrough, ITMAdversary, createParties
from g_ledger import Ledger_Functionality, LedgerITM
from collections import defaultdict
from gevent.queue import Queue, Channel
from f_paymentchannel import PaymentChannel_Functionality, PayITM
from protected_wrapper import Protected_Wrapper, ProtectedITM

'''
Blockchain Functionality
'''
g_ledger = Ledger_Functionality('sid1', 0)
protected,ledger_itm = ProtectedITM('sid1', 0, g_ledger)
comm.setFunctionality(ledger_itm)

'''
Payment Channel functionality
'''
idealf, pay_itm = PayITM('sid2',1, ledger_itm, 2, 3)
comm.setFunctionality(pay_itm)

'''
Ideal world parties
'''
iparties = createParties('sid2', range(2,4), pay_itm)
comm.setParties(iparties)
for party in iparties:
    gevent.spawn(party.run)

'''
Start functionality itms
'''
gevent.spawn(ledger_itm.run)
gevent.spawn(pay_itm.run)

:


