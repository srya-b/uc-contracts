from itm import ProtocolWrapper, FunctionalityWrapper, PartyWrapper, GenChannel, WrappedFunctionalityWrapper, WrappedProtocolWrapper, WrappedPartyWrapper
from utils import z_crupt
import gevent
from numpy.polynomial.polynomial import Polynomial
import random, os

#def createUC(fs, pwrapper, prot, adv):
def createUC(k, fs, ps, adv, poly, importargs={}):
    f2p,p2f = GenChannel('f2p'),GenChannel('p2f')
    f2a,a2f = GenChannel('f2a'),GenChannel('a2f')
    f2z,z2f = GenChannel('f2z'),GenChannel('z2f')
    p2a,a2p = GenChannel('p2a'),GenChannel('a2p')
    p2z,z2p = GenChannel('p2z'),GenChannel('z2p')
    z2a,a2z = GenChannel('z2a'),GenChannel('a2z')
    pump = GenChannel('ol pump and dump')

    env_channels = {'f2z':f2z, 'z2f':z2f, 'p2z':p2z, 'z2p':z2p, 'a2z':a2z, 'z2a':z2a}
    func_channels = {'f2z':f2z, 'z2f':z2f, 'f2p':f2p, 'p2f':p2f, 'f2a':f2a, 'a2f':a2f}
    party_channels = {'p2z':p2z, 'z2p':z2p, 'p2a':p2a, 'a2p':a2p, 'p2f':p2f, 'f2p':f2p}
    adv_channels = {'a2z':a2z, 'z2a':z2a, 'a2f':a2f, 'f2a':f2a, 'a2p':a2p, 'p2a':p2a}
    
    channels = {}
    channels.update(env_channels)
    channels.update(func_channels)
    channels.update(party_channels)
    channels.update(adv_channels)
   
    static = GenChannel('static')

    # initialize random bits
    rng = random.Random(os.urandom(32))
    
    def _exec():
        r = gevent.wait( objects=[static], count=1)[0]
        m = r.read().msg
        static.reset()
        sid_msg,crupt_msg = m
        assert sid_msg[0] == 'sid'
        print('sid', sid_msg)
        sid = sid_msg[1]

        assert crupt_msg[0] == 'crupt'
        print('crupted', crupt_msg)
        crupt = set()
        for _s,_p in crupt_msg[1:]:
            z_crupt(_s,_p)
            crupt.add( (_s,_p))

        f = FunctionalityWrapper(k, rng, crupt, sid, func_channels, pump, poly, importargs)
        for t,c in fs:
            f.newcls(t,c)
        gevent.spawn( f.run )
        p = ps(k, rng, crupt, sid, party_channels, pump, poly, importargs)

        gevent.spawn(p.run)
        # TODO change to wrapped adversray
        advitm = adv(k, rng, crupt, sid, -1, adv_channels, pump, poly, importargs)
        gevent.spawn(advitm.run)
    
    gevent.spawn(_exec)
    return channels,static,pump

def execUC(k, env, fs, ps, adv, poly):
    c,static,pump = createUC(k, fs, ps, adv, poly)
    return env(k, static, c['z2p'], c['z2f'], c['z2a'], c['a2z'], c['f2z'], c['p2z'], pump)

#def createWrappedUC(fs, ps, wrapper, prot, adv, poly):
def createWrappedUC(k, fs, ps, wrapper, adv, poly, importargs={}):
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
    pump = GenChannel('big ol dump')

    env_channels = {'f2z':f2z, 'z2f':z2f, 'p2z':p2z, 'z2p':z2p, 'a2z':a2z, 'z2a':z2a, 'w2z':w2z, 'z2w':z2w}
    func_channels = {'f2z':f2z, 'z2f':z2f, 'f2p':f2p, 'p2f':p2f, 'f2a':f2a, 'a2f':a2f, 'f2w':f2w, 'w2f':w2f}
    party_channels = {'p2z':p2z, 'z2p':z2p, 'p2a':p2a, 'a2p':a2p, 'p2f':p2f, 'f2p':f2p, 'p2w':p2w, 'w2p':w2p}
    adv_channels = {'a2z':a2z, 'z2a':z2a, 'a2f':a2f, 'f2a':f2a, 'a2w':a2w, 'w2a':w2a, 'a2p':a2p, 'p2a':p2a}
    wrapper_channels = {'w2a':w2a, 'a2w':a2w, 'w2f':w2f, 'f2w':f2w, 'w2p':w2p, 'p2w':p2w, 'w2z':w2z, 'z2w':z2w}

    channels = {}
    channels.update(env_channels)
    channels.update(func_channels)
    channels.update(party_channels)
    channels.update(adv_channels)
    channels.update(wrapper_channels)

    static = GenChannel()
    rng = random.Random(os.urandom(32))
    
    def _exec():
        r = gevent.wait( objects=[static], count=1)[0]
        m = r.read().msg
        static.reset()
        sid_msg,crupt_msg = m
        assert sid_msg[0] == 'sid'
        print('sid', sid_msg)
        sid = sid_msg[1]

        assert crupt_msg[0] == 'crupt'
        crupt = set()
        for _s,_p in crupt_msg[1:]:
            z_crupt(_s,_p)
            crupt.add( (_s,_p) )

        w = wrapper(k, rng, crupt, {'f2w':f2w, 'w2f':w2f, 'p2w':p2w, 'w2p':w2p, 'a2w':a2w, 'w2a':w2a, 'z2w':z2w, 'w2z':w2z}, pump, poly, importargs)
        gevent.spawn(w.run)

        #f = WrappedFunctionalityWrapper(k, rng, crupt, p2f, f2p, a2f, f2a, z2f, f2z, w2f, f2w, pump, poly, importargs)
        f = WrappedFunctionalityWrapper(k, rng, crupt, sid, func_channels, pump, poly, importargs)
        for t,c in fs:
            f.newcls(t,c)
        gevent.spawn( f.run )
        #p = ps(k, sid, z2p, p2z, f2p, p2f, a2p, p2a, w2p, p2w, pump, poly, importargs)
        print('execuc crupt', crupt)
        p = ps(k, rng, crupt, sid, {'z2p':z2p, 'p2z':p2z, 'f2p':f2p, 'p2f':p2f, 'a2p':a2p, 'p2a':p2a, 'w2p':w2p, 'p2w':p2w}, pump, poly, importargs)
        gevent.spawn(p.run)
        # TODO change to wrapped adversray
        advitm = adv(k, rng, crupt, sid, -1, adv_channels, pump, poly, importargs)
        gevent.spawn(advitm.run)

    gevent.spawn(_exec)
    return channels,static,pump

def execWrappedUC(k, env, fs, ps, wrapper, adv, poly=Polynomial([1])):
    c,static,pump = createWrappedUC(k, fs, ps, wrapper, adv, poly)
    return env(k, static, c['z2p'], c['z2f'], c['z2a'], c['z2w'], c['a2z'], c['p2z'], c['f2z'], c['w2z'], pump)

