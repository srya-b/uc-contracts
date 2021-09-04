from uc.itm import ProtocolWrapper, GenChannel
import gevent
from numpy.polynomial.polynomial import Polynomial
import random, os

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
            crupt.add( (_s,_p))

        f = fs(k, rng, crupt, sid, -1, func_channels, pump, poly, importargs)
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

#def createWrappedUC(k, fs, ps, gs, adv, poly, importargs={}):
def createGUC(k, fs, ps, gs, adv, poly, importargs={}):
    f2p,p2f = GenChannel('f2p'),GenChannel('p2f')
    f2a,a2f = GenChannel('f2a'),GenChannel('a2f')
    f2z,z2f = GenChannel('f2z'),GenChannel('z2f')
    f2g,g2f = GenChannel('f2g'),GenChannel('g2f')
    p2a,a2p = GenChannel('p2a'),GenChannel('a2p')
    p2z,z2p = GenChannel('p2z'),GenChannel('z2p')
    p2g,g2p = GenChannel('p2g'),GenChannel('g2p')
    z2a,a2z = GenChannel('z2a'),GenChannel('a2z')
    z2g,g2z = GenChannel('z2g'),GenChannel('g2z')
    g2a,a2g = GenChannel('g2a'),GenChannel('a2g')
    pump = GenChannel('big ol dump')

    env_channels = {'f2z':f2z, 'z2f':z2f, 'p2z':p2z, 'z2p':z2p, 'a2z':a2z, 'z2a':z2a, 'g2z':g2z, 'z2g':z2g}
    func_channels = {'f2z':f2z, 'z2f':z2f, 'f2p':f2p, 'p2f':p2f, 'f2a':f2a, 'a2f':a2f, 'f2g':f2g, 'g2f':g2f}
    party_channels = {'p2z':p2z, 'z2p':z2p, 'p2a':p2a, 'a2p':a2p, 'p2f':p2f, 'f2p':f2p, 'p2g':p2g, 'g2p':g2p}
    adv_channels = {'a2z':a2z, 'z2a':z2a, 'a2f':a2f, 'f2a':f2a, 'a2g':a2g, 'g2a':g2a, 'a2p':a2p, 'p2a':p2a}
    gfunc_channels = {'g2a':g2a, 'a2g':a2g, 'g2f':g2f, 'f2g':f2g, 'g2p':g2p, 'p2g':p2g, 'g2z':g2z, 'z2g':z2g}

    channels = {}
    channels.update(env_channels)
    channels.update(func_channels)
    channels.update(party_channels)
    channels.update(adv_channels)
    channels.update(gfunc_channels)

    static = GenChannel()
    rng = random.Random(os.urandom(32))
    
    def _exec():
        r = gevent.wait( objects=[static], count=1)[0]
        m = r.read().msg
        static.reset()
        sid_msg,gsid_msg,ssids_msg,crupt_msg = m
        assert sid_msg[0] == 'sid'
        print('sid', sid_msg)
        print('gsid', gsid_msg)
        print('ssids', ssids_msg)
        sid = sid_msg[1]
        gsid = gsid_msg[1]
        ssids = ssids_msg[1]

        assert crupt_msg[0] == 'crupt'
        crupt = set()
        for _s,_p in crupt_msg[1:]:
            crupt.add( (_s,_p) )

        #w = wrapper(k, rng, crupt, sid, {'f2g':f2g, 'g2f':g2f, 'p2g':p2g, 'g2p':g2p, 'a2g':a2g, 'g2a':g2a, 'z2g':z2g, 'g2z':g2z}, pump, poly, importargs)
        #gevent.spawn(w.run)
        g = gs(k, rng, crupt, gsid, -1, gfunc_channels, poly, pump, importargs, ssids)
        gevent.spawn(g.run)

        #f = WrappedFunctionalityWrapper(k, rng, crupt, p2f, f2p, a2f, f2a, z2f, f2z, g2f, f2g, pump, poly, importargs)
        #f = WrappedFunctionalityWrapper(k, rng, crupt, sid, func_channels, pump, poly, importargs)
        f = fs(k, rng, crupt, sid, -1, func_channels, pump, poly, importargs, gsid, ssids)
        #for t,c in fs:
        #    f.newcls(t,c)
        gevent.spawn( f.run )
        #p = ps(k, sid, z2p, p2z, f2p, p2f, a2p, p2a, g2p, p2g, pump, poly, importargs)
        print('execuc crupt', crupt)

        #p = ps(k, rng, crupt, sid, {'z2p':z2p, 'p2z':p2z, 'f2p':f2p, 'p2f':p2f, 'a2p':a2p, 'p2a':p2a, 'g2p':g2p, 'p2g':p2g}, pump, poly, importargs)
        p = ps(k, rng, crupt, sid, party_channels, pump, poly, importargs, gsid, ssids)
        gevent.spawn(p.run)
        # TODO change to wrapped adversray
        advitm = adv(k, rng, crupt, sid, -1, adv_channels, pump, poly, importargs, gsid, ssids)
        gevent.spawn(advitm.run)

    gevent.spawn(_exec)
    return channels,static,pump

#def execWrappedUC(k, env, fs, ps, wrapper, adv, poly=Polynomial([1])):
def execGUC(k, env, fs, ps, wrapper, adv, poly=Polynomial([1])):
    c,static,pump = createGUC(k, fs, ps, wrapper, adv, poly)
    print('type', type(env))
    return env(k, static, c['z2p'], c['z2f'], c['z2a'], c['z2g'], c['a2z'], c['p2z'], c['f2z'], c['g2z'], pump)

def createWrappedSimulation(k, fs, ps, wrapper, adv, poly, importargs={}):
    f2p,p2f = GenChannel('f2p'),GenChannel('p2f')
    f2a,a2f = GenChannel('f2a'),GenChannel('a2f')
    f2z,z2f = GenChannel('f2z'),GenChannel('z2f')
    f2g,g2f = GenChannel('f2g'),GenChannel('g2f')
    p2a,a2p = GenChannel('p2a'),GenChannel('a2p')
    p2z,z2p = GenChannel('p2z'),GenChannel('z2p')
    p2g,g2p = GenChannel('p2g'),GenChannel('g2p')
    z2a,a2z = GenChannel('z2a'),GenChannel('a2z')
    z2g,g2z = GenChannel('z2g'),GenChannel('g2z')
    g2a,a2g = GenChannel('g2a'),GenChannel('a2g')
    pump = GenChannel('big ol dump')

    env_channels = {'f2z':f2z, 'z2f':z2f, 'p2z':p2z, 'z2p':z2p, 'a2z':a2z, 'z2a':z2a, 'g2z':g2z, 'z2g':z2g}
    func_channels = {'f2z':f2z, 'z2f':z2f, 'f2p':f2p, 'p2f':p2f, 'f2a':f2a, 'a2f':a2f, 'f2g':f2g, 'g2f':g2f}
    party_channels = {'p2z':p2z, 'z2p':z2p, 'p2a':p2a, 'a2p':a2p, 'p2f':p2f, 'f2p':f2p, 'p2g':p2g, 'g2p':g2p}
    adv_channels = {'a2z':a2z, 'z2a':z2a, 'a2f':a2f, 'f2a':f2a, 'a2g':a2g, 'g2a':g2a, 'a2p':a2p, 'p2a':p2a}
    wrapper_channels = {'g2a':g2a, 'a2g':a2g, 'g2f':g2f, 'f2g':f2g, 'g2p':g2p, 'p2g':p2g, 'g2z':g2z, 'z2g':z2g}

    channels = {}
    channels.update(env_channels)
    channels.update(func_channels)
    channels.update(party_channels)
    channels.update(adv_channels)
    channels.update(wrapper_channels)

    static = GenChannel()
    itms = GenChannel()
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
            crupt.add( (_s,_p) )

        w = wrapper(k, rng, crupt, {'f2g':f2g, 'g2f':g2f, 'p2g':p2g, 'g2p':g2p, 'a2g':a2g, 'g2a':g2a, 'z2g':z2g, 'g2z':g2z}, pump, poly, importargs)
        gevent.spawn(w.run)

        #f = WrappedFunctionalityWrapper(k, rng, crupt, p2f, f2p, a2f, f2a, z2f, f2z, g2f, f2g, pump, poly, importargs)
        f = WrappedFunctionalityWrapper(k, rng, crupt, sid, func_channels, pump, poly, importargs)
        for t,c in fs:
            f.newcls(t,c)
        gevent.spawn( f.run )
        #p = ps(k, sid, z2p, p2z, f2p, p2f, a2p, p2a, g2p, p2g, pump, poly, importargs)
        print('execuc crupt', crupt)
        p = ps(k, rng, crupt, sid, {'z2p':z2p, 'p2z':p2z, 'f2p':f2p, 'p2f':p2f, 'a2p':a2p, 'p2a':p2a, 'g2p':g2p, 'p2g':p2g}, pump, poly, importargs)
        gevent.spawn(p.run)
        # TODO change to wrapped adversray
        advitm = adv(k, rng, crupt, sid, -1, adv_channels, pump, poly, importargs)
        gevent.spawn(advitm.run)

        itms.write( (w, f, p, advitm) )


    gevent.spawn(_exec)
    return channels,static,pump,itms
