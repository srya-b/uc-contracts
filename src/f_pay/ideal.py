import dump
import comm
import gevent
from itm import ITMFunctionality, ITMPassthrough, ITMAdversary, createParties, ITMPrinterAdversary
from comm import P2F, P2G, F2G, A2G, A2P, Many2FChannel, M2F, Z2P, A2P, Z2A
from utils import z_mine_blocks, z_send_money, z_get_balance, z_get_leaks, z_tx_leak, z_tx_leaks, z_delay_tx, z_set_delays, z_start_ledger, z_ideal_parties, z_sim_party, z_mint_mine, z_inputs, z_tx_inputs, z_ping, z_read, z_instant_input, print
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

ledgerid = ('sid1',0)
fpaysid = 'sid2'
fpayid = (fpaysid,1)
advid = ('sid',7)
simpartyid = ('sid3',23)
fpaypartyids = [2,3]
p1id = (fpaysid, fpaypartyids[0])
p2id = (fpaysid, fpaypartyids[1])
zid = (0,0)


''' All of the channels for the functionalities '''
a2ledger = A2G(ledgerid,advid)
f2ledger = F2G(ledgerid,('sid2',1))
m2ledger = Many2FChannel(ledgerid)
p2ledger1 = M2F(p1id,m2ledger)
p2ledger2 = M2F(p2id,m2ledger)

a2fpay = A2G(fpayid, advid)
f2fpay = F2G(fpayid, ('none',-1))
m2fpay = Many2FChannel(fpayid)
p2fpay1 = M2F(p1id, m2fpay)
p2fpay2 = M2F(p2id, m2fpay)

z2p1 = Z2P(p1id, zid)
z2p2 = Z2P(p2id, zid)
a2p1 = A2P(p1id, advid)
a2p2 = A2P(p2id, advid)

z2sp = Z2P(simpartyid, zid)
a2sp = A2P(simpartyid, advid)
sp2f = M2F(simpartyid, m2ledger)
z2a = Z2A(advid, zid)

# '''Blockchain Functionality'''
g_ledger, protected, ledger_itm = z_start_ledger(ledgerid[0],ledgerid[1],Ledger_Functionality,ProtectedITM, a2ledger, f2ledger, m2ledger)
comm.setFunctionality(ledger_itm)
# '''Payment Channel functionality'''
idealf, pay_itm = PayITM(fpayid[0], fpayid[1], ledger_itm, p1id[1], p2id[1], a2fpay, f2fpay, f2ledger, m2fpay)
comm.setFunctionality(pay_itm)
# '''Ideal world parties'''
iparties = z_ideal_parties(fpaysid, fpaypartyids, pay_itm, createParties, [a2p1,a2p2], [p2fpay1,p2fpay2], [z2p1,z2p2])
comm.setParties(iparties)
# ''' Extra party'''
simparty = z_sim_party(simpartyid[0], simpartyid[1], ITMPassthrough, ledger_itm, a2sp, sp2f, z2sp)
comm.setParty(simparty)
p1 = iparties[0]
p2 = iparties[1]

# '''Simulator spawn'''
simulator = Sim_Payment(advid[0], advid[1], ledger_itm, pay_itm, Adv, p2, Contract_Pay, a2p2, a2ledger)
simitm = ITMAdversary(advid[0], advid[1], z2a, a2p2, a2fpay, a2ledger)
simitm.init(simulator)
comm.setAdversary(simitm)
gevent.spawn(simitm.run)
print('P1:', p1.sid, p1.pid)
print('P2:', p2.sid, p2.pid)

# '''Start functionality itms'''
gevent.spawn(pay_itm.run)

z_mine_blocks(1, z2sp, z2sp.to)
z_mint_mine(z2sp, z2a, simitm, ledger_itm, p1, p2)
z_ping(z2p1); z_ping(z2p2)

try:
    import __builtin__
except ImportError:
    import builtins as __builtin__

def print(*args, **kwargs):
    return __builtin__.print(*args, **kwargs)

def mainmain(cmds):
    p1i = 0; p2i = 0
    p1d = 0; p2d = 0
    p1w = 0; p2w = 0
    for _cmd in cmds:
        cmd = _cmd.split(' ')
        if cmd[0] == 'pay':
            if cmd[1] == 'p1': 
                p1i = 1; 
                z_inputs(('pay',int(cmd[2])),z2p1)
            elif cmd[1] == 'p2': 
                p2i = 1; 
                z_inputs(('pay',int(cmd[2])),z2p2)
            if p1i + p2i == 2:
                z_ping(z2p1); z_ping(z2p2)
                p1i = 0; p2i = 0
        if cmd[0] == 'pass':
            if cmd[1] == 'p1':
                p1i = 1
                z_inputs(('input',[],0), z2p1)
            elif cmd[1] == 'p2':
                p2i = 1
                z_inputs(('input', [],0), z2p2)
        elif cmd[0] == 'deposit':
            if cmd[1] == 'p1':
                p1d = 1
                z_instant_input(z2p1, ('deposit', int(cmd[2])))
            elif cmd[1] == 'p2': 
                p2d = 1
                z_instant_input(z2p2, ('deposit', int(cmd[2])))
        elif cmd[0] == 'withdraw':
            if cmd[1] == 'p1': 
                p1w = 1
                z_inputs(('withdraw', int(cmd[2])), z2p1)
            elif cmd[1] == 'p2': 
                p2w = 1
                z_inputs(('withdraw', int(cmd[2])), z2p2)
        elif cmd[0] == 'blocks':
            z_mine_blocks(int(cmd[1]), z2sp, z2sp.to)
        elif cmd[0] == 'delay':
            d = [int(i) for i in cmd[1:]]
            z_set_delays(z2a, simitm, ledger_itm, d)
        elif cmd[0] == 'read':
            if cmd[1] == 'p1': # read output from p1
                z_ping(z2p1)
                p1r = z_read(p1id,p1)
                if p1r: print('p1', p1r,'\n')
            elif cmd[1] == 'p2': # read output from p2
                z_ping(z2p2)
                p2r = z_read(p2id,p2)
                if p2r: print('p2', p2r, '\n')

if __name__=='__main__':
    import sys
    fn = sys.argv[1]
    f = open(fn)
    cmds = []
    for line in f:
        if line == '\n':
            break
        cmds.append( line.strip() )
    mainmain(cmds)
    gevent.wait()

