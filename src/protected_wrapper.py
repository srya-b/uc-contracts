import gevent
import random
import dump
import comm
from itm import ITMFunctionality
from hashlib import sha256
from g_ledger import Ledger_Functionality
from collections import defaultdict
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

    sid access is also restricted. Only those in the same sid can access a
    private contracts. 

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
        self.raddresses = {}
        self.private = {}

        self.outputs = self.ledger.outputs
        self.adversary_out = self.ledger.adversary_out
        
        self.DELTA = self.ledger.DELTA

    def __str__(self):
        return str(self.ledger)

    def iscontract(self, addr):
        return addr in self.ledger.contracts

    '''
        All honest parties must access the protected mode.
        This means that they can only see sid,pid combos and no actual mapping between
        then and pseudonyms in the underlying blockchain
    '''

    #def inputp2f(self, msg):
    #    sender,msg = msg
    #    assert not comm.isf(*sender), and not comm.isadversary(*sender)
    #    
    #    if msg[0] == 'transfer':
    #        _,_to,_val,_data,_fro = msg
    #        to = self.genym(_to)
    #        val = _val
    #        data = _data
    #        
    #        if self.iscontract(_to):
    #            to = _to
    #            if to in self.private and sid != self.private[to]:
    #                data = ()
    #    elif msg[0] == 'tick':
    #        _,_sender = msg
    #        _sender = self.genym(_sender)
    #        msg = (msg[0], _sender)
    #    elif msg[0] == 'contract-create':
    #        _,_addr,_val,_data,_private,_fro = msg
    #        fro = self.genym(_fro)
    #        if _private: self.private[_addr] = sid
    #        msg = (msg[0], _addr, _val, _data, _private, fro)
    #    self.ledger.input_msg(sender, msg) 

    #def inputf2f(self, msg):
    #    sender,msg = msg
    #    assert comm.isf(*sender)

    #    if msg[0] == 'transfer':
    #        _,_to,_val,_data,_fro = msg
    #        to = self.genym(_to)
    #        val = _val
    #        data = _data
    #        if self.iscontract(_to):
    #            to = _to
    #            if to in self.private and sid != self.private[to]:
    #                data = ()
    #        fro = self.genym(_fro)
    #        msg = (msg[0], to, val, data, fro)
    #    else:
    #        raise Exception('What you be passing into my wrapper???', msg)
    #    self.ledger.input_msg(sender, msg)
    #        
    #def inputa2f(self, msg):
    #    sender,msg = msg
    #    
    #    if msg[0] == 'tick':
    #        addr = self.genym(sender)
    #        msg = (msg[0], addr, msg[1])
    #        self.ledger.adversary_msg(sender, msg)
    #    else: 
    #        self.ledger.adversary_msg()

    def input_msg(self, sender, _msg):
        sid,pid = None,None
        if sender:
            sid,pid = sender
            #if sender not in self.addresses:
            #    a = self.subroutine_genym(sender)
        
        # if functionality, it can choose wrapper/no-wrapper
        # adversary can also decide which he wants to talk to
        if comm.isf(sid,pid) or comm.isadversary(sid,pid):
            #print('msg', _msg)
            wrapper,msg = _msg
        else:
            msg = _msg
            wrapper = True
    
        if not wrapper:
            if msg[0] == 'tick' and comm.isadversary(sid,pid):
                self.ledger.adversary_msg(sender, msg)
            else:
                self.ledger.input_msg(sender, msg)
        else:
            #print('PROTECTED MSG', msg)
            if msg[0] == 'transfer':
                _,_to,_val,_data,_fro = msg
                to = self.genym(_to)
                val = _val
                data = _data

                '''Special rules for contracts'''
                if self.iscontract(_to):
                    to = _to
                    '''Contracts that are private and accessed by other sid
                    can only receive money from them, no execution'''
                    if to in self.private and sid != self.private[to]:
                        data = ()
                ''' Only a functionality can send a transaction FROM a random address.'''
                if comm.isf(sid,pid):
                    fro = self.genym(_fro)
                    #if len(rest):               # This means that the functionality has specified a delay
                    #    deadline = rest[0]
                    #    msg = ('transferf', to, val, data, fro, deadline)
                else:
                    fro = self.genym(sender)
                msg = (msg[0], to, val, data, fro)
                #print('[PROTECTED]', 'transger msg', msg)
            elif msg[0] == 'tick':
                _,_sender = msg
                _sender = self.genym(_sender)
                msg = (msg[0], _sender)
            elif msg[0] == 'contract-create':
                _,_addr,_val,_data,_private,_fro = msg
                if comm.isf(sid,pid):
                    fro = self.genym(_fro)
                else:
                    fro = self.genym(sender)
                ''' No translation necessary for the address '''
                if _private: self.private[_addr] = sid
                msg = (msg[0],_addr,_val,_data,_private,fro)
                print('Contract create, private:', _private)

            self.ledger.input_msg(sender,msg)

    def genym(self, key):
        if key not in self.addresses:
            return self.subroutine_genym(key)
        else:
            return self.addresses[key]

    def rgenym(self, image):
        assert image in self.raddresses
        return self.raddresses[image]

    def subroutine_genym(self, key):
        p = str(key).encode()
        h = sha256(p).hexdigest()[24:]
        #print('[PROTECTED]', 'new pseudonym ( %s, %s )' % (key, h))
        self.addresses[key] = h
        self.raddresses[h] = key
        return self.addresses[key]

    def subroutine_gettx(self, addr, to, fro):
        #assert to >= fro, 'to:%s   fro:%s' % (to, fro)
        if fro >= to: return []
        output = []
        '''Need to include 'to' in the range'''
        for blockno in range(fro,to+1):
            txqueue = self.ledger.txqueue[blockno]
            for tx in txqueue:
                if tx[0] == 'transfer':
                    to,val,data,fro,nonce = tx[1:]
                    if to == addr or fro == addr:
                        output.append((to, fro, val))  # Append (sender, amount)

        ''' Convert all addresses to sid,pid shit'''
        for i in range(len(output)):
            to,fro,val = output[i]
            output[i] = (self.rgenym(to), self.rgenym(fro), val)
        return output

    def subroutine_get_addr(self, sid, pid, key):
        if not comm.isf(sid,pid) and not comm.isadversary(sid,pid) and (sid,pid) != key:
            return None

        if key in self.addresses:
            return self.addresses[key]
        else:
            return None
    '''
        So far subroutine messages are only for the ledger
        so they are passed through all of the time
    '''
    def subroutine_msg(self, sender, _msg):
        sid,pid = sender

        #if type(_msg[0]) == bool:
        #    wrapper,msg = _msg
        #else:
        #    msg = _msg
        #    wrapper = True
        if comm.isf(sid,pid) or comm.isadversary(sid,pid):
            try:
                wrapper,msg = _msg
            except ValueError:
                msg = _msg
                wrapper = False
        else:
            msg = _msg
            wrapper = True

        if wrapper:
            if msg[0] == 'genym':
                return self.genym((sid,pid))
            elif msg[0] == 'getbalance':
                #print('[protected] getbalance subroutine call')
                _,_addr = msg
                addr = self.genym(_addr)
                msg = (msg[0], addr)
                return self.ledger.subroutine_msg(sender,msg)
            elif msg[0] == 'get-caddress':
                #_,_addr = msg
                #addr = self.genym(_addr)
                addr = self.genym((sid,pid))
                msg = (msg[0], addr)
                return self.ledger.subroutine_msg(sender,msg)
            elif msg[0] == 'get-addr':# and (comm.isf(*sender) or comm.isadversary(*sender)):
                return self.subroutine_get_addr(sid, pid, msg[1])
            elif msg[0] == 'get-txs':
                _,_addr,blockto,blockfro = msg
                addr = self.genym(_addr)
                return self.subroutine_gettx(addr, blockto, blockfro)
            elif msg[0] == 'read-output':
                _,_outputs = msg
                outputs = []
                for o in _outputs:
                    _sender,_nonce = o
                    outputs.append( (self.genym(sender), _nonce))
                msg = (msg[0], outputs)
                return self.ledger.subroutine_msg(sender, msg)
            elif msg[0] == 'contract-ref':
                _,_addr = msg
                if self.iscontract(_addr):
                    if _addr in self.private:
                        if sid == self.private[to]:
                            return self.ledger.subroutine_msg(sender,msg)
                    else:
                        return self.ledger.subroutine_msg(sender,msg)
            else:
                return self.ledger.subroutine_msg(sender, msg)
        else:
            return self.ledger.subroutine_msg(sender, msg)

    '''
        Unlike honest parties, adversary doesn't need to use the protected
        mode.
    '''
    def adversary_msg(self, sender, _msg):
        sid,pid = sender
        #print('PROTECTED MODE MESSAGE', _msg)
        wrapper,msg = _msg
        #print('DEBUG: adversary msg', msg)
        if not wrapper:
            self.ledger.adversary_msg(sender, msg)
        else:
            if msg[0] == 'tick':
                addr = self.genym(sender)
                msg = (msg[0], addr, msg[1])
            self.ledger.adversary_msg(sender, msg)

from comm import Channel
def ProtectedITM(sid,pid, G, a2f, f2f, p2f):
    p = Protected_Wrapper(G)
    p_itm = ITMFunctionality(sid,pid,a2f,f2f,p2f)
    p_itm.init(p)
    return p, p_itm
