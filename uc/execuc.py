from uc.itm import ProtocolWrapper, GenChannel
import gevent
from numpy.polynomial.polynomial import Polynomial
import random, os

def createUC(k, fs, ps, adv):
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
        m = r.read()
        static.reset()
        sid_msg,crupt_msg = m
        assert sid_msg[0] == 'sid'
        sid = sid_msg[1]

        assert crupt_msg[0] == 'crupt'
        crupt = set()
        for _s,_p in crupt_msg[1:]:
            crupt.add( (_s,_p))

        f = fs(k, rng, crupt, sid, -1, func_channels, pump)
        gevent.spawn( f.run )
        p = ps(k, rng, crupt, sid, party_channels, pump)

        gevent.spawn(p.run)
        advitm = adv(k, rng, crupt, sid, -1, adv_channels, pump)
        gevent.spawn(advitm.run)
    
    gevent.spawn(_exec)
    return channels,static,pump

def execUC(k, env, fs, ps, adv):
    c,static,pump = createUC(k, fs, ps, adv)
    return env(k, static, c['z2p'], c['z2f'], c['z2a'], c['a2z'], c['f2z'], c['p2z'], pump)

