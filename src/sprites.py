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
idealfsid = 'sid2'
p1pid = 2; p1id = (idealfsid, p1pid)
p2pid = 3; p2id = (idealfsid, p2pid)
spsid = 'abcd'; sppid = 23; spid = (spsid,sppid)
zid = (0,0)

# REAL WORLD INIT
fstatepid = 1; fstateid = (idealfsid, fstatepid)
advsid = 'sid'; advpid = 7; advid = (advsid,advpid)

# IDEAL WORLD INIT
fpaypid = 1; fpayid = (idealfsid,fpaypid)
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
i_a2fpay = A2G(fpayid,simid)
i_m2fpay = Many2FChannel(fpayid)
i_p12fpay = M2F(p1id, i_m2fpay)
i_p22fpay = M2F(p2id, i_m2fpay)

# Ideal World Channels - Env
i_z2p1 = Z2P(p1id, zid)
i_z2p2 = Z2P(p2id, zid)
i_z2sp = Z2P(spid, zid)
i_z2a = Z2A(simid, zid)

# Ideal World Channels - Adv
i_a2p1 = A2P(p1id, simid)
i_a2p2 = A2P(p2id, simid)


# Real Ledger
r_ledger,_,r_ledger_itm = z_start_ledger(*ledgerid, Ledger_Functionality, ProtectedITM, r_a2ledger, r_f2ledger, r_m2ledger)
# Ideal Ledger
i_ledger,_,i_ledger_itm = z_start_ledger(*ledgerid, Ledger_Functionality, ProtectedITM, i_a2ledger, i_f2ledger, i_m2ledger)
# Honest Party Simulated by Environment - Real
r_simparty = z_sim_party(*spid, ITMPassthrough, r_ledger_itm, "NONE", r_sp2ledger, r_z2sp)
# Honest Party - Ideal
i_simparty = z_sim_party(*spid, ITMPassthrough, i_ledger_itm, None, i_sp2ledger, i_z2sp)
# F_state - Real
r_fstate,state_itm = StateITM(*fstateid, r_ledger_itm, "TODO", U_Pay, r_a2fstate, "TODO", r_f2ledger, r_m2fstate, p1pid, p2pid)
# F_pay - Ideal
i_fpay,pay_itm = PayITM(*fpayid, i_ledger_itm, p1pid, p2pid, i_a2fpa, None, 



