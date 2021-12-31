from uc.itm import ProtocolWrapper, GenChannel
import gevent
from numpy.polynomial.polynomial import Polynomial
import random, os

def createUC(k, fs, ps, adv):
    """Setups of the necessary ITIs in the UC experiment,
    waits to receive the sid and crupt list from the environment,
    and offers all channels in the execution.

    Args:
        k: The security parameter
        fs: The functionality being run, must have same interface as UCFunctionality
        ps: The protocol to be run inside the ProtocolWrapper, same as UCProtocol
        adv: The adversary code, as UCAdversary

    Returns:
        channels: all of the channels between the main ITIs in the execution.
        static: the channel through which the environment communicates to execuc
            to give the sid and crupt list
        pump: The channel that all ITIs get use to return control to env and env cant
            wait on.
    """
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
    """The main function called which sets up the UC experiment,
    runs the environmenta, and returns its output.

    Args:
        k: The security parameter.
        env: the code for the environment, look at envs in uc.apps
        fs: the functionality code, follows UCFunctionality
        ps: the protocol code to run inside ProtocolWrapper, follows UCProtocol
        adv: the adversary code, follows UCAdverasary, see uc.adversary

    Returns:
        b: the output (bit) from the environment
    """
    c,static,pump = createUC(k, fs, ps, adv)
    b = env(k, static, c['z2p'], c['z2f'], c['z2a'], c['a2z'], c['f2z'], c['p2z'], pump)
    return b

