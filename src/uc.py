from itm import ProtocolWrapper, FunctionalityWrapper, PartyWrapper, GenChannel
from comm import setAdversary
import gevent

def execUC(env, fs, pwrapper, prot, adv):
    f2p,p2f = GenChannel(),GenChannel()
    f2a,a2f = GenChannel(),GenChannel()
    f2z,z2f = GenChannel(),GenChannel()
    p2a,a2p = GenChannel(),GenChannel()
    p2z,z2p = GenChannel(),GenChannel()
    z2a,a2z = GenChannel(),GenChannel()
    static = GenChannel()
    
    def _exec():
        r = gevent.wait( objects=[static], count=1)
        r = r[0]
        m = r.read()
        static.reset()
        assert m[0] == 'sid'
        print('sid', m)
        sid = m[1]

        f = FunctionalityWrapper(p2f, f2p, a2f, f2a, z2f, f2z)
        for t,c in fs:
            f.newcls(t,c)
        gevent.spawn( f.run )
        if pwrapper == PartyWrapper:
            p = PartyWrapper(z2p,p2z, f2p,p2f, a2p,p2a, prot)
        else:
            p = ProtocolWrapper(z2p,p2z, f2p,p2f, a2p,p2a, prot) 
        gevent.spawn(p.run)
        advitm = adv(sid, -1, z2a, a2z, p2a, a2p, a2f, f2a)
        setAdversary(advitm)
        gevent.spawn(advitm.run)

    gevent.spawn(_exec)
    env(static, z2p, z2f, z2a, a2z, p2z, f2z)




