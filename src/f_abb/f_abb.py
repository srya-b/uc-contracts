import dump
import gevent

from itm import UCAsyncWrappedFunctionality
import numpy as np
from enum import Enum
from utils import MessageTag
from contract import TransitionType, Contract

from collections import defaultdict

class AsyncABBFunctionality(UCAsyncWrappedFunctionality):
         
    def __init__(self, sid, pid, channels, pump):
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
        self.pump = pump
        UCAsyncWrappedFunctionality.__init__(self, sid, pid, channels)
    
    def adv_msg(self, msg):
        self.pump.write("pump") # adversary provides no input to F_ABB, only impact through 'eventually'

    def party_msg(self, msg):
        imp = msg.imp
        msg = msg.msg
        dealer, msg = msg
        if msg[0] == MessageTag.INPUT_VAL:
            input = msg[1]
            contract_id = msg[2]
            self.eventually(self.new_input, [dealer, input, contract_id])
            self.leak((MessageTag.INPUT_VAL, (contract_id, dealer)))
        if msg[0] == MessageTag.CREATE_CONTRACT:
            contract = msg[1]
            self.eventually(self.new_contract, [contract])
            self.leak((MessageTag.CREATE_CONTRACT, (contract, dealer)))
        self.pump.write("pump")

    def env_msg(self, msg):
        self.pump.write("pump") # environment cannot interact with functionality
        
    def new_input(self, dealer, input, contract_id):
        self.input_counts[dealer] += 1
        var_name = (dealer, self.input_counts[dealer])
        
        self.inputs[var_name] = (input, contract_id)
        
        pos = len(self.BC)
        self.BC.append( (MessageTag.DEFINED_VAR, (var_name, contract_id)) )
        
        try:
            self.contracts[contract_id].set_var(dealer, input, True)
        except:
            return
            
        
        while True:
            transition = self.contracts[contract_id].get_transition()
            if transition is None:
                break
                
            type, vars = transition
            if type == TransitionType.OUT:
                varname, val = vars
                self.outputs.append((contract_id, (varname, val), pos))
                self.contracts[contract_id].set_output(varname)
                continue
                
            if type == TransitionType.ADD:
                coeffs, vars, outvar = vars
                self.contracts[contract_id].set_var(outvar, np.dot(coeffs, vars))
            if type == TransitionType.MULT:
                in1, in2, outvar = vars
                self.contracts[contract_id].set_var(outvar, in1*in2)
            
        self.generate_outputs(pos)
        self.leak(self.outputs)
        self.pump.write("pump")
    
    def new_contract(self, contract):
        if issubclass(contract, Contract):
            contract_id = len(self.contracts)
            self.contracts.append(contract())
            pos = len(self.BC)
            self.BC.append( (MessageTag.DEFINED_CONTRACT, (contract, contract_id)) )
            self.generate_outputs(pos)
        self.pump.write("pump")
        
    def generate_outputs(self, pos):
        for party in self.parties:
            self.eventually(self._generate_outputs, [pos, party])
            
    def _generate_outputs(self, pos, party):
        if pos <= self.last[party]: return
        
        for out in self.outputs:
            print(out)
            if not (out[2] > self.last[party] and out[2] <= pos): continue
            self.eventually(self.write, ['f2p', ((self.sid, party), (out[0], out[1]))])
                
        msgs = self.BC[self.last[party]+1 : pos+1]
        self.last[party] = pos
        self.write('f2p', ((self.sid, party), msgs))
        