import dump
import gevent

import numpy as np
from enum import Enum

from collections import defaultdict
from queue import Queue

from itm import UCAsyncWrappedProtocol
from utils import wait_for, MessageTag
from honeybadgermpc.polywrapper import PolyWrapper
from contract import Contract, TransitionType

    
class Functionalities(Enum):
    F_ATOMIC = 'F_atomic'
    F_OFFLINE = 'F_offline'
    F_ASYNC = 'F_async'
    
class ContractHandler:
    def __init__(self, prot):
        self.inputs = Queue()
        self.msgs = list()
        self.current_transition = None
        self.transition_count = 0
        self.prot = prot
        self.pw = PolyWrapper(len(self.prot.parties))
        self.step1 = False
        self.contract = None
    def set_contract(self, contract, id):
        self.contract = contract
        self.id = id
    def add_input(self, input):
        self.inputs.put(input)
        return self.compute_actions()
    def add_msg(self, senderpid, msg):
        #msg format: (type, step, *args)
        if not isinstance(msg, tuple): return []
        if not ((msg[0] == TransitionType.MULT and len(msg) == 4) or (msg[0] == TransitionType.OUT and len(msg) == 3)): return []
        if (senderpid, msg) not in self.msgs:
            self.msgs.append((senderpid, msg))
        return self.compute_actions()
    def compute_actions(self):
        if self.contract is None: return []
        if self.current_transition is None: 
            self.current_transition = self.contract.get_transition()
            if self.current_transition is None:
                if self.inputs.empty(): return []
                dealer, var = self.inputs.get()
                self.contract.set_var(dealer, var, True)
                return self.compute_actions()
            self.transition_count += 1

        type, vars = self.current_transition
        if type == TransitionType.ADD:
            coeffs, vars, outvar = vars
            self.contract.set_var(outvar, np.dot(coeffs, vars))
            self.current_transition = None
            return self.compute_actions()
        if type == TransitionType.MULT:
            in1, in2, outvar = vars
            if self.step1 is False:
                self.step1 = True
                msg = (MessageTag.TRIPLE, (self.id, self.transition_count, outvar))
                m = self.prot.write_to_functionality(Functionalities.F_OFFLINE, msg)
                _, self.triple = m.msg[1]
                left = in1 - self.triple[0]
                right = in2 - self.triple[1]
                left_msg = (self.id, (type, (self.transition_count, outvar), 'left', left))
                right_msg = (self.id, (type, (self.transition_count, outvar), 'right', right))
                for pid in self.prot.parties:
                    self.prot.write_to_party(pid, left_msg)
                    self.prot.write_to_party(pid, right_msg)
                return self.add_msg(self.prot.pid, left_msg) + self.add_msg(self.prot.pid, right_msg)
            pid_set = set()
            left_vals = [(pid, msg[3]) for (pid, msg) in self.msgs if msg[0] == TransitionType.MULT and msg[1] == (self.transition_count, outvar) and msg[2] == 'left' and not (pid not in pid_set and pid_set.add(pid))]
            right_vals = [(pid, msg[3]) for (pid, msg) in self.msgs if msg[0] == TransitionType.MULT and msg[1] == (self.transition_count, outvar) and msg[2] == 'right' and not (pid not in pid_set and pid_set.add(pid))]
            left_arr = [None]*self.pw.n
            right_arr = [None]*self.pw.n
            for (pid, point) in left_vals: left_arr[pid] = point
            for (pid, point) in right_vals: right_arr[pid] = point
            left_poly = self.pw.reconstruct(left_arr)
            right_poly = self.pw.reconstruct(right_arr)
            
            if left_poly is not None and right_poly is not None:
                self.step1 = False
                self.current_transition = None
                l_secret = self.pw.secret(left_poly)
                r_secret = self.pw.secret(right_poly)
                self.contract.set_var(outvar, l_secret*r_secret + self.triple[0]*r_secret + self.triple[1]*l_secret + self.triple[2])
                return self.compute_actions()
        if type == TransitionType.OUT:
            varname, val = vars
            if self.step1 is False:
                self.step1 = True
                msg = (self.id, (type,  (self.transition_count, varname), val))
                for pid in self.prot.parties:
                    self.prot.write_to_party(pid, msg)
                return self.add_msg(self.prot.pid, msg)
            pid_set = set()
            
            vals = [(pid, msg[2]) for (pid, msg) in self.msgs if msg[0] == TransitionType.OUT and msg[1] == (self.transition_count, varname) and not (pid not in pid_set and pid_set.add(pid))]
            arr = [None]*self.pw.n
            for (pid, point) in vals: arr[pid] = point
            poly = self.pw.reconstruct(arr)
            if poly is not None: 
                self.step1 = False
                self.current_transition = None
                self.contract.set_output(varname)
                return [(MessageTag.OUTPUT, (self.id, varname), self.pw.secret(poly))] + self.compute_actions()
            return []
       
        return []
        
class OnlineMPCProtocol(UCAsyncWrappedProtocol):
        
    def __init__(self, sid, pid, channels, pump, poly):
        self.ssid, self.parties = sid
        self.msg_counts = defaultdict(int)
        self.BC = []
        self.contracts = []
        self.inputs = defaultdict(Queue)
        self.input_counts = defaultdict(int)
        self.contract_handlers = defaultdict(lambda: ContractHandler(self))
        self.pump = pump
        UCAsyncWrappedProtocol.__init__(self, sid, pid, channels, poly)
        
    def env_msg(self, msg):
        imp = msg.imp
        msg = msg.msg
        
        if msg[0] == MessageTag.INPUT_VAL:
            input = msg[1]
            contract_id = msg[2]
            self.write('p2f', ((self.get_sid(Functionalities.F_OFFLINE), Functionalities.F_OFFLINE), (MessageTag.RAND,)))
            m = wait_for(self.f2p)
            _, val, label = m.msg[1]
            tx = (MessageTag.INPUT_VAL, input - val, label, contract_id)
            self.write('p2f', ((self.get_sid(Functionalities.F_ATOMIC), Functionalities.F_ATOMIC), (MessageTag.TX, tx)))
            m = wait_for(self.f2p)
        if msg[0] == MessageTag.CREATE_CONTRACT:
            contract = msg[1]
            tx = (MessageTag.CREATE_CONTRACT, contract)
            self.write('p2f', ((self.get_sid(Functionalities.F_ATOMIC), Functionalities.F_ATOMIC), (MessageTag.TX, tx)))
            m = wait_for(self.f2p)
        self.pump.write("pump")
    def adv_msg(self, msg):
        self.pump.write("pump")

    def func_msg(self, d):
        imp = d.imp
        func, msg = d.msg
        msgs = []
        if func[1] == Functionalities.F_ATOMIC:
            tag, BC = msg
            if tag != "blockchain": 
                self.write('p2z', ('out', []))
                return
            if len(BC) <= len(self.BC): 
                self.write('p2z', ('out', []))
                return
            for idx, tx in enumerate(BC[len(self.BC):]):
                tx, dealer = tx
                if tx[0] == MessageTag.INPUT_VAL:
                    val = tx[1]
                    label = tx[2]
                    contract_id = tx[3]

                    self.input_counts[dealer] += 1
                    var_name = (dealer, self.input_counts[dealer])
                    
                    self.write('p2f', ((self.get_sid(Functionalities.F_OFFLINE), Functionalities.F_OFFLINE), (MessageTag.LABEL, (dealer, label))))
                    
                    m = wait_for(self.f2p)
                    _, share = m.msg[1]
                                        
                    secret_input = val + share
                    if contract_id < len(self.contracts):
                        sid, pid = dealer
                        self.contract_handlers[contract_id].add_input((pid, secret_input))
                        #self.inputs[contract_id].put((dealer, secret_input))
                    # try:
                        # self.contracts[contract_id].set_var(dealer, secret_input, True)
                    # except:
                        # continue
                        
                    input_msg = (MessageTag.DEFINED_VAR, var_name, contract_id, len(self.BC)+idx)
                    msgs.append(input_msg)
                if tx[0] == MessageTag.CREATE_CONTRACT:
                    contract_class = tx[1]
                    if issubclass(contract_class, Contract):
                        contract_id = len(self.contracts)
                        contract_msg = (MessageTag.DEFINED_CONTRACT, contract_class, contract_id, len(self.BC)+idx)
                        self.contracts.append(contract_class())
                        self.contract_handlers[contract_id].set_contract(contract_class(), contract_id)
                        msgs.append(contract_msg)
            msgs.extend(self.perform_transitions())
            self.BC = BC
        elif func[1] == Functionalities.F_ASYNC:
            msgs = self.perform_transitions(msg)
        elif func[1] == Functionalities.F_OFFLINE:
            pass # should not happen here
        
        if len(msgs) == 0:
            self.pump.write("pump")
        else:
            self.write('p2z', (MessageTag.OUTPUT, msgs))
    def perform_transitions(self, msg = None):
        if msg is not None:
            tag, senderpid, msg = msg
            contract_id = msg[0]
            msg = msg[1]
            msgs = self.contract_handlers[contract_id].add_msg(senderpid, msg)
            return msgs
        out = []
        for handler in list(self.contract_handlers.values()): 
            out.extend(handler.compute_actions())
        return out
                
    def get_sid(self, func, to = None):
        if func == Functionalities.F_ATOMIC:
            return self.sid
        if func == Functionalities.F_OFFLINE:
            return self.sid
        if func == Functionalities.F_ASYNC:
            self.msg_counts[to] += 1
            return (self.ssid, (self.sid, self.pid), (self.sid, to), self.msg_counts[to])
     
    def write_to_party(self, pid, msg):
        self.write('p2f', ((self.get_sid(Functionalities.F_ASYNC, to = pid), Functionalities.F_ASYNC), msg))
        m = wait_for(self.f2p)
    
    def write_to_functionality(self, func, msg):
        self.write('p2f', ((self.get_sid(func), func), msg))
        return wait_for(self.f2p)