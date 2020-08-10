from utils import wait_for
from syn_katz import Clock_Functionality, BD_SEC_Functionality, KatzDummyAdversary
from itm import ProtocolWrapper, PartyWrapper
from syn_katz.f_bracha import Bracha_Protocol, SFE_Bracha_Functionality, BrachaSimulator

def env1(static, z2p, z2f, z2a, a2z, p2z, f2z):
    sid = ('one', 4, (1,2,3,4))
    static.write( ('sid', sid) )

    # Start synchronization requires roundOK first to determine honest parties
    # giving input to a party before all have done this will result in Exception
    z2p.write( ((sid,1), ('sync',)) )
    wait_for(a2z)
    z2p.write( ((sid,2), ('sync',)) )
    wait_for(a2z)
    z2p.write( ((sid,3), ('sync',)) )
    wait_for(a2z)
    z2p.write( ((sid,4), ('sync',)) )
    wait_for(a2z)
   
    ## DEALER INPUT
    z2p.write( ((sid,1), ('input',10)) )
    wait_for(a2z)

    # N=3 ACTIVATIONS FOR ROUND=1     (Dealer sends VAL)
    for i in range(4):
        z2p.write( ((sid,1), ('output',)))
        wait_for(a2z)
        z2p.write( ((sid,2), ('output',)))
        wait_for(a2z)
        z2p.write( ((sid,3), ('output',)))
        wait_for(a2z)
        z2p.write( ((sid,4), ('output',)))
        wait_for(a2z)

    # N=3 ACTIVATIONS FOR ROUND=2   (get VAL, send ECHO)
    for i in range(4):
        z2p.write( ((sid,1),('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,2), ('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,3), ('output',)))
        wait_for(a2z)
#        sys.exit(0)
        z2p.write( ((sid,4), ('output',)))
        wait_for(a2z)

    # N=3 ACTIVATIONS FOR ROUND=3   (get ECHO, send READY)
    for _ in range(3): 
        z2p.write( ((sid,1), ('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,2), ('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,3), ('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,4), ('output',)))
        wait_for(a2z)
    
    z2p.write( ((sid,1), ('output',)) )
    wait_for(a2z)
    z2p.write( ((sid,1), ('output',)) )
    fro,msg = wait_for(p2z)
    assert msg[0] == 'early'
    z2p.write( ((sid,2), ('output',)) )
    wait_for(a2z)
    z2p.write( ((sid,3), ('output',)) )
    wait_for(a2z)
    z2p.write( ((sid,4), ('output',)))
    wait_for(a2z)

    # First activation should get READY and ACCEPT  (get READY, wait n activations to output)
    for i in range(4):
        z2p.write( ((sid,3), ('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,1), ('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,2), ('output',)) )
        wait_for(a2z)
        z2p.write( ((sid,4), ('output',)))
        wait_for(a2z)
        
    z2p.write( ((sid,1), ('output',)) )
    fro,msg = wait_for(p2z)
    print("P1 output", msg)
    z2p.write( ((sid,2), ('output',)) )
    fro,msg = wait_for(p2z)
    print("P2 output", msg)
    z2p.write( ((sid,3), ('output',)) )
    fro,msg = wait_for(p2z)
    print("P3 output", msg)
    z2p.write( ((sid,4), ('output',)))
    fro,msg = wait_for(p2z)
    print("P4 output", msg)

from uc import execUC

# Real world
print('\033[91m \n\n######## \033[1mREAL WORLD\033[0m\033[91m ########\n\n\033[0m')
execUC(env1, [('F_clock',Clock_Functionality),('F_bd',BD_SEC_Functionality)], ProtocolWrapper, Bracha_Protocol, KatzDummyAdversary)
print('\033[91m \n\n######## \033[1mIDEAL WORLD\033[0m\033[91m ########\n\n\033[0m')
execUC(env1, [('F_sfe', SFE_Bracha_Functionality)], PartyWrapper, 'F_sfe', BrachaSimulator)
