import dump
import comm
import gevent
from itm import ITMFunctionality, ITMPassthrough, ITMAdversary, createParties, ITMPrinterAdversary
from comm import P2F, P2G, F2G, A2G, A2P, M2FChannel, M2F, Z2P, A2P, Z2A
from utils import z_mine_blocks, z_send_money, z_get_balance, z_get_leaks, z_tx_leak, z_tx_leaks, z_delay_tx, z_set_delays, z_start_ledger, z_ideal_parties, z_sim_party, print
from g_ledger import Ledger_Functionality, LedgerITM
from collections import defaultdict
from gevent.queue import Queue, Channel
from f_paymentchannel import PaymentChannel_Functionality, PayITM, Sim_Payment
from pay_protocol import Adv, Contract_Pay
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

''' All of the channels for the functionalities '''
a2ledger = A2G(('sid1',0),('sid',7))
f2ledger = F2G(('sid1',0),('sid2',1))
m2ledger = M2FChannel(('sid1',0))
p2ledger1 = M2F(('sid2',2),m2ledger)
p2ledger2 = M2F(('sid2',3),m2ledger)

a2fpay = A2G(('sid2',1), ('sid',7))
f2fpay = F2G(('sid2',1), ('none',-1))
m2fpay = M2FChannel(('sid2',1))
p2fpay1 = M2F(('sid2',2), m2fpay)
p2fpay2 = M2F(('sid2',3), m2fpay)

z2p1 = Z2P(('sid2',2), (0,0))
z2p2 = Z2P(('sid2',3), (0,0))
a2p1 = A2P(('sid2',2), ('sid',7))
a2p2 = A2P(('sid2',3), ('sid',7))

z2sp = Z2P(('sid2',23), (0,0))
a2sp = A2P(('sid2',23), ('sid',7))
sp2f = M2F(('sid2',23), m2ledger)
z2a = Z2A(('sid',7), (0,0))

'''Blockchain Functionality'''
g_ledger, protected, ledger_itm = z_start_ledger('sid1',0,Ledger_Functionality,ProtectedITM, a2ledger, f2ledger, m2ledger)
comm.setFunctionality(ledger_itm)
'''Payment Channel functionality'''
idealf, pay_itm = PayITM('sid2',1, ledger_itm, 2, 3, a2fpay, f2fpay, f2ledger, m2fpay)
comm.setFunctionality(pay_itm)
'''Ideal world parties'''
iparties = z_ideal_parties('sid2', [2,3], pay_itm, createParties, [a2p1,a2p2], [p2fpay1,p2fpay2], [z2p1,z2p2])
comm.setParties(iparties)
''' Extra party'''
simparty = z_sim_party('sid2', 23, ITMPassthrough, ledger_itm, a2sp, sp2f, z2sp)
comm.setParty(simparty)
#################### EXPERIMENT ########################
p1 = iparties[0]
p2 = iparties[1]
'''Adversary'''
#adversary = ITMAdversary('sid2',6)
#comm.setAdversary(adversary)
#adversary.addParty(p1); adversary.addParty(p2)
#gevent.spawn(adversary.run)
'''Simulator spawn'''
simulator = Sim_Payment('sid', 7, ledger_itm, pay_itm, Adv, p2, Contract_Pay, a2p2, a2ledger)
simitm = ITMAdversary('sid', 7, z2a, a2p2, a2fpay, a2ledger)
simitm.init(simulator)
comm.setAdversary(simitm)
gevent.spawn(simitm.run)
print('P1:', p1.sid, p1.pid)
print('P2:', p2.sid, p2.pid)

'''Start functionality itms'''
gevent.spawn(pay_itm.run)

'''p1 and p2 needs funds, so mine blocks and send them money'''
#z_mine_blocks(1, simparty, ledger_itm)
z_mine_blocks(1, z2sp, simparty.sender)
#z_send_money(10, p1, simparty, ledger_itm)
z_send_money(10, p1, z2sp)
#z_send_money(10, p2, simparty, ledger_itm)
z_send_money(10, p2, z2sp)
#z_set_delays(simitm, ledger_itm, [0,0])
z_set_delays(z2a, simitm, ledger_itm, [0,0])
#z_mine_blocks(1, simparty, ledger_itm)
z_mine_blocks(1, z2sp, simparty.sender)


print('USERS DEPOSIT')
'''
Users deposit
'''
#exe(p1.input.set( ('deposit', 10) ))
exe(z2p1.write( ('deposit', 10) ))
#exe(p2.input.set( ('deposit', 1) ))
exe(z2p2.write( ('deposit', 1) ))
#z_set_delays(simitm, ledger_itm, [0,0])
z_set_delays(z2a, simitm, ledger_itm, [0,0])
#z_mine_blocks(1, simparty, ledger_itm)
z_mine_blocks(1, z2sp, simparty.sender)

'''Check channel balanace is correct'''
balance = p1.subroutine_call(
    ('balance',)
)
print('balance', balance)
assert balance[0] == 10 and balance[1] == 1
'''Send my homeboi p2 some money bruh
    ....ok....
'''

#exe(p1.input.set(('pay', 2)))
exe(z2p1.write( ('pay',2) ))
balance = p2.subroutine_call(('balance',))
print('balance', balance)
assert balance[0] == 10-2 and balance[1] == 1+2, 'p1:(%d), p2:(%d)' % (balance[0], balance[1])


''' p1 multiple pays'''
#exe(p1.input.set(('pay', 1)))
#exe(p1.input.set(('pay', 1)))
#exe(p1.input.set(('pay', 1)))
#exe(p1.input.set(('pay', 1)))
exe(z2p1.write( ('pay',1) ))
exe(z2p1.write( ('pay',1) ))
exe(z2p1.write( ('pay',1) ))
exe(z2p1.write( ('pay',1) ))

balance = p2.subroutine_call(
    ('balance',)
)
print('balance', balance)
assert balance[0] == 10-2-4 and balance[1] == 1+2+4, 'p1:(%d), p2:(%d)' % (balance[0], balance[1])


print('ADVERSARY corrupting p2 and sending payment...')
#exe(simitm.input.set(
#    ('party-input', (p2.sid, p2.pid), ('pay', 2))
#))
exe(z2a.write( 
    ('party-input', (p2.sid, p2.sid), ('pay',2))
))
#z_set_delays(simitm, ledger_itm, [8])
z_set_delays(z2a, simitm, ledger_itm, [8])
#z_mine_blocks(8, simparty, ledger_itm)
z_mine_blocks(8, z2sp, simparty.sender)

balance = p1.subroutine_call(('balance',))
print(balance)
