import gevent
from gevent.queue import Queue, Channel
from collections import defaultdict
from itm import ITMFunctionality, ITMPassthrough, ITMAdversary, createParties
import dump
from f_multisig import C_Multisig, Multisig_Functionality, MultisigITM
from g_ledger import Ledger_Functionality, LedgerITM
import comm
from protected_wrapper import Protected_Wrapper, ProtectedITM

'''
Blockchain Functionality
'''
g_ledger = Ledger_Functionality('sid1', 0)
protected,ledger_itm = ProtectedITM('sid1', 0, g_ledger)
comm.setFunctionality(ledger_itm)

'''
Multisig functionality
'''
caddr = 'abcd'
idealf, multisig_itm = MultisigITM('sid2',1,ledger_itm,2,3,caddr)
comm.setFunctionality(multisig_itm)

'''
Ideal world parties
'''
iparties = createParties('sid2', range(2,4), multisig_itm)
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
adversary = ITMAdversary('sid2', 6)
comm.setAdversary(adversary)
g_ledger.set_backdoor(adversary.leak)
idealf.set_backdoor(adversary.leak)
gevent.spawn(adversary.run)

'''
Simulator spawn
'''
#simulator = Sim_Multisig('sid', 7, ledger_itm, multisig_itm)
#gevent.spawn(simulator.run)

simparty = ITMPassthrough('sid2', 23)
comm.setParty(simparty)
simparty.init(ledger_itm)
gevent.spawn(simparty.run)

#################### EXPERIMENT ##############################
#################### TRIGGERED  ##############################
#simaddr = '1234'
def z_mine_blocks(n, itm):
    sender = (itm.sid, itm.pid)
    for i in range(n):
        #itm.input.set( ('tick', sender) )
        ledger_itm.input.set((
            sender,
            True,
            ('tick', sender)
        ))
        dump.dump_wait()

def z_send_money(v, to, itm):
    sender = (itm.sid, itm.pid)
    
    ledger_itm.input.set((
        sender,
        True,
        ('transfer', (to.sid,to.pid), v, (), 'does not matter')
    ))
    dump.dump_wait()

def z_get_balance(itm):
    sender = (simparty.sid, simparty.pid)
    return ledger_itm.subroutine_call((
        sender,
        True,
        ('getbalance', (itm.sid, itm.pid))
    ))

p1 = iparties[0]
p2 = iparties[1]

print('P1:', p1.sid, p1.pid)
print('P2:', p2.sid, p2.pid)

''' p1 and p2 need funds, so mine blocks and send them funds '''
z_mine_blocks(1, simparty)
#bsim = ledger_itm.subroutine_call((
#    ('sid1234',1),
#    True,
#    ('getbalance', (simparty.sid, simparty.pid))
#))
bsim = z_get_balance(simparty)
assert(bsim > 0)

z_send_money(10, p1, simparty)
z_send_money(10, p2, simparty)
z_mine_blocks(10, simparty)

b1 = z_get_balance(p1)
print('P1 BALANCE', b1)
b2 = z_get_balance(p2)
print('P2 BALANCE', b2)

'''
p1 deposit funds
'''
p1.input.set( ('deposit',10) )
dump.dump_wait()

'''
Environment increments block number, different delivery of deposits.
'''
z_mine_blocks(1, simparty)

p2.input.set( ('deposit',1) )
dump.dump_wait()

'''
Mine blocks for deliver of first deposit
'''
z_mine_blocks(7, simparty)

'''
P1 is delivered, not P2
'''
balance = p1.subroutine_call( ('balance',) )
print('P1 BALANCE', balance)
z_mine_blocks(1, simparty)

'''
Finally, p2 deposit is also delivered
'''
balance = p2.subroutine_call( ('balance',) )
print('P2 BALANCE', balance)

print('*** DEPOSITS SHOULD BE DELIVERED ***')

'''
Open a new transfer
'''
p1.input.set( ('transfer', (simparty.sid,simparty.pid) , 5) )
dump.dump_wait()

z_mine_blocks(8, simparty)

p2.input.set( ('confirm', 0) )
dump.dump_wait()

z_mine_blocks(8, simparty)
balance = p2.subroutine_call( ('balance',))
print('BALANCE AFTER:', balance)





