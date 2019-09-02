import dump
import comm
import gevent
from itm import ITMFunctionality, ITMPassthrough, ITMAdversary, createParties, ITMPrinterAdversary, ITMProtocol
from comm import P2F, P2G, F2G, A2G, A2P, M2FChannel, M2F, Z2P, A2P, Z2A
from utils import z_mine_blocks, z_send_money, z_get_balance, z_get_leaks, z_tx_leak, z_tx_leaks, z_delay_tx, z_set_delays, z_deploy_contract, z_mint, z_start_ledger, z_ideal_parties, z_sim_party, z_genym, z_real_parties, z_mint_mine, z_prot_input, z_instant_input, z_inputs, z_tx_inputs, z_ping, print
from g_ledger import Ledger_Functionality, LedgerITM
from collections import defaultdict
from gevent.queue import Queue, Channel
from f_state import StateChannel_Functionality, StateITM, Sim_State
from pay_protocol import Contract_Pay, Pay_Protocol, Adv, U_Pay
from protected_wrapper import Protected_Wrapper, ProtectedITM

def exe(result): 
    dump.dump_wait()

ledgerid = ('sid1',0)
fstatesid = 'sid2'
fstateid = (fstatesid,1)
advid = ('sid',7)
simpartyid = ('sid3',23)
fstatepartyids = [2,3]
p1id = (fstatesid, fstatepartyids[0])
p2id = (fstatesid, fstatepartyids[1])
zid = (0,0)


''' All of the channels for the functionalities '''
a2ledger = A2G(ledgerid,advid)
f2ledger = F2G(ledgerid,('sid2',1))
m2ledger = M2FChannel(ledgerid)
p2ledger1 = M2F(p1id,m2ledger)
p2ledger2 = M2F(p2id,m2ledger)

a2fstate = A2G(fstateid, advid)
f2fstate = F2G(fstateid, ('none',-1))
m2fstate = M2FChannel(fstateid)
p2fstate1 = M2F(p1id, m2fstate)
p2fstate2 = M2F(p2id, m2fstate)

z2p1 = Z2P(p1id, zid)
z2p2 = Z2P(p2id, zid)
a2p1 = A2P(p1id, advid)
a2p2 = A2P(p2id, advid)

z2sp = Z2P(simpartyid, zid)
a2sp = A2P(simpartyid, advid)
sp2f = M2F(simpartyid, m2ledger)
z2a = Z2A(advid, zid)



'''Blockchain Functionality'''
#g_ledger, protected, ledger_itm = z_start_ledger('sid1',0,Ledger_Functionality,ProtectedITM)
g_ledger, protected, ledger_itm = z_start_ledger(ledgerid[0],ledgerid[1],Ledger_Functionality,ProtectedITM, a2ledger, f2ledger, m2ledger)
comm.setFunctionality(ledger_itm)
'''sim'd party'''
#simparty = z_sim_party('sid2',23,ITMPassthrough,ledger_itm)
simparty = z_sim_party(simpartyid[0], simpartyid[1], ITMPassthrough, ledger_itm, a2sp, sp2f, z2sp)
comm.setParty(simparty)
caddr = simparty.subroutine_call( ('get-caddress',) )
'''State Functionality'''
#idealf, state_itm = StateITM('sid2', 1, ledger_itm, caddr, U_Pay, f2ledger, 2,3)
idealf, state_itm = StateITM('sid2', 1, ledger_itm, caddr, U_Pay, a2fstate, f2fstate, f2ledger, m2fstate, 2,3)
comm.setFunctionality(state_itm)
gevent.spawn(state_itm.run)
''' Parites'''
rparties = z_real_parties('sid2', [2,3], ITMProtocol, Pay_Protocol, state_itm, ledger_itm, caddr, [a2p1,a2p2], [p2fstate1,p2fstate2], [p2ledger1, p2ledger2], [z2p1,z2p2])
comm.setParties(rparties)
pl = rparties[0]; pr = rparties[1]
'''Adversary'''
adversary = Adv('sid', 7, ledger_itm, state_itm, pr, Contract_Pay, a2fstate)
advitm = ITMAdversary('sid', 7, z2a, a2p2, a2fstate, a2ledger)
advitm.init(adversary)
comm.setAdversary(advitm)
gevent.spawn(advitm.run)

pladdr = z_genym((pl.sid,pl.pid), ledger_itm)
praddr = z_genym((pr.sid,pr.pid),ledger_itm)
print('pladdr', pladdr, 'praddr', praddr)
'''Deploy Contract_Pay'''
caddr = z_deploy_contract(z2sp, z2a, simparty, advitm, ledger_itm, Contract_Pay, pladdr, praddr)

'''
Ping F_state when you want the state to progress with an update.
Ping a party when you want its input to get sent to F_state
'''


z_inputs(('input',([],0)), z2p1, z2p2)
z_ping(z2p1); z_ping(z2p2)
z_mint_mine(z2sp, z2a, advitm, ledger_itm, pl, pr)
print('[GET BALANCE] \n\t', z_get_balance(pl, simparty, ledger_itm), '\n\t', z_get_balance(pr, simparty, ledger_itm), '\n\t', z_get_balance(simparty, simparty, ledger_itm))
z_tx_inputs(z2a, advitm, ledger_itm, ('deposit', 10), z2sp, z2p1, z2p2)
z_ping(a2fstate)
z_inputs(('pay', 2), z2p1)
z_ping(z2p1)
z_mine_blocks(9, z2sp, z2sp.to)
z_ping(a2fstate)

print('[GET BALANCE] \n\t', z_get_balance(pl, simparty, ledger_itm), '\n\t', z_get_balance(pr, simparty, ledger_itm), '\n\t', z_get_balance(simparty, simparty, ledger_itm))

z_inputs(('withdraw',5), z2p2)
z_inputs(('pay',2), z2p2)
z_ping(z2p2)
z_mine_blocks(9, z2sp, z2sp.to)
z_ping(a2fstate)

z_set_delays(z2a, advitm, ledger_itm, [0])
z_mine_blocks(1, z2sp, z2sp.to)

z_inputs(('pay',2), z2p2)
z_ping(z2p2)
z_mine_blocks(9, z2sp, z2sp.to)
z_ping(a2fstate)
z_ping(z2p2)
z_ping(z2p1)

print('[GET BALANCE] \n\t', z_get_balance(pl, simparty, ledger_itm), '\n\t', z_get_balance(pr, simparty, ledger_itm), '\n\t', z_get_balance(simparty, simparty, ledger_itm))
