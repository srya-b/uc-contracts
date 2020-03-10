import dump
import gevent

from itm import UCAsyncWrappedFunctionality
import numpy as np
from enum import Enum


class AsyncABBFunctionality(UCAsyncWrappedFunctionality):
    class Defined(Enum):
        CONTRACT = 1
        VAR = 2
        
    class MessageType(Enum):
        INPUT_VAL = 1
        CREATE_CONTRACT = 2
         
    def __init__(self, sid, pid, channels):
        self.sid = sid
        self.ssid = sid[0]
        self.parties = sid[1] # TODO: define sid to include parties
        self.pid = pid
        self.BC = []
        self.inputs = {}
        self.contracts = []
        self.outputs = []
        self.last = defaultdict(lambda: -1)
        self.input_counts = defaultdict(int)
        UCAsyncWrappedFunctionality.__init__(self, sid, pid, channels)
    
    def adv_msg(self, msg):
        pass # adversary provides no input to F_ABB, only impact through 'eventually'

    def party_msg(self, msg):
        dealer, msg = msg
        msg = msg.msg
        imp = msg.imp
        if msg[0] == MessageType.INPUT_VAL:
            input = msg[1]
            contract_id = msg[2]
            self.eventually(self.new_input, [dealer, input, contract_id])
            self.leak((MessageType.INPUT_VAL, (contract_id, dealer)))
        if msg[0] == MessageType.CREATE_CONTRACT:
            contract = msg[1]
            self.eventually(self.new_contact, [contract])
            self.leak((MessageType.CREATE_CONTRACT, (contract, contract_id, dealer)))

    def env_msg(self, msg):
        dump.dump() # environment cannot interact with functionality

    def wrapper_msg(self, msg):
        pass
        
    def new_input(self, dealer, input, contract_id):
        
        self.input_counts[dealer] += 1
        var_name = (dealer, self.input_counts[dealer])
        
        self.inputs[var_name] = (input, contract_id)
        
        pos = len(self.BC)
        self.BC.append( (Defined.VAR, var_name) )
        
        try:
            self.contracts[contract_id].set_var(dealer, input, True)
        except:
            return
            
        
        while True:
            transition = self.contracts[contract_id].get_transition()
            if transition is None:
                break
                
            type, vars = transition
            if type == 'out':
                self.outputs.extend((vars, pos)) # varname, val = vars
                continue
                
            if type == 'add':
                coeffs, vars, outvar = vars
                self.contracts[contract_id].set_var(outvar, np.dot(coeffs, vars))
            if type == 'mult':
                in1, in2, outvar = vars
                self.contracts[contract_id].set_var(outvar, in1*in2)
            
        self.generate_outputs(pos)
        self.leak(outputs)
    
    def new_contract(self, contract):
        contract_id = len(self.contracts)
        self.contracts.append(contract)
        pos = len(self.BC)
        self.BC.append( (Defined.CONTRACT, (contract, contract_id)) )
        self.generate_outputs(pos)
        
    def generate_outputs(self, pos):
        for party in self.parties:
            self.eventually(self._generate_outputs, [pos, party])
            
    def _generate_outputs(self, pos, party):
        if pos <= self.last[i]: return
        
        for out in self.outputs:
            if not (out[1] > self.last[i] and out[1] <= j): continue
            self.eventually(self.write, ['f2p', ((self.sid, party), out[0])])
                
        msgs = self.BC[self.last[i]+1 : pos+1]
        self.last[i] = pos
        self.write('f2p', ((self.sid, party), msgs))
        