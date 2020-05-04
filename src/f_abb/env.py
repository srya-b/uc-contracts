from itm import WrappedProtocolWrapper, WrappedPartyWrapper
from adversary import DummyWrappedAdversary
from prot_online import OnlineMPCProtocol, ContractHandler
from asyncwrapper import AsyncWrapper
from f_atomic import AtomicBroadcastFunctionality
from f_offline import OfflinePhaseFunctionality
from f_async import AsyncBroadcastFunctionality
from f_abb import AsyncABBFunctionality
from sim_abb import ABBSimulator
from prot_online import Functionalities as F
from contract import ExampleContract, TransitionType
from execuc import execWrappedUC
from utils import z_get_leaks, waits, MessageTag
import comm

from honeybadgermpc.polywrapper import PolyWrapper

import logging
from logging import FileHandler, INFO
from collections import defaultdict



class InfoFileHandler(FileHandler):
    def __init__(self, filename, mode='a', encoding=None, delay=False):
        FileHandler.__init__(self, filename, mode, encoding, delay)

    def emit(self, record):
        if not record.levelno == INFO:
            return
        FileHandler.emit(self, record)

class AdvWrapper:
    def __init__(self, parties, sid, pid, z2a, a2z):
        self.parties = parties
        self.pid = pid
        self.sid = sid
        self.z2a = z2a
        self.a2z = a2z
        self.outputs = {}
        self.output = None
        self.BC = []
        self.handlers = defaultdict(lambda: ContractHandler(self))
        self.contracts = []
    
    def write_to_party(self, party, d):
        # dummy function to handle contracthandler
        id, msg = d
        if msg[0] == TransitionType.OUT:
            var = (id, msg[1])
            val = msg[2]
            self.outputs[var] = msg[2]
            self.output = msg[2]
    
    def write_to_functionality(self, func, d):
        assert func == F.F_OFFLINE
        inner_msg = ((self.sid, func), d)
        party_msg = ((self.sid, self.pid), ('P2F', inner_msg))
        adv_msg = ('A2P', party_msg)
        self.z2a.write(adv_msg)
        out = waits(self.a2z)
        log.info(out)
        out.msg = out.msg[1]
        return out
        
    def set_blockchain(self, BC):
        if len(BC) <= len(self.BC): return
        for (msg, sender) in BC[len(self.BC):]:
            if msg[0] == MessageTag.CREATE_CONTRACT:
                self.handlers[len(self.contracts)].set_contract(msg[1](), len(self.contracts))
                self.handlers[len(self.contracts)].compute_actions()
                self.contracts.append(msg[1]())
            if msg[0] == MessageTag.INPUT_VAL:
                (tag, val, label, contract_id) = msg
                func_msg = (MessageTag.LABEL, (sender, label))
                _, share = self.write_to_functionality(F.F_OFFLINE, func_msg).msg[1]                
                secret_input = val + share
                sid, pid = sender
                self.handlers[contract_id].add_input((pid, secret_input))
        self.BC = BC

def env(static, z2p, z2f, z2a, z2w, a2z, p2z, f2z, w2z, pump):
    n = 5
    pw = PolyWrapper(n)
    sid = ('ssid', tuple(range(n)))
    static.write( (('sid', sid), ('crupt', (sid, 0))) )
    log.info(waits(pump, a2z, p2z, w2z, f2z))
    
    adv_wrapper = AdvWrapper(tuple(range(n)), sid, 0, z2a, a2z)
    
    z2p.write( ((sid, 1), (MessageTag.CREATE_CONTRACT, ExampleContract)) )
    log.info(waits(pump, a2z, p2z))
    
    tx = (MessageTag.CREATE_CONTRACT, ExampleContract)
    inner_msg = ((sid, F.F_ATOMIC), (MessageTag.TX, tx))
    z2a.write( ('A2P', ((sid, 0), ('P2F', inner_msg))) )
    log.info(waits(pump, a2z, p2z))

        
    z2a.write(('A2W', (MessageTag.SEND_LEAKS,)))
    log.info(waits(pump, a2z, p2z))
        
    z2a.write(('A2W', (MessageTag.SEND_LEAKS,)))
    log.info(waits(pump, a2z, p2z))
    
    z2a.write(('A2W', (MessageTag.DELAY, 2)))
    log.info(waits(pump, a2z, p2z))

    for pid in range(n):
        
        if pid == 0: 
            tx = (MessageTag.INPUT_VAL, 0, 1, 0)
            inner_msg = ((sid, F.F_ATOMIC), (MessageTag.TX, tx))
            z2a.write( ('A2P', ((sid, pid), ('P2F', inner_msg))) )
            log.info(waits(pump, a2z, p2z))
            continue
        z2p.write( ((sid, pid), (MessageTag.INPUT_VAL, 2**pid, 0)))
        log.info(waits(pump, a2z, p2z))
    points = []
    for _ in range(250):
        z2w.write( (MessageTag.ADVANCE,) )
        msg = waits(pump, a2z, p2z)
        log.info(msg)

        try:
            (c_party, (func, (tag, senderpid, (contract_id, msg_)))) = msg.msg
            adv_wrapper.handlers[contract_id].add_msg(senderpid, msg_)
            type, varname, share = msg_
            points.append((senderpid, share))
        except (ValueError, TypeError) as e:
            pass
            
        try:
            (c_party, (func, (tag, blockchain))) = msg.msg
            adv_wrapper.set_blockchain(blockchain)
        except (ValueError, TypeError) as e:
            pass
            
        try:
            (party, (tag, arr)) = msg.msg
            for elem in arr: 
                if elem[0] == MessageTag.OUTPUT: secret = elem[2]
        except (ValueError, TypeError) as e:
            pass
            
    points2 = [None]*n
    for (pid, share) in points: points2[pid] = share
    assert pw.secret(pw.reconstruct(points2)) == secret
    assert pw.share(pw.reconstruct(points2), 0) == adv_wrapper.output
if __name__ == '__main__':
    log = logging.getLogger('ideal')
    log.addHandler(InfoFileHandler('ideal.log'))
    
    print('\n\t\t\033[93m [IDEAL WORLD] \033[0m\n')
    execWrappedUC(env, [('F_abb', AsyncABBFunctionality)], WrappedPartyWrapper, AsyncWrapper, 'F_abb', ABBSimulator)

    log = logging.getLogger('real')
    log.addHandler(InfoFileHandler('real.log'))
    
    print('\n\t\t\033[93m [REAL WORLD] \033[0m\n')
    execWrappedUC(env, [(F.F_ATOMIC, AtomicBroadcastFunctionality), (F.F_OFFLINE, OfflinePhaseFunctionality), (F.F_ASYNC, AsyncBroadcastFunctionality)], WrappedProtocolWrapper, AsyncWrapper, OnlineMPCProtocol, DummyWrappedAdversary)
