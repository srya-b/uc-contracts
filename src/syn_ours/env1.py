from itm import ProtocolWrapper, WrappedProtocolWrapper, WrappedPartyWrapper
from adversary import DummyWrappedAdversary
from syn_ours import Syn_FWrapper, Syn_Channel, Syn_Bracha_Protocol, RBC_Simulator, Syn_Bracha_Functionality
#from execuc import execWrappedUC
from execuc import execWrappedUC
from utils import z_get_leaks, waits
import logging

log = logging.getLogger(__name__)
logging.basicConfig(level="INFO")


def env1(static, z2p, z2f, z2a, z2w, a2z, p2z, f2z, w2z, pump):
    delta = 3
    n = 3
    #sid = ('one', (1,2,3), delta)
    sid = ('one', tuple(range(1,n+1)), delta)
    static.write( (('sid', sid), ('crupt',)) )

    z2p.write( ((sid,1), ('input', 2)), n*(4*n + 1) )
    #wait_for(p2z)
    waits(pump, a2z, p2z)

    def channel_id(fro, to, r):
        s = ('one', (sid,fro), (sid,to), r, delta)
        return (s,'F_chan')

    z2a.write( ('A2W', ('get-leaks',)) )
    msgs = waits(pump, a2z, p2z)
    log.debug('\033[91m [Leaks] \033[0m {}'.format( '\n'.join(str(m) for m in msgs.msg)))

    log.debug('\033[91m send first VAL, get +2 ECHO messages \033[0m')
    for _ in range(4):
        z2w.write( ('poll',) )
        log.info(waits(pump, a2z, p2z))

    log.debug('\033[91m +2 ECHO + 1 = 3 polls to send next VAL message +2 ECHO msgs \033[0m')
    for _ in range(3):
        z2w.write( ('poll',) )
        log.info(waits(pump, a2z, p2z))

    log.debug('\033[91m +2 ECHO + 1 = 3 polls to send last VAL message +2 ECHO msgs \033[0m')
    for _ in range(3):
        z2w.write( ('poll',) )
        log.info(waits(pump, a2z, p2z))

    log.debug('\033[91m +2 ECHO +1 = 3 polls to send 1 -> 2 ECHO msg, +2 READY msgs \033[0m')
    for _ in range(3):
        z2w.write( ('poll',) )
        log.info(waits(pump, a2z, p2z))

    log.debug('\033[91m +2 READY +1 = 3 polls to send 1 -> 3 ECHO msg, +2 READY msgs \033[0m')
    for _ in range(3):
        z2w.write( ('poll',) )
        log.info(waits(pump, a2z, p2z))

    log.debug('\033[91m +2 READY +1 = 3 polls to send 2 -> 1 ECHO msg, +2 READY msgs \033[0m')
    for _ in range(3):
        z2w.write( ('poll',) )
        log.info(waits(pump, a2z, p2z))

    log.debug('\033[91m +2 READY +1 = 3 polls to send 2 -> 3 ECHO msg, +0 READY msgs \033[0m')
    for _ in range(3):
        z2w.write( ('poll',) )
        log.info(waits(pump, a2z, p2z))

    log.debug('\033[91m DELAYING \033[0m')
    z2a.write( ('A2W', ('delay', 3)) )
    log.info(waits(pump, a2z))

    log.debug('\033[91m +0 READY +1 = 3 polls to send 3 -> 1 ECHO msg, +0 msgs \033[0m')
    for _ in range(4):
        z2w.write( ('poll',) )
        log.info(waits(pump, a2z, p2z))

    log.debug('\033[91m +0 READY +1 = 3 polls to send 3 -> 2 ECHO msg, +0 msgs \033[0m')
    z2w.write( ('poll',) )
    log.info(waits(pump, a2z, p2z))

    log.debug('\033[91m +0 READY +1 = 3 polls to send 2 -> 1 READY msg, +0 msgs \033[0m')
    z2w.write( ('poll',) )
    log.info(waits(pump, a2z, p2z))

    log.debug('\033[91m +0 READY +1 = 3 polls to send 2 -> 3 READY msg, +0 msgs \033[0m')
    z2w.write( ('poll',) )
    log.info(waits(pump, a2z, p2z))

    log.debug('\033[91m +0 READY +1 = 3 polls to send 3 -> 1 READY msg, 1 ACCEPTS\033[0m')
    z2w.write( ('poll',) )
    log.info('\033[1mp1 output\033[0m {}'.format(waits(pump, a2z, p2z)))

    log.debug('\033[91m +0 READY +1 = 3 polls to send 3 -> 2 READY msg, 2 Doesnt accept \033[0m')
    z2w.write( ('poll',) )
    log.info(waits(pump, a2z, p2z))

    log.debug('\033[91m +0 READY +1 = 3 polls to send 1 -> 2 READY msg, 2 ACCEPTS\033[0m')
    z2w.write( ('poll',) )
    log.info('\033[1mp2 output\033[0m {}'.format( waits(pump, a2z, p2z)))

    log.debug('\033[91m +0 READY +1 = 3 polls to send 1 -> 3 READY msg, 3 ACCEPTS\033[0m')
    z2w.write( ('poll',) )
    log.info('\033[1mp3 output\033[0m {}'.format(waits(pump, a2z, p2z)))

def env3(static, z2p, z2f, z2a, z2w, a2z, p2z, f2z, w2z, pump):
    delta = 3
    n = 3
    #sid = ('one', (1,2,3), delta)
    sid = ('one', tuple(range(1,n+1)), delta)
    #static.write( (('sid', sid), ('crupt',)) )
    static.write( (('sid', sid), ('crupt',(sid,2))) )

    z2p.write( ((sid,1), ('input', 2)), n*(4*n + 1) )
    #wait_for(p2z)
    waits(pump, a2z, p2z)

    def channel_id(fro, to, r):
        s = ('one', (sid,fro), (sid,to), r, delta)
        return (s,'F_chan')

    z2a.write( ('A2W', ('get-leaks',)) )
    msgs = waits(pump, a2z, p2z)
    print('\033[91m [Leaks] \033[0m', '\n'.join(str(m) for m in msgs.msg))

    log.debug('\033[91m send first VAL, get +2 ECHO messages \033[0m')
    for _ in range(4):
        z2w.write( ('poll',) )
        print(waits(pump, a2z, p2z))

    log.debug('\033[91m +2 ECHO + 1 = 3 polls to send next VAL message +2 ECHO msgs \033[0m')
    for _ in range(3):
        z2w.write( ('poll',) )
        print(waits(pump, a2z, p2z))
    log.debug('*****')
    
    z2a.write( ('A2P', ((sid,2), ('P2F', ((channel_id(2,1,1)), ('send', ('ECHO', 2)))))) )
    print('crupt output:', waits(pump, a2z))

    z2a.write( ('A2P', ((sid,2), ('P2F', ((channel_id(2,3,1)), ('send', ('ECHO', 2)))))) )
    print('crupt output:', waits(pump, a2z))

    log.debug('\033[91m +2 ECHO + 1 = 3 polls to send last VAL message +2 ECHO msgs \033[0m')
    for _ in range(3):
        z2w.write( ('poll',) )
        print(waits(pump, a2z, p2z))

    log.debug('\033[91m +2 ECHO +1 = 3 polls to send 1 -> 2 ECHO msg, +2 READY msgs \033[0m')
    for _ in range(3):
        z2w.write( ('poll',) )
        print(waits(pump, a2z, p2z))

    z2a.write( ('A2P', ((sid,2), ('P2F', ((channel_id(2,1,1)), ('send', ('READY', 2)))))) )
    print('crupt output:', waits(pump, a2z))

    z2a.write( ('A2P', ((sid,2), ('P2F', ((channel_id(2,3,1)), ('send', ('READY', 2)))))) )
    print('crupt output:', waits(pump, a2z))

    log.debug('\033[91m +2 READY +1 = 3 polls to send 1 -> 3 ECHO msg, +2 READY msgs \033[0m')
    for _ in range(3):
        z2w.write( ('poll',) )
        print(waits(pump, a2z, p2z))

    log.debug('\033[91m +2 READY +1 = 3 polls to send 2 -> 1 ECHO msg, +2 READY msgs \033[0m')
    for _ in range(3):
        z2w.write( ('poll',) )
        print(waits(pump, a2z, p2z))

    log.debug('\033[91m +2 READY +1 = 3 polls to send 2 -> 3 ECHO msg, +0 READY msgs \033[0m')
    for _ in range(3):
        z2w.write( ('poll',) )
        print(waits(pump, a2z, p2z))

    log.debug('\033[91m +0 READY +1 = 3 polls to send 3 -> 1 ECHO msg, +0 msgs \033[0m')
    z2w.write( ('poll',) )
    print(waits(pump, a2z, p2z))

    log.debug('\033[91m +0 READY +1 = 3 polls to send 3 -> 2 ECHO msg, +0 msgs \033[0m')
    z2w.write( ('poll',) )
    print('waiting', waits(pump, a2z, p2z))

    log.debug('\033[91m +0 READY +1 = 3 polls to send 2 -> 1 READY msg, +0 msgs \033[0m')
    z2w.write( ('poll',) )
    print(waits(pump, a2z, p2z))

    log.debug('\033[91m +0 READY +1 = 3 polls to send 2 -> 3 READY msg, +0 msgs \033[0m')
    z2w.write( ('poll',) )
    print(waits(pump, a2z, p2z))

    log.debug('\033[91m +0 READY +1 = 3 polls to send 3 -> 1 READY msg, 1 ACCEPTS\033[0m')
    z2w.write( ('poll',) )
    print('\033[1mp1 output\033[0m', waits(pump, a2z, p2z))

    log.debug('\033[91m +0 READY +1 = 3 polls to send 3 -> 2 READY msg, 2 Doesnt accept \033[0m')
    z2w.write( ('poll',) )
    print(waits(pump, a2z, p2z))

    log.debug('\033[91m +0 READY +1 = 3 polls to send 1 -> 2 READY msg, 2 ACCEPTS\033[0m')
    z2w.write( ('poll',) )
    print('\033[1mp2 output\033[0m', waits(pump, a2z, p2z))

    log.debug('\033[91m +0 READY +1 = 3 polls to send 1 -> 3 READY msg, 3 ACCEPTS\033[0m')
    z2w.write( ('poll',) )
    print('\033[1mp3 output\033[0m', waits(pump, a2z, p2z))

def env2(static, z2p, z2f, z2a, z2w, a2z, p2z, f2z, w2z, pump):
    delta = 3
    n = 4
    #sid = ('one', (1,2,3), delta)
    sid = ('one', tuple(range(1,n+1)), delta)
    static.write( (('sid', sid), ('crupt',)) )

    z2p.write( ((sid,1), ('input', 2)), n*(4*n + 1) )
    #wait_for(p2z)
    waits(pump, a2z, p2z)

    def channel_id(fro, to, r):
        s = ('one', (sid,fro), (sid,to), r, delta)
        return (s,'F_chan')

    z2a.write( ('A2W', ('get-leaks',)) )
    msgs = waits(pump, a2z, p2z)
    print('\033[91m [Leaks] \033[0m', '\n'.join(str(m) for m in msgs.msg))

    log.debug('\033[91m send first VAL, get +2 ECHO messages \033[0m')
    for _ in range(4):
        z2w.write( ('poll',) )
        print(waits(pump, a2z, p2z))

    log.debug('\033[91m +2 ECHO + 1 = 3 polls to send next VAL message +2 ECHO msgs \033[0m')
    for _ in range(3):
        z2w.write( ('poll',) )
        print(waits(pump, a2z, p2z))

    log.debug('\033[91m +2 ECHO + 1 = 3 polls to send last VAL message +2 ECHO msgs \033[0m')
    for _ in range(3):
        z2w.write( ('poll',) )
        print(waits(pump, a2z, p2z))

    log.debug('\033[91m +2 ECHO + 1 = 3 polls to send fourth VAL message +2 ECHO msgs \033[0m')
    for _ in range(3):
        z2w.write( ('poll',) )
        print(waits(pump, a2z, p2z))

    log.debug('\033[91m +2 ECHO +1 = 3 polls to send 1 -> 2 ECHO msg, +2 READY msgs \033[0m')
    for _ in range(3):
        z2w.write( ('poll',) )
        print(waits(pump, a2z, p2z))

    log.debug('\033[91m +2 READY +1 = 3 polls to send 1 -> 3 ECHO msg, +2 READY msgs \033[0m')
    for _ in range(3):
        z2w.write( ('poll',) )
        print(waits(pump, a2z, p2z))

    log.debug('\033[91m +2 READY +1 = 3 polls to send 1 -> 4 ECHO msg, +2 READY msgs \033[0m')
    for _ in range(3):
        z2w.write( ('poll',) )
        print(waits(pump, a2z, p2z))

    log.debug('\033[91m +2 READY +1 = 3 polls to send 2 -> 1 ECHO msg, +2 READY msgs \033[0m')
    for _ in range(3):
        z2w.write( ('poll',) )
        print(waits(pump, a2z, p2z))

    log.debug('\033[91m +2 READY +1 = 3 polls to send 2 -> 3 ECHO msg, +0 READY msgs \033[0m')
    for _ in range(3):
        z2w.write( ('poll',) )
        print(waits(pump, a2z, p2z))

    log.debug('\033[91m +2 READY +1 = 3 polls to send 2 -> 4 ECHO msg, +0 READY msgs \033[0m')
    for _ in range(3):
        z2w.write( ('poll',) )
        print(waits(pump, a2z, p2z))

    log.debug('\033[91m +0 READY +1 = 3 polls to send 3 -> 1 ECHO msg, +0 msgs \033[0m')
    z2w.write( ('poll',) )
    print(waits(pump, a2z, p2z))

    log.debug('\033[91m +0 READY +1 = 3 polls to send 3 -> 2 ECHO msg, +0 msgs \033[0m')
    z2w.write( ('poll',) )
    print(waits(pump, a2z, p2z))

    log.debug('\033[91m +0 READY +1 = 3 polls to send 3 -> 4 ECHO msg, +0 msgs \033[0m')
    z2w.write( ('poll',) )
    print(waits(pump, a2z, p2z))

    log.debug('\033[91m +0 READY +1 = 3 polls to send 2 -> 1 READY msg, +0 msgs \033[0m')
    z2w.write( ('poll',) )
    print(waits(pump, a2z, p2z))

    log.debug('\033[91m +0 READY +1 = 3 polls to send 2 -> 3 READY msg, +0 msgs \033[0m')
    z2w.write( ('poll',) )
    print(waits(pump, a2z, p2z))

    log.debug('\033[91m +0 READY +1 = 3 polls to send 2 -> 4 READY msg, +0 msgs \033[0m')
    z2w.write( ('poll',) )
    print(waits(pump, a2z, p2z))

    log.debug('\033[91m +0 READY +1 = 3 polls to send 3 -> 1 READY msg, 1 ACCEPTS\033[0m')
    z2w.write( ('poll',) )
    print('\033[1mp1 output\033[0m', waits(pump, a2z, p2z))

    log.debug('\033[91m +0 READY +1 = 3 polls to send 3 -> 2 READY msg, 2 Doesnt accept \033[0m')
    z2w.write( ('poll',) )
    print(waits(pump, a2z, p2z))

    log.debug('\033[91m +0 READY +1 = 3 polls to send 3 -> 4 READY msg, 4 ACCEPTS\033[0m')
    z2w.write( ('poll',) )
    print(waits(pump, a2z, p2z))

#    log.debug('\033[91m +0 READY +1 = 3 polls to send 1 -> 2 READY msg, 2 ACCEPTS\033[0m')
#    z2w.write( ('poll',) )
#    print('\033[1mp2 output\033[0m', waits(pump, a2z, p2z))
#
#    log.debug('\033[91m +0 READY +1 = 3 polls to send 1 -> 3 READY msg, 3 ACCEPTS\033[0m')
#    z2w.write( ('poll',) )
#    print('\033[1mp3 output\033[0m', waits(pump, a2z, p2z))

if __name__=='__main__':
    print('\n\t\t\033[93m [IDEAL WORLD] \033[0m\n')
    execWrappedUC(env1, [('F_bracha',Syn_Bracha_Functionality)], WrappedPartyWrapper, Syn_FWrapper, 'F_bracha', RBC_Simulator)
    print('\n\t\t\033[93m [REAL WORLD] \033[0m\n')
    execWrappedUC(env1, [('F_chan',Syn_Channel)], WrappedProtocolWrapper, Syn_FWrapper, Syn_Bracha_Protocol, DummyWrappedAdversary)
