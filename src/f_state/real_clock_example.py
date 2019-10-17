import dump
import comm
import gevent
from itm import ITMFunctionality, ITMPassthrough, ITMAdversary, createParties, ITMPrinterAdversary, ITMProtocol
from comm import P2F, P2G, F2G, A2G, A2P, Many2FChannel, M2F, Z2P, A2P, Z2A
from utils import z_mine_blocks, z_send_money, z_get_balance, z_get_leaks, z_tx_leak, z_tx_leaks, z_delay_tx, z_set_delays, z_deploy_contract, z_mint, z_start_ledger, z_ideal_parties, z_sim_party, z_genym, z_real_parties, z_mint_mine, z_prot_input, z_instant_input, z_inputs, z_tx_inputs, z_ping, z_read, z_read_print, z_start_clock, print
from g_ledger import Ledger_Functionality, LedgerITM
from g_clock import Clock_Functionality, ClockITM
from collections import defaultdict
from gevent.queue import Queue, Channel
from protected_wrapper import Protected_Wrapper, ProtectedITM
from f_state import StateChannel_Functionality, StateITM, Sim_State
from f_broadcast import Broadcast_Functionality, BroadcastITM
from state_protocol import State_Protocol, Adv, State_Contract
from contract1 import Contract1, U1

ledgerid = ('sid1',0)
clockid = ('sidc', 1)
statesid = 'sid2'
bcid = (statesid, 22)
advid = ('sid',7)
simpartyid = ('sid3',23)
statepartyids = [2,3,4]
p1id = (statesid, statepartyids[0])
p2id = (statesid, statepartyids[1])
p3id = (statesid, statepartyids[2])
zid = (-1,-1)

''' All of the channels for the functionalities '''
a2ledger = A2G(ledgerid,advid)
f2ledger = F2G(ledgerid,('sid2',1))
m2ledger = Many2FChannel(ledgerid)
p2ledger1 = M2F(p1id,m2ledger)
p2ledger2 = M2F(p2id,m2ledger)
p2ledger3 = M2F(p3id,m2ledger)
p2ledgers = [p2ledger1,p2ledger2,p2ledger3]

a2clock = A2G(clockid, advid)
m2clock = Many2FChannel(clockid)
p2clock1 = M2F(p1id, m2clock)
p2clock2 = M2F(p2id, m2clock)
p2clock3 = M2F(p3id, m2clock)
p2clocks = [p2clock1, p2clock2, p2clock3]
ledger2clock = M2F(ledgerid, m2clock)
f2clock = A2G(clockid, bcid)
#fstate2clock = M2F(fstateid, m2clock)
#fstate2clock = F2G(clockid, fstateid)
sp2clock = M2F(simpartyid, m2clock)

a2bc = A2G(bcid,advid)
f2bc = F2G(bcid, (None,-1))
m2bc = Many2FChannel(bcid)
p2bc1 = M2F(p1id,m2bc)
p2bc2 = M2F(p2id,m2bc)
p2bc3 = M2F(p3id,m2bc)
p2bcs = [p2bc1,p2bc2,p2bc3]

z2p1 = Z2P(p1id, zid)
z2p2 = Z2P(p2id, zid)
z2p3 = Z2P(p3id, zid)
z2ps = [z2p1,z2p2,z2p3]
a2p1 = A2P(p1id, advid)
a2p2 = A2P(p2id, advid)
a2p3 = A2P(p3id, advid)
a2ps = [a2p1,a2p2,a2p3]

z2sp = Z2P(simpartyid, zid)
a2sp = A2P(simpartyid, advid)
sp2f = M2F(simpartyid, m2ledger)
z2a = Z2A(advid, zid)

# choose leader and create channels
leader = p2id; leaderpid = p2id[1]
# clock
g_clock, clock_itm = z_start_clock(clockid[0], clockid[1], Clock_Functionality, ClockITM, a2clock, f2clock, m2clock) 
# Ledger
g_ledger, protected, ledger_itm = z_start_ledger(ledgerid[0],ledgerid[1],Ledger_Functionality,ProtectedITM, a2ledger, f2ledger, m2ledger)
# Broadcats channel
f_bc,bc_itm = BroadcastITM(bcid[0], bcid[1], ledger_itm, a2bc, f2bc, m2bc, *statepartyids)
#gevent.spawn(bc_itm.run)
# Simulated honest party
simparty = z_sim_party(simpartyid[0], simpartyid[1], ITMPassthrough, ledger_itm, a2sp, sp2f, z2sp)
#caddr1 = simparty.subroutine_call( ((-1,-1), True, ('get-caddress',)) )
#caddr2 = simparty.subroutine_call( ((-1,-1), True, ('get-caddress',)) )
simnonce = simparty.subroutine_call( ((-1,-1), True, ('get-nonce',)) )
print('\t\nsimnonce={}\n'.format(simnonce))
caddr1 = simparty.subroutine_call( ((-1,-1), True, ('compute-caddress',simnonce+1)) )
caddr2 = simparty.subroutine_call( ((-1,-1), True, ('compute-caddress',simnonce+2)) )
# real parties
prots = []
for pid,p2g,p2bc in zip(statepartyids,p2ledgers,p2bcs):
    prots.append(State_Protocol(statesid, pid, ledger_itm, bc_itm, caddr2, U1, p2g, p2bc, *statepartyids))
rparties = []

#select leader
leader = p2id; leaderpid = p2id[1]
m2leader = Many2FChannel(leaderpid)
p2leader1 = M2F(p1id, m2leader)
p2leader2 = M2F(p2id, m2leader)
p2leader3 = M2F(p3id, m2leader)
p2leaders = [p2leader1, p2leader2, p2leader3]
for pid,a2p,p2f,z2p in zip(statepartyids,a2ps,p2leaders,z2ps):
    rparties.append( ITMProtocol(statesid, pid, a2p, p2f, z2p) )
for prot,p in zip(prots,rparties):
    p.init(prot)

pleader = rparties[1]
pleader.add_channels(m2leader)
for p,p2l in zip(prots,p2leaders):
    p.set_leader(leaderpid,pleader,p2l)
#for p in rparties:
#    gevent.spawn(p.run)
comm.setParties(rparties)

# Adversaries
adversary = Adv(statesid, 7, ledger_itm, bc_itm, rparties[0], caddr2, a2ledger)
advitm = ITMAdversary(statesid, 7, z2a, a2p1, a2bc, a2ledger)
advitm.init(adversary); comm.setAdversary(advitm)
#gevent.spawn(advitm.run)

# set clocks
ledger_itm.set_clock(ledger2clock, g_clock)
g_ledger.set_clock(ledger2clock, g_clock)
bc_itm.set_clock(f2clock, g_clock)
for party,p2c in zip(rparties,p2clocks): party.set_clock(p2c, g_clock)
simparty.set_clock(sp2clock, g_clock)

# spawn itms
gevent.spawn(clock_itm.run)
gevent.spawn(ledger_itm.run)
gevent.spawn(simparty.run)
for party in rparties: gevent.spawn(party.run)
gevent.spawn(advitm.run)
gevent.spawn(bc_itm.run)

paddrs = [z_genym((_p.sid,_p.pid), ledger_itm) for _p in rparties]
#caddr = z_deploy_contract(z2sp, z2a, simparty, advitm, ledger_itm, Contract1, *paddrs)
aux_caddr = z_deploy_contract(z2sp, z2a, simparty, advitm, ledger_itm, Contract1, *paddrs)
assert aux_caddr == caddr1, '\tcaddr1={}, caddr2={}\n\taux={}\n'.format(caddr1,caddr2,aux_caddr)
state_caddr = z_deploy_contract(z2sp, z2a, simparty, advitm, ledger_itm, State_Contract, U1, aux_caddr, 8, paddrs)
assert state_caddr == caddr2, '\tcaddr1={}, caddr2={}\n\taux={} state={}\n'.format(caddr1,caddr2,aux_caddr,state_caddr)

z_inputs(('register',), z2p1, z2p2, z2p3)

print('*************************************************************')

z_mint_mine(z2sp, z2a, advitm, ledger_itm, *rparties)

try:
    import __builtin__
except ImportError:
    import builtins as __builtin__

def print(*args, **kwargs):
    return __builtin__.print(*args, **kwargs)
# TODO right now the clock starts at 0 for everyone when the first input is given by the environment
# this need to change and be tested to ensure that whenever parties register that's all that matters
z_inputs(('input','add', 0), z2p1)
z_inputs(('input','add', 0), z2p2)
z_inputs(('input','sub', 0), z2p3)
z_ping(z2p1); z_ping(z2p1)
z_ping(z2p2); z_ping(z2p2)
z_ping(z2p3); z_ping(z2p3)
z_inputs(('clock-update',), z2p1, z2p2, z2p3)
#z_mine_blocks(1, z2sp, z2sp.to)
z_ping(a2bc)
z_ping(z2p1); z_ping(z2p1)
z_ping(z2p2); z_ping(z2p2)
z_ping(z2p3); z_ping(z2p3)
z_inputs(('clock-update',), z2p1, z2p2, z2p3)
z_ping(a2bc)
z_ping(z2p1)
z_ping(z2p2)
z_ping(z2p3)
z_ping(z2p1)
z_ping(z2p2)
z_ping(z2p3)
#
#p1r = z_read(p1id,rparties[0])
#p2r = z_read(p2id,rparties[1])
#p3r = z_read(p3id,rparties[2])
#print('\t\tREAD OUTPUT')
#print('p1', p1r, '\n')
#print('p1', p1r, '\n')
#print('p2', p2r, '\n')
#print('p3', p3r, '\n')
#
#
z_inputs(('input','add', 1), z2p1)
z_inputs(('input','add', 1), z2p2)
z_inputs(('input','sub', 1), z2p3)
z_inputs(('clock-update',), z2p1, z2p2, z2p3)
##z_mine_blocks(1, z2sp, z2sp.to)
z_ping(a2bc)
z_ping(z2p1)
z_ping(z2p1)
z_ping(z2p2)
z_ping(z2p2)
z_ping(z2p3)
z_ping(z2p3)
z_inputs( ('write', p2ledger1, ('transfer', state_caddr, 0, ('dispute',(0,)), 'NA')), z2p1 )
z_set_delays(z2a, advitm, ledger_itm, [0])
z_inputs(('clock-update',), z2p1, z2p2, z2p3)
z_mine_blocks(1, z2sp, z2sp.to)
z_ping(a2bc)
z_ping(z2p1)
z_ping(z2p2)
z_ping(z2p3)
#
#p1r = z_read(p1id,rparties[0])
#p2r = z_read(p2id,rparties[1])
#p3r = z_read(p3id,rparties[2])
#print('\t\tREAD OUTPUT')
#print('p1', p1r, '\n')
#print('p1', p1r, '\n')
#print('p2', p2r, '\n')
#print('p3', p3r, '\n')

#z_inputs(('input','sub', 2), z2p1)
#z_inputs(('input','sub', 2), z2p2)
#z_inputs(('input','sub', 2), z2p3)
#z_inputs(('clock-update',), z2p1, z2p2, z2p3)
##z_mine_blocks(1, z2sp, z2sp.to)
#z_ping(a2bc)
#z_ping(z2p1)
#z_ping(z2p2)
#z_ping(z2p3)
#z_inputs(('clock-update',), z2p1, z2p2, z2p3)
#z_ping(a2bc)
#z_ping(z2p1)
#z_ping(z2p2)
#z_ping(z2p3)
#
#p1r = z_read(p1id,rparties[0])
#p2r = z_read(p2id,rparties[1])
#p3r = z_read(p3id,rparties[2])
#print('\t\tREAD OUTPUT')
#print('p1', p1r, '\n')
#print('p1', p1r, '\n')
#print('p2', p2r, '\n')
#print('p3', p3r, '\n')
#
#
