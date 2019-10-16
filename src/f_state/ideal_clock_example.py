import dump
import comm
import gevent
from itm import ITMFunctionality, ITMPassthrough, ITMAdversary, createParties, ITMPrinterAdversary, ITMProtocol
from comm import P2F, P2G, F2G, A2G, A2P, Many2FChannel, M2F, Z2P, A2P, Z2A
from utils import z_mine_blocks, z_send_money, z_get_balance, z_get_leaks, z_tx_leak, z_tx_leaks, z_delay_tx, z_set_delays, z_deploy_contract, z_mint, z_start_ledger, z_ideal_parties, z_sim_party, z_genym, z_real_parties, z_mint_mine, z_prot_input, z_instant_input, z_inputs, z_tx_inputs, z_ping, z_read, z_start_clock, print
from g_ledger import Ledger_Functionality, LedgerITM
from g_clock import Clock_Functionality, ClockITM
from collections import defaultdict
from gevent.queue import Queue, Channel
from f_state import StateChannel_Functionality, StateITM, Sim_State
from protected_wrapper import Protected_Wrapper, ProtectedITM
from contract1 import Contract1, U1

ledgerid = ('sid1',0)
clockid = ('sidc', 1)
fstatesid = 'sid2'
fstateid = (fstatesid,1)
advid = ('sid',7)
simpartyid = ('sid3',23)
fstatepartyids = [2,3,4]
p1id = (fstatesid, fstatepartyids[0])
p2id = (fstatesid, fstatepartyids[1])
p3id = (fstatesid, fstatepartyids[2])
zid = (0,0)

# ''' All of the channels for the functionalities '''
a2ledger = A2G(ledgerid,advid)
f2ledger = F2G(ledgerid,('sid2',1))
m2ledger = Many2FChannel(ledgerid)
p2ledger1 = M2F(p1id,m2ledger)
p2ledger2 = M2F(p2id,m2ledger)
p2ledger3 = M2F(p3id,m2ledger)

a2clock = A2G(clockid, advid)
m2clock = Many2FChannel(clockid)
p2clock1 = M2F(p1id, m2clock)
p2clock2 = M2F(p2id, m2clock)
p2clock3 = M2F(p3id, m2clock)
p2clocks = [p2clock1, p2clock2, p2clock3]
ledger2clock = M2F(ledgerid, m2clock)
#fstate2clock = M2F(fstateid, m2clock)
fstate2clock = F2G(clockid, fstateid)
sp2clock = M2F(simpartyid, m2clock)

a2fstate = A2G(fstateid, advid)
f2fstate = F2G(fstateid, ('none',-1))
m2fstate = Many2FChannel(fstateid)
p2fstate1 = M2F(p1id, m2fstate)
p2fstate2 = M2F(p2id, m2fstate)
p2fstate3 = M2F(p3id, m2fstate)

z2p1 = Z2P(p1id, zid)
z2p2 = Z2P(p2id, zid)
z2p3 = Z2P(p3id, zid)
a2p1 = A2P(p1id, advid)
a2p2 = A2P(p2id, advid)
a2p3 = A2P(p3id, advid)

z2sp = Z2P(simpartyid, zid)
a2sp = A2P(simpartyid, advid)
sp2f = M2F(simpartyid, m2ledger)
z2a = Z2A(advid, zid)

# clock
g_clock, clock_itm = z_start_clock(clockid[0], clockid[1], Clock_Functionality, ClockITM, a2clock, fstate2clock, m2clock) 
# Ledger
g_ledger, protected, ledger_itm = z_start_ledger(ledgerid[0],ledgerid[1],Ledger_Functionality,ProtectedITM, a2ledger, f2ledger, m2ledger)
# Simulated honest party
simparty = z_sim_party(simpartyid[0], simpartyid[1], ITMPassthrough, ledger_itm, a2sp, sp2f, z2sp)
caddr = simparty.subroutine_call( ((-1,-1), True, ('get-caddress',)) )
# F_state
idealf, state_itm = StateITM('sid2', 1, ledger_itm, caddr, U1, a2fstate, f2fstate, f2ledger, m2fstate, 2,3,4)
# Parties
iparties = z_ideal_parties(fstatesid, fstatepartyids, state_itm, createParties, [a2p1,a2p2,a2p3], [p2fstate1,p2fstate2,p2fstate3], [z2p1,z2p2,z2p3])
comm.setParties(iparties)
p1 = iparties[0]; p2 = iparties[1]; p3 = iparties[2]
# Simulator
simulator = Sim_State(advid[0], advid[1], ledger_itm, state_itm, p2, Contract1, a2p2, a2ledger)
simitm = ITMAdversary(advid[0], advid[1], z2a, a2p2, a2fstate, a2ledger)
simitm.init(simulator)
comm.setAdversary(simitm)

# set clocks
ledger_itm.set_clock(ledger2clock, g_clock)
g_ledger.set_clock(ledger2clock, g_clock)
state_itm.set_clock(fstate2clock, g_clock)
for party,p2c in zip(iparties,p2clocks): party.set_clock(p2c, g_clock)
simparty.set_clock(sp2clock, g_clock)

# spawn all the itms
gevent.spawn(clock_itm.run)
gevent.spawn(ledger_itm.run)
gevent.spawn(simparty.run)
gevent.spawn(state_itm.run)
for party in iparties: gevent.spawn(party.run)
gevent.spawn(simitm.run)

#p1addr = z_genym((p1.sid,p1.pid), ledger_itm)
#p2addr = z_genym((p2.sid,p2.pid), ledger_itm)
#p3addr = z_genym((p3.sid,p3.pid), ledger_itm)
p1addr = p1.sender; p2addr = p2.sender; p3addr = p3.sender
caddr = z_deploy_contract(z2sp, z2a, simparty, simitm, ledger_itm, Contract1, p1addr, p2addr, p3addr)

z_inputs(('register',), z2p1, z2p2, z2p3)

for p in iparties:
    print('round', p.clock_read())

z_inputs(('input',0), z2p1, z2p2, z2p3)
z_inputs(('clock-update',), z2p1, z2p2, z2p3)
for p in iparties:
    print('round', p.clock_read())
z_ping(a2fstate)
z_ping(z2p1, z2p2, z2p3)

#z_inputs(('input',0), z2p1, z2p2, z2p3)
z_mine_blocks(1, z2sp, z2sp.to)
#z_ping(a2fstate)
##z_ping(z2p1, z2p2, z2p3)
#
z_mint_mine(z2sp, z2a, simitm, ledger_itm, p1, p2, p3)

try:
    import __builtin__
except ImportError:
    import builtins as __builtin__

def print(*args, **kwargs):
    return __builtin__.print(*args, **kwargs)


z_inputs(('input', 'add',),z2p1)
z_inputs(('input', 'add',),z2p2)
z_inputs(('input', 'sub',),z2p3)
z_inputs(('clock-update',), z2p1, z2p2, z2p3)
#z_mine_blocks(1, z2sp, z2sp.to)
z_ping(a2fstate)
p1r = z_read(p1id, p1); p2r = z_read(p2id, p2); p3r = z_read(p3id, p3)
if p1r: print('p1',p1r,'\n')
if p2r: print('p2',p2r,'\n')
if p3r: print('p3',p3r,'\n')

z_inputs(('input', 'add',),z2p1)
z_inputs(('input', 'add',),z2p2)
z_inputs(('input', 'sub',),z2p3)
z_inputs(('clock-update',), z2p1, z2p2, z2p3)
#z_mine_blocks(1, z2sp, z2sp.to)
z_ping(a2fstate)
p1r = z_read(p1id, p1); p2r = z_read(p2id, p2); p3r = z_read(p3id, p3)
if p1r: print('p1',p1r,'\n')
if p2r: print('p2',p2r,'\n')
if p3r: print('p3',p3r,'\n')
#
z_inputs(('input', 'sub',),z2p1)
z_inputs(('input', 'sub',),z2p2)
z_inputs(('input', 'sub',),z2p3)
z_mine_blocks(1, z2sp, z2sp.to)
z_inputs(('clock-update',), z2p1, z2p2, z2p3)
z_ping(a2fstate)
p1r = z_read(p1id, p1); p2r = z_read(p2id, p2); p3r = z_read(p3id, p3)
if p1r: print('p1',p1r,'\n')
if p2r: print('p2',p2r,'\n')
if p3r: print('p3',p3r,'\n')
#   #
#   #
#   ### tx input
#   print('p2ledger2', p2ledger2)
#   z_inputs( ('write', p2ledger2, ('transfer', caddr, 0, ('mult', (25,)), 'doesnt matter')), z2p2)
#   z_set_delays(z2a, simitm, ledger_itm, [0])
#   z_mine_blocks(1, z2sp, z2sp.to)
#   z_inputs(('input', 'sub',),z2p1)
#   z_inputs(('input', 'sub',),z2p2)
#   z_inputs(('input', 'sub',),z2p3)
#   z_inputs(('clock-update',), z2p1, z2p2, z2p3)
#   z_ping(a2fstate)
#   p1r = z_read(p1id, p1); p2r = z_read(p2id, p2); p3r = z_read(p3id, p3)
#   if p1r: print('p1',p1r,'\n')
#   if p2r: print('p2',p2r,'\n')
#   if p3r: print('p3',p3r,'\n')
#   #
#   z_inputs(('input', 'pass',),z2p1)
#   z_inputs(('input', 'pass',),z2p2)
#   z_inputs(('input', 'pass',),z2p3)
#   z_inputs(('clock-update',), z2p1, z2p2, z2p3)
#   #z_mine_blocks(1, z2sp, z2sp.to)
#   z_ping(a2fstate)
#   p1r = z_read(p1id, p1); p2r = z_read(p2id, p2); p3r = z_read(p3id, p3)
#   if p1r: print('p1',p1r,'\n')
#   if p2r: print('p2',p2r,'\n')
#   if p3r: print('p3',p3r,'\n')
