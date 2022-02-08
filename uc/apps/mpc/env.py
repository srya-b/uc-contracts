from uc.utils import waits, collectOutputs
import gevent

def env(k, static, z2p, z2f, z2a, a2z, f2z, p2z, pump):
    print('\033[94m[ env_honest ]\033[0m')
    sid = ('one', "3, 99")

    # corrupt observer (pid=98) and corrupt party pid=1
    static.write( (('sid',sid), ('crupt', 98, 1)))

    global last_handle
    last_handle = None

    transcript = []
    def _a2z():
        while True:
            global last_handle
            tag,m = waits(a2z)
            transcript.append('a2z: ' + str((tag,m)))
            if tag == 'P2A':
                pid,m = m
                print('a2z m', m)
                if m[0] == 'OpOutput' or m[0] == 'OpRes':
                    last_handle = m[1]
            pump.write('dump')

    def _p2z():
        while True:
            global last_handle
            pid,m = waits(p2z)
            print('p2z m', m)
            if m[0] == 'OpOutput' or m[0] == 'OpRes':
                last_handle = m[1]
            transcript.append('p2z: ' + str((pid,m)))
            pump.write('dump')

    g1 = gevent.spawn(_a2z)
    g2 = gevent.spawn(_p2z)
  
    # send inputs throug the honest Input Party
    z2p.write( (99, ('op', ('CONST', 2))) )
    waits(pump)

    x = last_handle
    print('x last handle', x)

    z2p.write( (99, ('op', ('CONST', 5))) )
    waits(pump)

    y = last_handle
    print('y last handle', y)

    z2p.write( (99, ('op', ('MULT', (x, y)))) )
    waits(pump)

    xy = last_handle
    z2p.write( (99, ('op', ('OPEN', xy))) )
    waits(pump)

    # follow from an honest party
    z2p.write( (2, ('op', ('CONST', 2))))
    waits(pump)

    x = last_handle

    z2p.write( (2, ('op', ('CONST', 5))))
    waits(pump)

    y = last_handle

    z2p.write( (2, ('op', ('MULT', (x,y)))))
    waits(pump)

    xy = last_handle

    z2p.write( (2, ('myshare', xy)))
    waits(pump)

    # logs from observer (a corrupt party)
    z2a.write( ('A2P', (98, ('log',))))
    waits(pump)

    # my share from one of the corrupt parties
    z2a.write( ('A2P', (1, ('myshare', 8))) )
    waits(pump)

    # follow along (from a corrupt party)
    z2a.write( ('A2P', (1, ('op', ('CONST', 2)))))
    waits(pump)
    x = last_handle

    z2a.write( ('A2P', (1, ('op', ('CONST', 5)))))
    waits(pump)
    y = last_handle

    z2a.write( ('A2P', (1, ('op', ('MULT', (x,y))))))
    waits(pump)

    z2a.write( ('A2P', (1, ('op', ('RAND',)))))
    waits(pump)

    # logs from an honest party
    z2p.write( ('99', ('log',)))
    waits(pump)

    gevent.kill(g1)
    gevent.kill(g2)

    print('transcript', transcript)
    return transcript

def distinguisher(t_ideal, t_real):
    print('\n\t\033[93m ideal transcript\033[0m')
    for i in t_ideal: print(str(i))

    print('\n\t\033[93m real transcript\033[0m')
    for i in t_real: print(str(i))

    if t_ideal == t_real:
        print("\033[92m[distinguisher] they're the same\033[0m")
    else:
        print("\033[91m[distinguisher] they're different\033[0m")



from f_mpc import fMPC, fMPC_sansMULT
from prot_mpc import MPC_Prot, mpc_beaver
from uc.execuc import execUC
from uc.protocol import DummyParty
from uc.adversary import DummyAdversary

tideal = execUC(
    128,
    env,
    fMPC,
    DummyParty,
    DummyAdversary
)
#treal = execUC(
#    128,
#    env,
#    fMPC_sansMULT,
#    MPC_Prot(mpc_beaver),
#    DummyAdversary
#)

distinguisher(tideal, [])
