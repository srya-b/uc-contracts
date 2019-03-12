import gevent
from gevent.queue import Queue, Channel
from collections import defaultdict
from itm import ITMFunctionality, ITMPassthrough, ITMAdversary, createParties
import dump
from f_multisig import C_Multisig, Multisig_Functionality, MultisigITM
from g_ledger import Ledger_Functionality, LedgerITM
import comm

'''
Blockchain Functionality
'''
g_ledger, ledger_itm = LedgerITM('sid', 0)
comm.setFunctionality(ledger_itm)

'''
Multisig functionality
'''
caddr = 'abcd'
idealf, multisig_itm = MultisigITM('sid',1,ledger_itm,2,3,caddr)
comm.setFunctionality(multisig_itm)

'''
Ideal world parties
'''
iparties = createParties('sid', range(2,4), multisig_itm)
comm.setParties(iparties)
for party in iparties:
    gevent.spawn(party.run)

'''
Real world.
'''
#rparties = [ITMPassthrough('sid', i) for i in range(4,6)]
#for party in rparties:
#    party.init(ledger_itm)
#for party in rparties:
#    gevent.spawn(party.run)

'''
Start functionality itms
'''
gevent.spawn(ledger_itm.run)
gevent.spawn(multisig_itm.run)

'''
Real adversary spawn.
'''
adversary = ITMAdversary('sid', 6)
comm.setAdversary(adversary)
g_ledger.set_backdoor(adversary.leak)
idealf.set_backdoor(adversary.leak)
gevent.spawn(adversary.run)

'''
Simulator spawn
'''
#simulator = Sim_Multisig('sid', 7, ledger_itm, multisig_itm)
#gevent.spawn(simulator.run)

simparty = ITMPassthrough('sid', 23)
comm.setParty(simparty)
simparty.init(ledger_itm)
gevent.spawn(simparty.run)

#################### EXPERIMENT ##############################
#################### TRIGGERED  ##############################
simaddr = '1234'
def mine_blocks(n):
    for i in range(n):
        simparty.input.set( ('tick', simaddr) )
        dump.dump_wait()


p1 = iparties[0]
p2 = iparties[1]

print('P1:', p1.sid, p1.pid)
print('P2:', p2.sid, p2.pid)

'''
p1 deposit funds
'''
p1.input.set( ('deposit',10) )
dump.dump_wait()

'''
Environment increments block number, different delivery of deposits.
'''
mine_blocks(1)

p2.input.set( ('deposit',1) )
dump.dump_wait()

'''
Mine blocks for deliver of first deposit
'''
mine_blocks(7)

'''
P1 is delivered, not P2
'''
balance = p1.subroutine_call( ('balance',) )
print('P1 BALANCE', balance)
mine_blocks(1)

'''
Finally, p2 deposit is also delivered
'''
balance = p2.subroutine_call( ('balance',) )
print('P2 BALANCE', balance)

'''
Open a new transfer
'''
p1.input.set( ('transfer', 'xxx', 5) )
dump.dump_wait()

mine_blocks(8)

p2.input.set( ('confirm', 0) )
dump.dump_wait()

mine_blocks(8)
balance = p2.subroutine_call( ('balance',))
print('BALANCE AFTER:', balance)
dump.dump_wait()





