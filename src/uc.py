from itm import ProtocolWrapper, FunctionalityWrapper, PartyWrapper, GenChannel
from comm import setAdversary
import gevent

def execUC(sid, env, fs, pwrapper, prot, adv):
    f2p,p2f = GenChannel(),GenChannel()
    f2a,a2f = GenChannel(),GenChannel()
    f2z,z2f = GenChannel(),GenChannel()
    p2a,a2p = GenChannel(),GenChannel()
    p2z,z2p = GenChannel(),GenChannel()
    z2a,a2z = GenChannel(),GenChannel()
    
    f = FunctionalityWrapper(p2f, f2p, a2f, f2a, z2f, f2z)
    gevent.spawn(f.run)
    for t,c in fs:
        f.newcls(t,c)
    
    #TODO remove sid from adversary
    advitm = adv(sid, -1, z2a, a2z, p2a, a2p, a2f, f2a)
    setAdversary(advitm)
    gevent.spawn(advitm.run)

    if pwrapper == PartyWrapper:
        p = PartyWrapper(z2p,p2z, f2p,p2f, a2p,p2a, prot)
    else:
        p = ProtocolWrapper(z2p,p2z, f2p,p2f, a2p,p2a, prot) 
    gevent.spawn(p.run)

    # TODO this is only for katz     vv
    env(sid, z2p, z2f, z2a, a2z, p2z, f2z, p)




