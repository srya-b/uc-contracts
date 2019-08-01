import dump
import comm
import gevent
from itm import ITMFunctionality, ITMPassthrough, ITMAdversary, createParties, ITMPrinterAdversary
from utils import z_mine_blocks, z_send_money, z_get_balance, z_get_leaks, z_tx_leak, z_tx_leaks, z_delay_tx, z_set_delays, z_deploy_contract, z_mint, z_start_ledger, z_ideal_parties, z_sim_party, print
from g_ledger import Ledger_Functionality, LedgerITM
from collections import defaultdict
from gevent.queue import Queue, Channel
from f_state import StateChannel_Functionality, StateITM, Sim_State
from protected_wrapper import Protected_Wrapper, ProtectedITM

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
sim'd party
'''
#simparty = ITMPassthrough('sid2', 23)
#comm.setParty(simparty)
#simparty.init(ledger_itm)
#gevent.spawn(simparty.run)
simparty = z_sim_party('sid2',23,ITMPassthrough,ledger_itm)
comm.setParty(simparty)


caddr = simparty.subroutine_call( ('get-caddress',) )
'''
FUnctionality
'''
def U(state, inputs, auxin, rnd):
    if rnd == 0:
        state = 0
    for inp in inputs:
        if inp == 'add':
            state += 1
        elif inp == 'sub':
            state -= 1
    return state,None
idealf, state_itm = StateITM('sid2', 1, ledger_itm, caddr, U, 2, 3, 4)
comm.setFunctionality(state_itm)

''' 
Parites
'''
iparties = z_ideal_parties('sid2', [2,3,4], state_itm, createParties)
comm.setParties(iparties)
p1 = iparties[0]; p2 = iparties[1]; p3 = iparties[2]

'''Simulator'''
simulator = Sim_State('sid', 7, ledger_itm, state_itm, p3)
simitm = ITMAdversary('sid', 7)
simitm.init(simulator)
comm.setAdversary(simitm)
gevent.spawn(simitm.run)


'''
Deploy prereq contract
'''
class C_AUX:
    def __init__(self, address, call, out):
        self.address = address
        self.call = call
        self.out = out
        
    def init(self, tx):
        pass

    def test(self, tx):
        self.out('testtesttest')

caddr = z_deploy_contract(simparty, simitm, ledger_itm, C_AUX)
gevent.spawn(state_itm.run)

print('dump ready 1:', dump.dump_check())
z_mine_blocks(4, simparty, ledger_itm)
print('dump ready 2:', dump.dump_check())
exe(p1.input.set(('input', ('add',0))))
exe(p2.input.set(('input', ('add',0))))
exe(p3.input.set(('input', ('add',0))))


