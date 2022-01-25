from uc.utils import waits, collectOutputs
import gevent


""" This files contains several environments that are run by execUC a the 
bottom of the files. All environments conform to some dedault behavior:
  1. Setting the SID of this session. The SID often encodes protocol parameters.
  2. The list of crupt parties. This is the static corruptions model.
  3. Return some transcript of the communication from the honest parties and the
     adversary.
"""

def env(k, static, z2p, z2f, z2a, a2z, f2z, p2z, pump):
    print('\033[94m[ env_honest ]\033[0m')

    # The SID is encoded, ideally, as a tupe of strings. In reality
    # you can encode it however you want as long as the protocols/functionalities
    # you are running know how to parse it for information. The string is the
    # easiest as it works well with the multisession extension. ITMs then parse
    # the SID using `literal_eval` from the `ast` python package. In this example
    # the SID encodes some string to identify the session and the two PIDs of the
    # parties in this protocol: 1 and 2. 
    # See prot_com and F_com for how the SID is parsed.
    sid = ('one', "1, 2")

    # The static channel is given by `execUC` which waits to read the sid
    # and the set of crupt parties. In this case there are no crupt parties
    # hence nothing after `crupt`.
    static.write( (('sid',sid), ('crupt',)))

    # these two functions simply wait to read on the p2z and a2z channels
    # of the environment and append the message to a transcript that is returned
    # at the end of the environment code. Often times, when there are corrupt
    # parties you'll want to manually read from the a2z channel or p2z channel
    # and use the information in a meaningful way. (See other environments in this
    # and other apps.
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

    # spawn the functions
    g1 = gevent.spawn(_a2z)
    g2 = gevent.spawn(_p2z)
    

    # Give input msg=('commt', 0) to paty with PID=1 
    z2p.write( (1, ('commit',0)))
    waits(pump)
    # the `pump` channel is given to ALL ITMs and it is used for them to
    # forfeit control back to the environment. An ITM may either write 
    # to another ITM or return control to the environment through `pump`.

    z2p.write( (1, ('reveal',)))
    waits(pump)
   
    # kill the two threads
    gevent.kill(g1)
    gevent.kill(g2)

    # return the transcript
    print('transcript', transcript)
    return transcript

def env_receiver_crupt(k, static, z2p, z2f, z2a, a2z, f2z, p2z, pump):
    print('\033[94m[ env_receiver_crupt ]\033[0m')
    sid = ('one', "1, 2")

    # same SID but now PID=2 is crupt
    static.write( (('sid',sid), ('crupt', 2)))

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

    z2p.write( (1, ('commit',0)))
    waits(pump)

    z2p.write( (1, ('reveal',)))
    waits(pump)

    print('transcript', transcript)
    return transcript

def env_committer_crupt(k, static, z2p, z2f, z2a, a2z, f2z, p2z, pump):
    print('\033[94m[ env_committer_crupt ]\033[0m')
    sid = ('one', "1, 2")

    static.write( (('sid',sid), ('crupt', 1)))

    transcript = []
    def _p2z():
        while True:
            m = waits(p2z)
            #transcript.append('p2z: ' + str(m.msg))
            transcript.append(m)
            print('p2z: ' + str(m))
            pump.write('')

    gevent.spawn(_p2z)


    # Notice here we don't have any function to read from a2z 
    # automatically because we want to use the information on it
    # in a meaningful way.
    z2a.write( ('A2F', ('hash', (123, 0))))
    m = waits(a2z)
    print('env msg', m)
    _,lasthash = m
    print('last hash', lasthash)

    # we still (optionally) choose to append the message to the
    # transcript
    transcript.append('a2z: ' + str(m))

    z2a.write( ('A2P', (1, ('sendmsg', 2, ('commit',lasthash)))))
    waits(pump)

    #z2a.write( ('A2P', (1, ('sendmsg', 2, 'yoyoyo'))) )
    #waits(pump)

    #z2a.write( ('A2P', (1, ('sendmsg', 2, ('open', (123, 0))))))
    #waits(pump)

    return transcript

def env_committer_crupt_bad_open(k, static, z2p, z2f, z2a, a2z, f2a, p2z, pump):
    print('\033[94m[ env_committer_crupt_bad_open ]\033[0m')
    sid = ('one', "1, 2")
    static.write( (('sid',sid), ('crupt', 1)))

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
    _,lasthash = m
    print('last hash', lasthash)
    transcript.append('a2z: ' + str(m))

    z2a.write( ('A2P', (1, ('sendmsg', 2, ('commit',lasthash)))))
    waits(pump)

    z2p.write( (2, ('sendmsg', ('this is the right message'))) )
    #waits(pump)
    waits(a2z)

    z2a.write( ('A2P', (1, ('sendmsg', 2, 'yoyoyo'))) )
    waits(pump)

    # Committer commits, but opens with the wrong nonce, receiver
    # should not accept 
    z2a.write( ('A2P', (1, ('sendmsg', 2, ('open', (123, 1))))))
    waits(pump)

    return transcript
    

# Distinguisher might be a bad name here, this just prints the 
# transcripts in a pretty way and compares them with direct 
# equality. In reality many times with protocols that sample
# random information like the pedersen commitment, the transcripts
# ay never be equal.
def distinguisher(t_ideal, t_real):
    print('\n\t\033[93m Ideal transcript\033[0m')
    for i in t_ideal: print(str(i))

    print('\n\t\033[93m real transcript\033[0m')
    for i in t_real: print(str(i))

    if t_ideal == t_real:
        print("\033[92m[Distinguisher] They're the same\033[0m")
    else:
        print("\033[91m[Distinguisher] They're different\033[0m")

from uc.adversary import DummyAdversary
from f_ro import Random_Oracle_and_Chan
from prot_com import Commitment_Prot
from uc.execuc import execUC
from f_com import F_Com_Channel
from sim_com import Sim_Com
from uc.protocol import DummyParty, protocolWrapper

if __name__=='__main__':
    # run the ideal execution first with the dummy parties
    # and the simulator that we created
    tideal = execUC(
        128,
        env_receiver_crupt,
        F_Com_Channel,
        DummyParty,
        Sim_Com,
    )

    print('\n')
    # the real world uses the dummy adversary and F_ro + Channel
    # as the hybrid functionality that prot_com uses.
    treal = execUC(
        128,
        env_receiver_crupt,
        Random_Oracle_and_Chan,
        Commitment_Prot,
        DummyAdversary,
    )

    distinguisher(tideal, treal)
