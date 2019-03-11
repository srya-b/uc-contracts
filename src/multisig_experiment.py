import gevent
from gevent.queue import Queue, Channel
from collections import defaultdict
from itm import ITMFunctionality, ITMPassthrough, ITMAdversary
import dump
from f_multisig import C_Multisig, Multisig_Functionality
from g_ledger import Ledger_Functionality

## BLOCKCHAIN FUNCTIONALITY
g_ledger = Ledger_Functionality('sid', 0)
ledger_itm = ITMFunctionality('sid', 0)
ledger_itm.init(g_ledger)

## MULTISIG FUNCTIONALITY
caddr = 'abcd'
idealf = Multisig_Functionality('sid', 1, ledger_itm, 2, 3, caddr)
multisig_itm = ITMFunctionality('sid', 1)
multisig_itm.init(idealf)

## IDEAL WORLD PARITES ##  
iparties = [ITMPassthrough('sid', i) for i in range(2,4)]
for party in iparties:
    party.init(multisig_itm)
for party in iparties:
    gevent.spawn(party.run)

## REAL WORLD ##
#rparties = [ITMPassthrough('sid', i) for i in range(4,6)]
#for party in rparties:
#    party.init(ledger_itm)
#for party in rparties:
#    gevent.spawn(party.run)

## START FUNCTIONALITY ITMs ##
gevent.spawn(ledger_itm.run)
gevent.spawn(multisig_itm.run)

## REAL ADVERSARY ##
adversary = ITMAdversary('sid', 6)
gevent.spawn(adversary.run)

## IDEAL SIMULATOR ##
#simulator = Sim_Multisig('sid', 7, ledger_itm, multisig_itm)
#gevent.spawn(simulator.run)

simparty = ITMPassthrough('sid', 23)
simparty.init(ledger_itm)
gevent.spawn(simparty.run)

#################### EXPERIMENT ##############################
#################### TRIGGERED  ##############################

p1 = iparties[0]
p2 = iparties[1]

print('P1:', p1.sid, p1.pid)
print('P2:', p2.sid, p2.pid)
p1.input.set( ('deposit',10) )
dump.dump_wait()

# ENVIRONMENT INCREMENTS BLOCK NUMBER, CHECKS DELIVERY
addr = '1234'
simparty.input.set( ('tick', addr) )
dump.dump_wait()

p2.input.set( ('deposit',1) )
dump.dump_wait()

# WAIT FOR DELIVERY
for i in range(7):
    simparty.input.set( ('tick', addr) )
    dump.dump_wait()

# P1 SHOULD DELIVER BUT NOT P2
balance = p1.subroutine_call( ('balance',) )
print('P1 BALANCE', balance)
simparty.input.set( ('tick', addr) )
dump.dump_wait()

balance = p2.subroutine_call( ('balance',) )
print('P2 BALANCE', balance)




