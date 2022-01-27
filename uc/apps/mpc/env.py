from uc.utils import waits, collectOutputs
import gevent

def env(k, static, z2p, z2f, z2a, a2z, f2z, p2z, pump):
    print('\033[94m[ env_honest ]\033[0m')
    sid = ('one', "3, 99")
    static.write( (('sid',sid), ('crupt',)))

    global last_handle
    last_handle = None

    transcript = []
    def _a2z():
        while True:
            m = waits(a2z)
            transcript.append('a2z: ' + str(m))
            pump.write('dump')

    def _p2z():
        while True:
            global last_handle
            pid,m = waits(p2z)
            if m[0] == 'OpOutput':
                last_handle = m[1]
            transcript.append('p2z: ' + str((pid,m)))
            pump.write('dump')

    g1 = gevent.spawn(_a2z)
    g2 = gevent.spawn(_p2z)
   
    z2p.write( (99, ('op', ('CONST', 2))) )
    waits(pump)

    x = last_handle
   
    z2p.write( (99, ('op', ('CONST', 5))) )
    waits(pump)

    y = last_handle
    

    print('mult opcode')
    z2p.write( (99, ('op', ('MULT', (x, y)))) )
    waits(pump)

    xy = last_handle
    z2p.write( (99, ('op', ('OPEN', xy))) )
    waits(pump)

    gevent.kill(g1)
    gevent.kill(g2)

    print('transcript', transcript)
    return transcript

from f_mpc import fMPC_
from uc.execuc import execUC
from uc.protocol import DummyParty
from uc.adversary import DummyAdversary

execUC(
    128,
    env,
    fMPC_,
    DummyParty,
    DummyAdversary
)
