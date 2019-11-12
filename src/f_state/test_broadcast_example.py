
import dump
import comm
import gevent
from itm2 import PartyWrapper, ProtocolWrapper, FunctionalityWrapper, ITMAdversary2, DummyAdversary
from comm import P2F, P2G, F2G, A2G, A2P, Many2FChannel, M2F, Z2P, A2P, Z2A, GenChannel
from utils2 import z_mine_blocks, z_send_money, z_get_balance, z_get_leaks, z_tx_leak, z_tx_leaks, z_delay_tx, z_set_delays, z_deploy_contract, z_mint, z_start_ledger, z_ideal_parties, z_sim_party, z_genym, z_real_parties, z_mint_mine, z_prot_input, z_instant_input, z_inputs, z_tx_inputs, z_ping, z_read, z_start_clock, z_ainputs, z_crupt, wait_for, print
from contract1 import Contract1, U1
from f_broadcast import Broadcast_Functionality
from state_protocol import State_Protocol, Adv, State_Contract
from f_state import Sim_State2

advid = ('sid',7)

_a2z = GenChannel('a2z')
_z2a = GenChannel('z2a')
_z2p = GenChannel('z2p')
_p2z = GenChannel('p2z')
_f2p = GenChannel('f2p')
_p2f = GenChannel('p2f')
_a2p = GenChannel('a2p')
_p2a = GenChannel('p2a')
_a2f = GenChannel('a2f')
_f2a = GenChannel('f2a')
_z2f = GenChannel('z2f')
_f2z = GenChannel('f2z')

sp = ('hello',1)
p1 = ('hello',2)
p2 = ('hello',3)
p3 = ('hello',4)

advitm = DummyAdversary(advid[0], advid[1], _z2a, _a2z, _p2a, _a2p, _a2f, _f2a)
comm.setAdversary(advitm)
gevent.spawn(advitm.run)
 
p = PartyWrapper('hello', _z2p, _p2z, _f2p, _p2f, _a2p, _p2a)
gevent.spawn(p.run)
f = FunctionalityWrapper(_p2f, _f2p, _a2f, _f2a, _z2f, _f2z)
gevent.spawn(f.run)
f.newFID(420, 'G_clock')
f.newFID('hello', 'F_bcast', (3, 2, 3, 4))

z_inputs( ((420,'G_clock'), ('register',)), _z2p, _p2z, 2)

z_inputs( (('hello','F_bcast'), ('bcast', 'hello')), _z2p, _p2z, 3)
leaks = z_get_leaks(_z2a, _a2z, 'A2F', ('hello', 'F_bcast'))
assert len(leaks) == 1
m = leaks.pop()
msg,r = m
print('\n\t leaks from F_bcast', msg, r)


rnd = z_inputs( ((420,'G_clock'), ('clock-read',)), _z2p, _p2z, 4)
print('\n\t rnd', rnd)

z_inputs( ((420,'G_clock'), ('clock-update',)), _z2p, _p2z, 2,3,4)
z_ainputs( ('A2F', (('hello','F_bcast'), ('deliver',m,4))), _z2a, _a2z)
#
msg = wait_for(_p2z)
#r = gevent.wait(objects=[_p2z],count=1)
#r = r[0]
#msg = r.read()
print('\n\t from party', msg)

#z_ainputs( ('A2F', ('ping', ('hello','F_bcast'))), _z2a, _a2z)
#
#o = z_inputs( (('hello','F_bcast'), ('read',)), _z2p, _p2z, 2, 3, 4)
#print('\t\t\033[1mP1: {}\033[0m'.format(o[0][1]))
#print('\t\t\033[1mP2: {}\033[0m'.format(o[1][1]))
#print('\t\t\033[1mP3: {}\033[0m'.format(o[2][1]))


