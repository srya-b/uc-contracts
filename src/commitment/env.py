from utils import waits
from messages import *
from itm import fork, forever
import gevent

def env(k, static, z2p, z2f, z2a, a2z, f2z, p2z, pump):
    sid = ('one', 1, 2)
    static.write( (('sid',sid), ('crupt',)))

    transcript = []
    def _p2z():
        while True:
            m = waits(p2z)
            transcript.append('p2z: ' + str(m.msg))
            print('p2z: ' + str(m.msg))
            pump.write('')

    def _a2z():
        while True:
            m = waits(a2z)
            transcript.append('a2z:' + str(m.msg))
            print('a2z:' + str(m.msg))
            pump.write('')

    gevent.spawn(_p2z)
    gevent.spawn(_a2z)

    z2p.write( ((sid,1), ('commit',0)), 3 )
    waits(pump)

    z2p.write( ((sid,1), ('reveal',)), 1 )
    waits(pump)

    print('transcript', transcript)
    return transcript

def env2(k, static, z2p, z2f, z2a, a2z, f2z, p2z, pump):
    print('its this one')
    sid = ('one', 1, 2)
    static.write( (('sid',sid), ('crupt', (sid,2))))

    transcript = []
    def _p2z():
        while True:
            m = waits(p2z)
            transcript.append('p2z: ' + str(m.msg))
            print('p2z: ' + str(m.msg))
            pump.write('')

    def _a2z():
        while True:
            m = waits(a2z)
            transcript.append('a2z:' + str(m.msg))
            print('a2z:' + str(m.msg))
            pump.write('')

    gevent.spawn(_p2z)
    gevent.spawn(_a2z)

    z2p.write( ((sid,1), ('commit',0)), 3)
    waits(pump)

    z2p.write( ((sid,1), ('reveal',)), 1)
    waits(pump)

    #print('transcript', transcript)
    return transcript

def distinguisher(t_ideal, t_real):
    print('\n\t\033[93m Ideal transcript\033[0m')
    for i in t_ideal: print(i)

    print('\n\t\033[93m real transcript\033[0m')
    for i in t_real: print(i)

    if t_ideal == t_real:
        print("\033[92m[Distinguisher] They're the same\033[0m")
    else:
        print("\033[91m[Distinguisher] They're different\033[0m")

from itm import ProtocolWrapper, protocolWrapper
from adversary import DummyAdversary
from commitment import F_Com, Random_Oracle_and_Chan, Commitment_Prot
from execuc import execUC
from numpy.polynomial.polynomial import Polynomial
from f_com import F_Com
from sim_com import Sim_Com
from itm import PartyWrapper, partyWrapper
from lemmaS import Lemma_Simulator, lemmaS

if __name__=='__main__':
    treal = execUC(
        128,
        env,
        [('F_ro', Random_Oracle_and_Chan)],
        protocolWrapper(Commitment_Prot),
        DummyAdversary,
        poly=Polynomial([1,2,3])
    )

    print('\n')
    tideal = execUC(
        128,
        env,
        [('F_com',F_Com)],
        partyWrapper('F_com'),
        Sim_Com,
        #lemmaS(Sim_Com, Polynomial([1,2,3]), DummyAdversary),
        poly=Polynomial([0,1])
    )

    distinguisher(tideal, treal)
