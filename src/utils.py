from __future__ import print_function
import inspect
import dump
import gevent 
import comm
from collections import defaultdict

global pouts
pouts = defaultdict(list)

def z_write(fro, msg):
    global pouts
    pouts[fro].append(msg)

def z_read(fro,p):
    p.subroutine_call( ((-1,-1),True,('read',)))
    global pouts
    return pouts[fro]

def gwrite(color, fro, to, msg):
    pass#print(u'\033[{}{:>20}\033[0m -----> {}, msg={}'.format(color, fro, str(to), msg))

def _write(to, msg):
#    print('\033[94m{:>20}\033[0m -----> {}, msg={}'.format('Environment', str(comm.getitm(*to)), msg))
    gwrite(u'94m', 'Environment', comm.getitm(*to), msg)

try:
    import __builtin__
except ImportError:
    import builtins as __builtin__

def print(*args, **kwargs):
    pass#return __builtin__.print(*args, **kwargs)

def contracts_same(contract1, contract2):
    type1 = type(contract1)
    type2 = type(contract2)

    return inspect.getsource(type1).split(':',1)[1] == inspect.getsource(type2).split(':',1)[1]

#def z_mine_blocks(n, itm, ledger):
def z_mine_blocks(n, z2p, receiver):
    #sender = (itm.sid, itm.pid)
    for i in range(n):
        #itm.input.set( ('tick', sender) )
        #ledger.input.set((
        #    sender,
        #    True,
        #    ('tick', sender)
        #))
        msg = ('tick', receiver)
        _write(z2p.to, msg)
        z2p.write( msg )
        #itm.input.set( msg )
        dump.dump_wait()

#def z_mine_block_perm(perm, itm, ledger):
#    sender = (itm.sid,itm.pid)
#    ledger.backdoor.set((
#        sender,
#        True,
#        (True, ('tick', perm))
#    ))
#    dump.dump_wait()

def z_tx_leak(msg):
    _,leaks = msg
    sender,leak = leaks[0]
    fro,tx = leak
    fro,nonce = fro
    return fro,nonce

def z_tx_leaks(msg):
    _,leaks = msg
    for sender,leak in leaks:
        fro,tx = leak
        fro,nonce = fro
        yield fro,nonce

#def z_delay_tx(adv, fro, nonce, rounds):
def z_delay_tx(z2a, fro, nonce, rounds):
    #adv.input.set( ('delay-tx', fro, nonce, rounds) )
    z2a.write( ('delay-tx', fro, nonce, rounds) )
    dump.dump_wait()

#def z_get_leaks(itm, ledger):
def z_get_leaks(z2a, ledger):
    #sender = (itm.sid, itm.pid)
    msg = ('get-leaks', (ledger.sid, ledger.pid))
    _write(z2a.to, msg)
    #itm.input.set( msg  )
    z2a.write( msg )
    #return ledger.subroutine_call((
    #    sender,
    #    True,
    #    ('get-leaks',)
    #))
    dump.dump_wait()

#def z_set_delays(itm, ledger, delays):
def z_set_delays(z2a, itm, ledger, delays):
    #z_get_leaks(itm,ledger)
    z_get_leaks(z2a, ledger)
    leaks = itm.leakbuffer.pop(0)
    
    for i,(delay,leak) in enumerate(zip(delays,z_tx_leaks(leaks))):
        fro,nonce = leak
        #z_delay_tx(itm, fro, nonce, delay)
        z_delay_tx(z2a, fro, nonce, delay)
        #print('(from,nonce)=({},{}), delay={}'.format(fro,nonce,delay))
    #print('delays={}, leaks={}, iterations={}'.format(len(delays), len(leaks), i+1))

def z_mine_block_perm(perm, itm):
    msg = ('tick', perm)
    _write(itm,msg)
    itm.input.set(msg)
    dump.dump_wait()


#def z_send_money(v, to, itm, ledger):
def z_send_money(v, to, z2p):
    #sender = (itm.sid, itm.pid)
    
    #ledger.input.set((
    #    sender,
    #    True,
    #    ('transfer', (to.sid,to.pid), v, (), 'does not matter')
    #))
    msg = ('transfer', (to.sid, to.pid), v, (), 'does not matter')
    _write(z2p.to,msg)
    #itm.input.set( msg )
    z2p.write( msg )
    dump.dump_wait()

def z_send_tx(val, to, data, itm, ledger):
    msg = ('transfer', (to.sid,ro.pid), val, data, 'doest matter')
    _write(itm, msg)
    itm.input.set(msg )
    dump.dump_wait()

def z_get_balance(itm, simparty, ledger):
    sender = (simparty.sid, simparty.pid)
    return ledger.subroutine_call((
        sender,
        True,
        ('getbalance', (itm.sid, itm.pid))
    ))

def z_genym(sender, itm):
    addr = itm.subroutine_call((sender, True, ('genym',)))
    return addr

#def z_deploy_contract(itm, adv, ledger, contract, *args):
def z_deploy_contract(z2sp, z2a, itm, adv, ledger, contract, *args):
    caddr = itm.subroutine_call( ('get-caddress',) )
    
    #itm.input.set(
    #    ('contract-create', caddr, 0, (contract,args), False, 'bad')
    #)
    z2sp.write(
        ('contract-create', caddr, 0, (contract,args), False, 'bad')
    )
    dump.dump_wait()
    z_set_delays(z2a, adv, ledger, [0])
    #z_mine_blocks(1, itm, ledger)
    z_mine_blocks(1, z2sp, z2sp.to)
    return caddr

#def z_ping(itm):
def z_ping(*z2ps):
    for z2p in z2ps:
        z_inputs(('ping',),z2p)

def z_mint(itm, adv, ledger, *to):
    for t in to:
        z_send_money(10, t, itm, ledger)
    z_set_delays(adv, ledger, [0 for _ in range(len(to))])

#def z_prot_input(itm, msg):
def z_prot_input(z2p, msg):
    _write(z2p.to, msg)
    #itm.input.set( (itm.sender, True, msg) )
    z2p.write( msg )
    dump.dump_wait()

def z_instant_input(z2p, msg):
    z_prot_input(z2p, msg)

def z_tx_inputs(z2a, adv, ledger, msg, z2sp, *z2ps):
    #for itm in itms:
    for z2p in z2ps:
        #z_instant_input(itm, msg)
        z_instant_input(z2p, msg)
    #z_set_delays(adv, ledger, [0 for _ in itms])
    z_set_delays(z2a, adv, ledger, [0 for _ in z2ps])
    #z_mine_blocks(1, simparty, ledger)
    z_mine_blocks(1, z2sp, z2sp.to) 

def z_inputs(msg, *z2ps):
    #for itm in itms:
    for z2p in z2ps:
        z_instant_input(z2p, msg)

def z_mint_mine(z2p, z2a, adv, ledger, *to):
    for t in to:
        #z_send_money(10, t, itm, ledger)
        z_send_money(10, t, z2p)
    #z_set_delays(adv, ledger, [0 for _ in range(len(to))])
    z_set_delays(z2a, adv, ledger, [0 for _ in range(len(to))]) 
    #z_mine_blocks(1, itm, ledger)
    z_mine_blocks(1, z2p, z2p.to)

def z_start_ledger(sid, pid, cledger, cwrapperitm, a2f, f2f, p2f):
    g_ledger = cledger(sid,pid)
    protected, ledger_itm = cwrapperitm(sid,pid,g_ledger, a2f, f2f, p2f)
    gevent.spawn(ledger_itm.run)
    comm.setFunctionality(ledger_itm)
    return g_ledger, protected, ledger_itm

def z_ideal_parties(sid,pids,itm,f, a2ps, p2fs, z2ps):
    iparties = f(sid,pids,itm, a2ps, p2fs, z2ps)
    for party in iparties:
        gevent.spawn(party.run)
    return iparties

def z_real_parties(sid,pids,citm,protocol,functionality,G,C, a2ps, p2fs, p2gs, z2ps):
    prots = [protocol(sid,pid,functionality,G,C, p2f, p2g) for pid,p2f,p2g in zip(pids,p2fs,p2gs)]
    parties = [citm(sid,pid,a2p,p2f,z2p) for pid,a2p,p2f,z2p in zip(pids,a2ps,p2fs,z2ps)]
    assert len(prots) == len(parties)
    for prot,p in zip(prots,parties):
        p.init(prot)
    for p in parties:
        gevent.spawn(p.run)
    comm.setParties(parties)
    return parties

def z_sim_party(sid,pid,citm,itm, a2p, p2f, z2p):
    simparty = citm(sid,pid, a2p, p2f, z2p)
    simparty.init(itm)
    gevent.spawn(simparty.run)
    comm.setParty(simparty)
    return simparty

