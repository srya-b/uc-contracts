from itm import ProtocolWrapper, FunctionalityWrapper, PartyWrapper, GenChannel, WrappedFunctionalityWrapper, WrappedProtocolWrapper
from comm import setAdversary
import gevent


def createUC(fs, pwrapper, prot, adv):
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
    return f2p,p2f,f2a,a2f,f2z,z2f,p2a,a2p,p2z,z2p,z2a,a2z,static

def execUC(env, fs, pwrapper, prot, adv):
    f2p,p2f,f2a,a2f,f2z,z2f,p2a,a2p,p2z,z2p,z2a,a2z,static = createUC(fs, pwrapper, prot, adv)
    env(static, z2p, z2f, z2a, a2z, p2z, f2z)

def createWrappedUC(fs, ps, wrapper, prot, adv):
    f2p,p2f = GenChannel('f2p'),GenChannel('p2f')
    f2a,a2f = GenChannel('f2a'),GenChannel('a2f')
    f2z,z2f = GenChannel('f2z'),GenChannel('z2f')
    f2w,w2f = GenChannel('f2w'),GenChannel('w2f')
    p2a,a2p = GenChannel('p2a'),GenChannel('a2p')
    p2z,z2p = GenChannel('p2z'),GenChannel('z2p')
    p2w,w2p = GenChannel('p2w'),GenChannel('w2p')
    z2a,a2z = GenChannel('z2a'),GenChannel('a2z')
    z2w,w2z = GenChannel('z2w'),GenChannel('w2z')
    w2a,a2w = GenChannel('w2a'),GenChannel('a2w')

    static = GenChannel()
    
    def _exec():
        r = gevent.wait( objects=[static], count=1)
        r = r[0]
        d = r.read()
        m = d.msg
        static.reset()
        assert m[0] == 'sid'
        print('sid', m)
        sid = m[1]

        #w = wrapper(f2w, w2f, p2w, w2p, a2w, w2a, z2w, w2z)
        w = wrapper({'f2w':f2w, 'w2f':w2f, 'p2w':p2w, 'w2p':w2p, 'a2w':a2w, 'w2a':w2a, 'z2w':z2w, 'w2z':w2z})
        gevent.spawn(w.run)

        f = WrappedFunctionalityWrapper(p2f, f2p, a2f, f2a, z2f, f2z, w2f, f2w)
        for t,c in fs:
            f.newcls(t,c)
        gevent.spawn( f.run )
        if ps == PartyWrapper:
            p = PartyWrapper(z2p,p2z, f2p,p2f, a2p,p2a, prot)
        else:
            p = WrappedProtocolWrapper(z2p,p2z, f2p,p2f, a2p,p2a, w2p,p2w, prot) 
        gevent.spawn(p.run)
        # TODO change to wrapped adversray
        advitm = adv(sid, -1, z2a, a2z, p2a, a2p, a2f, f2a, a2w, w2a)
        setAdversary(advitm)
        gevent.spawn(advitm.run)

    gevent.spawn(_exec)
    return f2p,p2f,f2a,a2f,f2z,z2f,p2a,a2p,p2z,z2p,z2a,a2z,z2w,w2z,a2w,w2a,static

def execWrappedUC(env, fs, ps, wrapper, prot, adv):
    f2p,p2f,f2a,a2f,f2z,z2f,p2a,a2p,p2z,z2p,z2a,a2z,z2w,w2z,a2w,w2a,static = createWrappedUC(fs, ps, wrapper, prot, adv)
    env(static, z2p, z2f, z2a, z2w, a2z, p2z, f2z, w2z)

