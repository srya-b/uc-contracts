import dump
import comm
import gevent
from itm import ITMFunctionality, ITMPassthrough, ITMAdversary, createParties, ITMPrinterAdversary
from utils import z_mine_blocks, z_send_money, z_get_balance, z_get_leaks, z_tx_leak, z_tx_leaks, z_delay_tx, z_set_delays, z_start_ledger, z_ideal_parties, z_sim_party, print
from g_ledger import Ledger_Functionality, LedgerITM
from collections import defaultdict
from gevent.queue import Queue, Channel
from f_paymentchannel import PaymentChannel_Functionality, PayITM, Sim_Payment
from protected_wrapper import Protected_Wrapper, ProtectedITM


'''
This environment just does a few payments, instructs the adversary to corrupt
a party and send a paymemt. The dishonest case happens and there's a ledger
transaction instead of an offline payment. This is the trace of the execution:

Legend: At the end of each line is the balance on-chain and on-contract for the
        parties after the line is executed. 
            p1(x,y) := p1 has x coins on-chain and 7 coins in the contract

1. Miner gives p1,p2 10 ether each. p1(10,0), p2(10,0)
2. P1 deposits 10, p2 deposits 1. p1(0,10), p2(9,1)
3. P1 pays 2 to P2. p1(0,8), p2(9,3)
4. P1 pays 1 to P2 4 times. p1(0,4), p2(9,7)
5. P2 (corrupted) pays 2 to p1. p1(0,6), p2(9,5)

Final balance in the contract:
    p1=6 p2=5
'''

def exe(result):
    dump.dump_wait()

'''
Blockchain Functionality
'''
#g_ledger = Ledger_Functionality('sid1', 0)
#protected,ledger_itm = ProtectedITM('sid1', 0, g_ledger)
#comm.setFunctionality(ledger_itm)
#gevent.spawn(ledger_itm.run)
g_ledger, protected, ledger_itm = z_start_ledger('sid1',0,Ledger_Functionality,ProtectedITM)
comm.setFunctionality(ledger_itm)

'''
Payment Channel functionality
'''
idealf, pay_itm = PayITM('sid2',1, ledger_itm, 2, 3)
comm.setFunctionality(pay_itm)

'''
Ideal world parties
'''
#iparties = createParties('sid2', range(2,4), pay_itm)
#comm.setParties(iparties)
#for party in iparties:
#    gevent.spawn(party.run)
iparties = z_ideal_parties('sid2', [2,3], pay_itm, createParties)
comm.setParties(iparties)

''' 
Extra party
'''
#simparty = ITMPassthrough('sid2', 23)
#comm.setParty(simparty)
#simparty.init(ledger_itm)
#gevent.spawn(simparty.run)
simparty = z_sim_party('sid2', 23, ITMPassthrough, ledger_itm)
comm.setParty(simparty)
#################### EXPERIMENT ########################
p1 = iparties[0]
p2 = iparties[1]

'''Adversary'''
#adversary = ITMAdversary('sid2',6)
#comm.setAdversary(adversary)
#adversary.addParty(p1); adversary.addParty(p2)
#gevent.spawn(adversary.run)


'''
Simulator spawn
'''
simulator = Sim_Payment('sid', 7, ledger_itm, pay_itm, p2, 'rando')
simitm = ITMAdversary('sid', 7)
simitm.init(simulator)
comm.setAdversary(simitm)
gevent.spawn(simitm.run)
print('P1:', p1.sid, p1.pid)
print('P2:', p2.sid, p2.pid)

'''
Start functionality itms
'''
gevent.spawn(pay_itm.run)

'''p1 and p2 needs funds, so mine blocks and send them money'''
z_mine_blocks(1, simparty, ledger_itm)
z_send_money(10, p1, simparty, ledger_itm)
z_send_money(10, p2, simparty, ledger_itm)
z_set_delays(simitm, ledger_itm, [0,0])
z_mine_blocks(1, simparty, ledger_itm)


print('USERS DEPOSIT')
'''
Users deposit
'''
exe(p1.input.set( ('deposit', 10) ))
exe(p2.input.set( ('deposit', 1) ))
z_set_delays(simitm, ledger_itm, [0,0])
z_mine_blocks(1, simparty, ledger_itm)

'''Check channel balanace is correct'''
balance = p1.subroutine_call(
    ('balance',)
)
print('balance', balance)
assert balance[0] == 10 and balance[1] == 1
'''Send my homeboi p2 some money bruh
    ....ok....
'''

exe(p1.input.set(
    ('pay', 2)
))
balance = p2.subroutine_call(
    ('balance',)
)
print('balance', balance)
assert balance[0] == 10-2 and balance[1] == 1+2, 'p1:(%d), p2:(%d)' % (balance[0], balance[1])


''' p1 multiple pays'''
exe(p1.input.set(
    ('pay', 1)
))
exe(p1.input.set(
    ('pay', 1)
))
exe(p1.input.set(
    ('pay', 1)
))
exe(p1.input.set(
    ('pay', 1)
))

balance = p2.subroutine_call(
    ('balance',)
)
print('balance', balance)
assert balance[0] == 10-2-4 and balance[1] == 1+2+4, 'p1:(%d), p2:(%d)' % (balance[0], balance[1])


print('ADVERSARY corrupting p2 and sending payment...')
exe(simitm.input.set(
    ('party-input', (p2.sid, p2.pid), ('pay', 2))
))
z_set_delays(simitm, ledger_itm, [8])
z_mine_blocks(8, simparty, ledger_itm)

balance = p1.subroutine_call(('balance',))
print(balance)
