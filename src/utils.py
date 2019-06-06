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

def z_mine_block_perm(perm, itm):
    itm.input.set(
        ('tick', perm)
    )
    dump.dump_wait()


def z_send_money(v, to, itm, ledger):
    sender = (itm.sid, itm.pid)
    
    ledger.input.set((
        sender,
        True,
        ('transfer', (to.sid,to.pid), v, (), 'does not matter')
    ))
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

