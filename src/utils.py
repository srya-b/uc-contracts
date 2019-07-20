from __future__ import print_function
import inspect
import dump

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

def z_get_balance(itm, simparty, ledger):
    sender = (simparty.sid, simparty.pid)
    return ledger.subroutine_call((
        sender,
        True,
        ('getbalance', (itm.sid, itm.pid))
    ))


try:
    import __builtin__
except ImportError:
    import builtins as __builtin__

def print(*args, **kwargs):
    return __builtin__.print(*args, '\n', **kwargs)

