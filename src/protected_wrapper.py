import gevent
import random
import dump
import comm
from itm import ITMFunctionality
from hashlib import sha256
from g_ledger import Ledger_Functionality
from collections import defaultdictionary
from gevent.event import AsyncResult
from gevent.queue import Channel, Queue


'''
    Sits between the parties and the g_ledger functionality. It creates
    and stores the mapping between sid,pid and pseudonym. The purpose of
    this distinction is so that the ideal world doesn't have to try to 
    match the address of the real world contract that was deployed.
    Example: since the environment can assign public keys to each itm that
    is deployed, it can give real world and ideal world difference public
    keys. Then the contract address is different, so contract can be distinguished
    since information about nonces and address is known

    Q: Why is it necessary to have this extra layer if all it does is translate
        sid,pid pairs into addresses? Couldn't you just have g_ledger deal with
        only sid,pid pairs?
    A: No, you can't because in the real world a contract is deployed to the 
        blockchain that is not a functionality or an itm and hence has no
        sid,pid assigned to it. If a random one is assigned, the environment
        can clearly see one case where all txs go to/from an sid,pid pair in the
        ideal world and the other case where a random generated addresses
        is used, essentially revealing which one is the real world or ideal world.
'''
class Protected_Wrapper(object):
    def __init__(self, ledger):
        self.ledger = ledger
        self.addresses = {}
        self.allowed = defaultdict(set)

        self.outputs = self.ledger.outputs
        self.adversary_out = self.ledger.adversary_out
        
        self.DELTA = self.ledger.DELTA

    '''
        All parties, including the adversary, must access the protected mode.
        This means that they can only see sid,pid combos and no actual mapping between
        then and pseudonyms in the underlying blockchain
    '''
    def input_msg(self, sender, _msg):
        sid,pid = None,None
        if sender:
            sid,pid = sender
            if sender not in self.addresses:
                a = self.subroutine_genym(sender)
        
        # if functionality, it can choose wrapper/no-wrapper
        # adversary can also decide which he wants to talk to
        if comm.isf(sid,pid) or comm.isadversary(sid,pid):
            print('msg', _msg)
            wrapper,msg = _msg
            print('wrapper is set to', wrapper)
        else:
            msg = _msg
            wrapper = True
    
        if not wrapper:
            if comm.isf(sid,pid):
                self.ledger.input_msg(sender, msg)
            else:
                dump.dump()
        else:
            if msg[0] == 'transfer':
                _,_to,_val,_data,_fro = msg

                to = self.genym(_to)
                val = _val
                data = _data
                '''
                    Only a functionality can send a transaction FROM a random
                    address.
                '''
                if comm.isf(sid,pid):
                    print('*** _fro', _fro)
                    fro = self.genym(_fro)
                else:
                    print('*** sender', sender)
                    fro = self.genym(sender)

                msg = (msg[0], to, val, data, fro)
                print('[PROTECTED]', 'transger msg', msg) 
            elif msg[0] == 'tick':
                _,_sender = msg

                _sender = self.genym(_sender)

                msg = (msg[0], _sender)

            self.ledger.input_msg(sender,msg)

    def genym(self, key):
        if key not in self.addresses:
            return self.subroutine_genym(key)
        else:
            return self.addresses[key]

    def subroutine_genym(self, key):
        p = str(key).encode()
        h = sha256(p).hexdigest()[24:]
        print('[PROTECTED]', 'new pseudonym ( %s, %s )' % (key, h))
        self.addresses[key] = h
        return self.addresses[key]

    '''
        So far subroutine messages are only for the ledger
        so they are passed through all of the time
    '''
    def subroutine_msg(self, sender, _msg):
        sid,pid = sender

        if type(_msg[0]) == bool:
            wrapper,msg = _msg
        else:
            msg = _msg
            wrapper = True

        if wrapper:
            if msg[0] == 'genym':
                return self.subroutine_genym(sid,pid)
            elif msg[0] == 'getbalance':
                print('[protected] getbalance subroutine call')
                _,_addr = msg
                addr = self.genym(_addr)
                msg = (msg[0], addr)
                return self.ledger.subroutine_msg(sender,msg)
            else:
                return self.ledger.subroutine_msg(sender, msg)
        else:
            return self.ledger.subroutine_msg(sender, msg)

    '''
        Adversary, like the parties, can only talk to the protected
        mode so mapping between sid,pid needs to happen here
    '''
    def adversary_msg(self, sender, _msg):
        sid,pid = sender
        wrapper,msg = _msg

        if not wrapper:
            self.ledger.adversary_msg(sender, msg)
        else:
            self.ledger.adversary_msg(sender, msg)


def ProtectedITM(sid,pid, G):
    p = Protected_Wrapper(G)
    p_itm = ITMFunctionality(sid,pid)
    p_itm.init(p)
    return p, p_itm
