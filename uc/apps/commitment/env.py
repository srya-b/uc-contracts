from uc.utils import waits, collectOutputs
import gevent

def env(k, static, z2p, z2f, z2a, a2z, f2z, p2z, pump):
    sid = ('one', 1, 2)
    static.write( (('sid',sid), ('crupt',)))

    transcript = []
    def _a2z():
        while True:
            m = waits(a2z)
            transcript.append('a2z: ' + str(m))
            pump.write('dump')

    def _p2z():
        while True:
            m = waits(p2z)
            transcript.append('p2z: ' + str(m))
            pump.write('dump')

    g1 = gevent.spawn(_a2z)
    g2 = gevent.spawn(_p2z)
    

    z2p.write( ((sid,1), ('commit',0)))
    waits(pump)

    z2p.write( ((sid,1), ('reveal',)))
    waits(pump)
    
    gevent.kill(g1)
    gevent.kill(g2)

    print('transcript', transcript)
    return transcript

def env_receiver_crupt(k, static, z2p, z2f, z2a, a2z, f2z, p2z, pump):
    sid = ('one', 1, 2)
    static.write( (('sid',sid), ('crupt', (sid,2))))

    transcript = []
    def _p2z():
        while True:
            m = waits(p2z)
            transcript.append('p2z: ' + str(m))
            print('p2z: ' + str(m))
            pump.write('')

    def _a2z():
        while True:
            m = waits(a2z)
            transcript.append('a2z:' + str(m))
            print('a2z:' + str(m))
            pump.write('')

    gevent.spawn(_p2z)
    gevent.spawn(_a2z)

    z2p.write( ((sid,1), ('commit',0)))
    waits(pump)

    z2p.write( ((sid,1), ('reveal',)))
    waits(pump)

    print('transcript', transcript)
    return transcript

def env_committer_crupt(k, static, z2p, z2f, z2a, a2z, f2z, p2z, pump):
    sid = ('one', 1, 2)
    static.write( (('sid',sid), ('crupt', (sid,1))))

    transcript = []
    def _p2z():
        while True:
            m = waits(p2z)
            #transcript.append('p2z: ' + str(m.msg))
            transcript.append(m)
            print('p2z: ' + str(m))
            pump.write('')

    gevent.spawn(_p2z)

    z2a.write( ('A2F', ('hash', (123, 0))))
    m = waits(a2z)
    print('env msg', m)
    _,(sid,lasthash) = m
    print('last hash', lasthash)
    transcript.append('a2z: ' + str(m))

    z2a.write( ('A2P', ((sid,1), ('sendmsg', 2, ('commit',lasthash)))))
    waits(pump)

    z2a.write( ('A2P', ((sid,1), ('sendmsg', 2, 'yoyoyo'))) )
    waits(pump)

    z2a.write( ('A2P', ((sid,1), ('sendmsg', 2, ('open', (123, 0))))))
    waits(pump)

    return transcript

def env_committer_crupt_bad_open(k, static, z2p, z2f, z2a, a2z, f2a, p2z, pump):
    sid = ('one', 1, 2)
    static.write( (('sid',sid), ('crupt', (sid,1))))

    transcript = []
    def _p2z():
        while True:
            m = waits(p2z)
            #transcript.append('p2z: ' + str(m.msg))
            transcript.append(m)
            print('p2z: ' + str(m))
            pump.write('')

    gevent.spawn(_p2z)

    z2a.write( ('A2F', ('hash', (123, 0))))
    m = waits(a2z)
    print('env msg', m)
    _,(sid,lasthash) = m
    print('last hash', lasthash)
    transcript.append('a2z: ' + str(m))

    z2a.write( ('A2P', ((sid,1), ('sendmsg', 2, ('commit',lasthash)))))
    waits(pump)

    z2p.write( ((sid,2), ('sendmsg', ('this is the right message'))) )
    #waits(pump)
    waits(a2z)

    z2a.write( ('A2P', ((sid,1), ('sendmsg', 2, 'yoyoyo'))) )
    waits(pump)

    z2a.write( ('A2P', ((sid,1), ('sendmsg', 2, ('open', (123, 1))))))
    waits(pump)

    return transcript
    

def distinguisher(t_ideal, t_real):
    print('\n\t\033[93m Ideal transcript\033[0m')
    for i in t_ideal: print(str(i))

    print('\n\t\033[93m real transcript\033[0m')
    for i in t_real: print(str(i))

    if t_ideal == t_real:
        print("\033[92m[Distinguisher] They're the same\033[0m")
    else:
        print("\033[91m[Distinguisher] They're different\033[0m")

from uc.itm import ProtocolWrapper, protocolWrapper
from uc.adversary import DummyAdversary
from f_ro import Random_Oracle_and_Chan
from prot_com import Commitment_Prot
from uc.execuc import execUC
from f_com import F_Com_Channel
from sim_com import Sim_Com
from uc.itm import DummyParty
from uc.lemmaS import Lemma_Simulator, lemmaS

if __name__=='__main__':
    tideal = execUC(
        128,
        env,
        F_Com_Channel,
        protocolWrapper(DummyParty),
        Sim_Com,
    )

    print('\n')
    treal = execUC(
        128,
        env,
        Random_Oracle_and_Chan,
        protocolWrapper(Commitment_Prot),
        DummyAdversary,
    )

    distinguisher(tideal, treal)
