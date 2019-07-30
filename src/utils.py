from __future__ import print_function
import inspect
import dump
import gevent 

def contracts_same(contract1, contract2):
    type1 = type(contract1)
    type2 = type(contract2)

    return inspect.getsource(type1).split(':',1)[1] == inspect.getsource(type2).split(':',1)[1]

def z_mine_blocks(n, itm, ledger):
    sender = (itm.sid, itm.pid)
    for i in range(n):
        #itm.input.set( ('tick', sender) )
        #ledger.input.set((
        #    sender,
        #    True,
        #    ('tick', sender)
        #))
        itm.input.set( ('tick', (itm.sid, itm.pid)) )
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

def z_delay_tx(adv, fro, nonce, rounds):
    adv.input.set( ('delay-tx', fro, nonce, rounds) )
    dump.dump_wait()

def z_get_leaks(itm, ledger):
    sender = (itm.sid, itm.pid)
    itm.input.set( ('get-leaks', (ledger.sid, ledger.pid)) )
    #return ledger.subroutine_call((
    #    sender,
    #    True,
    #    ('get-leaks',)
    #))
    dump.dump_wait()

def z_set_delays(itm, ledger, delays):
    z_get_leaks(itm,ledger)
    leaks = itm.leakbuffer.pop(0)
    
    for i,(delay,leak) in enumerate(zip(delays,z_tx_leaks(leaks))):
        fro,nonce = leak
        z_delay_tx(itm, fro, nonce, delay)
        print('(from,nonce)=({},{}), delay={}'.format(fro,nonce,delay))
    print('delays={}, leaks={}, iterations={}'.format(len(delays), len(leaks), i+1))

    print("Dome with all the leaks")

def z_mine_block_perm(perm, itm):
    itm.input.set(
        ('tick', perm)
    )
    dump.dump_wait()


def z_send_money(v, to, itm, ledger):
    sender = (itm.sid, itm.pid)
    
    #ledger.input.set((
    #    sender,
    #    True,
    #    ('transfer', (to.sid,to.pid), v, (), 'does not matter')
    #))

    itm.input.set(
        ('transfer', (to.sid, to.pid), v, (), 'does not matter')
    )
    dump.dump_wait()

def z_send_tx(val, to, data, itm, ledger):
    itm.input.set(
        ('transfer', (to.sid,ro.pid), val, data, 'doest matter') 
    )
    dump.dump_wait()

def z_get_balance(itm, simparty, ledger):
    sender = (simparty.sid, simparty.pid)
    return ledger.subroutine_call((
        sender,
        True,
        ('getbalance', (itm.sid, itm.pid))
    ))

def z_deploy_contract(itm, adv, ledger, contract):
    caddr = itm.subroutine_call( ('get-caddress',) )
    
    itm.input.set(
        ('contract-create', caddr, 0, (contract,()), False, 'bad')
    )
    dump.dump_wait()
    z_set_delays(adv, ledger, [0])
    z_mine_blocks(1, itm, ledger)
    return caddr

def z_mint(itm, ledger, *to):
    for t in to:
        z_send_money(10, to, itm, ledger)
    z_set_delays(itm, ledger, [0 for _ in range(len(t))])
    z_mine_blocks(1, itm, ledger)

def z_start_ledger(sid, pid, cledger, cwrapperitm):
    g_ledger = cledger(sid,pid)
    protected, ledger_itm = cwrapperitm(sid,pid,g_ledger)
    gevent.spawn(ledger_itm.run)
    return g_ledger, protected, ledger_itm

def z_ideal_parties(sid,pids,itm,f):
    iparties = f(sid,pids,itm)
    for party in iparties:
        gevent.spawn(party.run)
    return iparties

def z_sim_party(sid,pid,citm,itm):
    simparty = citm(sid,pid)
    simparty.init(itm)
    gevent.spawn(simparty.run)
    return simparty

try:
    import __builtin__
except ImportError:
    import builtins as __builtin__

def print(*args, **kwargs):
    return __builtin__.print(*args, '\n', **kwargs)

