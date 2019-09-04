import dump
import comm
import gevent
from itm import ITMFunctionality, ITMPassthrough, ITMAdversary, createParties, ITMPrinterAdversary, ITMProtocol
from comm import P2F, P2G, F2G, A2G, A2P, Many2FChannel, M2F, Z2P, A2P, Z2A
from utils import z_mine_blocks, z_send_money, z_get_balance, z_get_leaks, z_tx_leak, z_tx_leaks, z_delay_tx, z_set_delays, z_deploy_contract, z_mint, z_start_ledger, z_ideal_parties, z_sim_party, z_genym, z_real_parties, z_mint_mine, z_prot_input, z_instant_input, z_inputs, z_tx_inputs, z_ping, print
from g_ledger import Ledger_Functionality, LedgerITM
from collections import defaultdict
from gevent.queue import Queue, Channel
from f_state import StateChannel_Functionality, StateITM, Sim_State
from pay_protocol import Contract_Pay, Pay_Protocol, Adv, U_Pay
from protected_wrapper import Protected_Wrapper, ProtectedITM

# COMMON
ledgersid = 'sid1'; ledgerpid = 0; ledgerid = (ledgersid,ledgerpid)
p1pid = 2; p1id = (fstatesid, p1pid)
p2pid = 3; p2id = (fstatesid, p2pid)
spsid = 'abcd'; sppid = 23; spid = (spsid,spipid)
zid = (0,0)

# REAL WORLD INIT
fstatesid = 'sid2'; fstatepid = 1; fstateid = (fstatesid, fstatepid)
advsid = 'sid'; advpid = 7; advid = (advsid,advpid)

# IDEAL WORLD INIT
fpaysid = 'sid2'; fpaypid = 1; fpayid = (fpaysid,fpaypid)
simsid = 'sid'; simpid = 7; simid = (simsid,simpid)

# Real World Channels - Ledger
r_a2ledger = A2G(ledgerid,advid)
r_f2ledger = F2G(ledgerid,fstateid)
r_m2ledger = Many2FChannel(ledgerid)
r_p12ledger = M2F(p1id,r_m2ledger)
r_p22ledger = M2F(p2id,r_m2ledger)
r_sp2ledger = M2F(spid,r_m2ledger)

# Real World Channels - Fstate
r_a2fstate = A2G(fstateid,advid)
r_m2fstate = Many2FChannel(fstateid)
r_p12fstate = M2F(p1id, r_m2fstate)
r_p22fstate = M2F(p2id, r_m2fstate)

# Real World Channels - Env
r_z2p1 = Z2P(p1id, zid)
r_z2p2 = Z2P(p2id, zid)
r_z2sp = Z2P(spid, zid)
r_z2a = Z2A(advid, zid)

# Real World Channels - Adv
r_a2p1 = A2P(p1id, advid)
r_a2p2 = A2P(p2id, advid)

# Ideal World Channels - Ledger
i_a2ledger = A2G(ledgerid,simid)
i_f2ledger = F2G(ledgerid,fpayid)
i_m2ledger = Many2FChannel(ledgerid)
i_p12ledger = M2F(p1id,i_m2ledger)
i_p22ledger = M2F(p2id,i_m2ledger)
i_sp2ledger = M2F(spid,i_m2ledger)

# Ideal World Channels - Fpay
i_a2fstate = A2G(fpayid,simid)
i_m2fstate = Many2FChannel(fpayid)
i_p12fstate = M2F(p1id, i_m2fpay)
i_p22fstate = M2F(p2id, i_m2fpay)

# Ideal World Channels - Env
i_z2p1 = Z2P(p1id, zid)
i_z2p2 = Z2P(p2id, zid)
i_z2sp = Z2P(spid, zid)
i_z2a = Z2A(simid, zid)

# Ideal World Channels - Adv
i_a2p1 = A2P(p1id, simid)
i_a2p2 = A2P(p2id, simid)







