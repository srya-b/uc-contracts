from __future__ import print_function
import inspect
import dump
import gevent 
import comm
from collections import defaultdict

global pouts
pouts = defaultdict(list)

def z_write(fro, msg):
    #curframe = inspect.currentframe()
    #calframe = inspect.getouterframes(curframe, 2)
    #print('caller name:', calframe[1][3])
    global pouts
    #print('\t\tbefore', fro, pouts[fro])
    pouts[fro].append(msg)
    #print('\t\tpouts', fro, pouts[fro])

def z_read(fro,p):
    p.subroutine_call( ((-1,-1),True,('read',)))
    global pouts
    return pouts[fro]

def z_read_print(fro,p,s):
    p.subroutine_call( ((-1,-1), True, ('read',)))
    global pouts
    if pouts[fro]:
        print(s, pouts[fro], '\n')
        return pouts[fro]

def gwrite(color, fro, to, msg):
    print(u'\033[{}{:>20}\033[0m -----> {}, msg={}'.format(color, fro, str(to), msg))

def _write(to, msg):
    gwrite(u'94m', 'Environment', comm.getitm(*to), msg)

try:
    import __builtin__
except ImportError:
    import builtins as __builtin__

def print(*args, **kwargs):
    return __builtin__.print(*args, **kwargs)

def contracts_same(contract1, contract2):
    type1 = type(contract1)
    type2 = type(contract2)

    return inspect.getsource(type1).split(':',1)[1] == inspect.getsource(type2).split(':',1)[1]

def z_mine_blocks(z2p, p2z, sid, pid, n):
    for i in range(n):
        z2p.write(( 1, ((69,'G_ledger'), ('tick', (sid,pid)))) )
        resp = wait_for(p2z)
        return resp

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

def z_delay_tx(z2a, a2z, fro, nonce, rounds):
    z2a.write( ('A2F', ('delay-tx', fro, nonce, rounds)) )
    resp = wait_for(a2z)
    return resp

#def z_get_leaks(z2a, a2z, t, fro):
#    msg = (t, ('get-leaks', fro))
#    z2a.write( msg )
#    resp = wait_for(a2z)
#    return resp

def z_get_leaks(z2a, a2z, t, fro):
    msg = (t, (fro, ('get-leaks',)))
    z2a.write( msg )
    resp = wait_for(a2z)
    return resp

def z_set_delays(z2a, a2z, delays):
    fro,leaks = z_get_leaks(z2a, a2z, 'A2F', (69,'G_ledger'))
    print('\n\t LEAKS:', leaks, '\n')

    for leak in leaks:
        itm,msg = leak
        (fro,nonce),tx = msg
        #print('\n\tleak:', fro,nonce , '\n')
        resp = z_delay_tx(z2a, a2z, fro, nonce, 0)
        #print('\n\tDelay Resp:', resp, '\n')

def z_mine_block_perm(perm, itm):
    msg = ('tick', perm)
    _write(itm,msg)
    itm.input.set(msg)
    dump.dump_wait()

def wait_for(_2_):
    try:
        r = gevent.wait(objects=[_2_],count=1)
        r = r[0]
        _2_.reset()
        return r.read()
    except gevent.exceptions.LoopExit:
        dump.dump_wait()
        print('DOESNT RETURN ANYTHING\n\n')
        return None

def z_send_money(_z2p, _p2z, sid, pid, v, to):
    msg = ('transfer', (sid, to), v, (), 'does not matter')
    _z2p.write( (pid, ((69,'G_ledger'), msg)) )
    resp = wait_for(_p2z)
    #print('SEND MONEY response', resp)
    return resp

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

def z_deploy_contract(z2p, p2z, z2a, a2z, fro, contract, *args):
    msg = ((69, 'G_ledger'), ('get-caddress',))
    caddr = z_inputs( msg, z2p, p2z, fro[1])
    #print('\n\t\t\033[1mGot caddr\033[0m', caddr[0][1][1])
    
    msg = ((69,'G_ledger'),('contract-create', caddr[0][1][1], 0, (contract,args), False, 'bad'))
    resp = z_inputs( msg, z2p, p2z, fro[1]) 
    z_set_delays(z2a, a2z, [0])
    z_mine_blocks(z2p, p2z, fro[0], fro[1], 1) 
    return caddr

#def z_ping(itm):
def z_ping(*z2ps):
    for z2p in z2ps:
        z_inputs(('ping',),z2p)

def z_mint(itm, adv, ledger, *to):
    for t in to:
        z_send_money(10, t, itm, ledger)
    z_set_delays(adv, ledger, [0 for _ in range(len(to))])

def z_prot_input(z2p, msg):
    _write(z2p.to, msg)
    z2p.write( msg )
    dump.dump_wait()

def z_instant_input(z2p, msg):
    z_prot_input(z2p, msg)

def z_tx_inputs(z2a, adv, ledger, msg, z2sp, *z2ps):
    for z2p in z2ps:
        z_instant_input(z2p, msg)
    z_set_delays(z2a, adv, ledger, [0 for _ in z2ps])
    z_mine_blocks(1, z2sp, z2sp.to) 

def z_ainputs(msg, z2a, a2z):
    z2a.write( msg )
    #resp = wait_for(a2z)
    #return resp

def z_inputs(msg, z2p, p2z, *pids):
    ret = []
    for pid in pids:
        z2p.write( (pid, msg) )
        resp = wait_for(p2z)
        ret.append(resp)
    return ret

def z_a2p2f(pid, msg, z2a, a2z):
    z_ainputs( ('A2P', (pid,  msg) ), z2a, a2z )

def z_a2p(pid, msg, z2a, a2z):
    z_ainputs( ('A2P', (pid, ('P', msg))) , z2a, a2z )

def z_mint_mine(z2p, p2z, z2a, a2z, sid, pid, *to):
    for t in to:
        resp = z_send_money(z2p, p2z, sid, pid, 10, t)
    z_set_delays(z2a, a2z, [0 for _ in range(len(to))])
    resp = z_mine_blocks(z2p, p2z, sid, pid, pid)
    print('MINE resp', resp)

def z_start_ledger(sid, pid, cledger, cwrapperitm, a2f, f2f, p2f):
    g_ledger = cledger(sid,pid)
    protected, ledger_itm = cwrapperitm(sid,pid,g_ledger, a2f, f2f, p2f)
    comm.setFunctionality(ledger_itm)
    return g_ledger, protected, ledger_itm

def z_start_clock(sid, pid, cclock, citm, a2f, f2f, p2f):
    g_clock, clock_itm = citm(sid, pid, a2f, f2f, p2f)
    comm.setFunctionality(clock_itm)
    return g_clock, clock_itm

def z_crupt(sid, pid):
    comm.corrupt(sid,pid)

def z_ideal_parties(sid,pids,itm,f, a2ps, p2fs, z2ps):
    iparties = f(sid,pids,itm, a2ps, p2fs, z2ps)
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
    comm.setParty(simparty)
    return simparty


def execUC(psid, nump, cpwrapper, pargs, cfwrapper, adv):
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

    

    
