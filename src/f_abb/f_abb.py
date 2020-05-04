import dump
import gevent

from itm import UCAsyncWrappedFunctionality
import numpy as np
from enum import Enum
from utils import MessageTag
from contract import TransitionType, Contract
from honeybadgermpc.polywrapper import PolyWrapper
from collections import defaultdict

from comm import isdishonest

class AsyncABBFunctionality(UCAsyncWrappedFunctionality):
         
    def __init__(self, sid, pid, channels, pump, poly):
        self.sid = sid
        self.ssid = sid[0]
        self.parties = sid[1] # TODO: define sid to include parties
        self.pw = PolyWrapper(len(self.parties))
        self.pid = pid
        self.BC = []
        self.inputs = {}
        self.contracts = []
        self.outputs = []
        self.messages = defaultdict(list)
        self.last = defaultdict(lambda: -1)
        self.input_counts = defaultdict(int)
        self.pump = pump
        self.initd = False
        UCAsyncWrappedFunctionality.__init__(self, sid, pid, channels, poly)
                    
    
    def adv_msg(self, msg):
        self.pump.write("pump") # adversary provides no input to F_ABB, only impact through 'eventually'

    def party_msg(self, msg):
        if not self.initd:
            self.initd = True
            for party in self.parties:
                self.eventually(self.deliver, [party], (MessageTag.DELIVER, (self.sid, party)))

        imp = msg.imp
        msg = msg.msg
        dealer, msg = msg
        if msg[0] == MessageTag.INPUT_VAL:
            input = msg[1]
            contract_id = msg[2]
            self.eventually(self.new_input, [dealer, self.pw.field(int(input)), contract_id], (MessageTag.INPUT_VAL, contract_id, dealer))
        if msg[0] == MessageTag.CREATE_CONTRACT:
            contract = msg[1]
            self.eventually(self.new_contract, [contract], (MessageTag.CREATE_CONTRACT, contract, dealer))
        if isdishonest(*dealer):
            self.write('f2p', (dealer, (MessageTag.OK,)))
        else:
            self.pump.write("pump")

    def env_msg(self, msg):
        self.pump.write("pump") # environment cannot interact with functionality
        
    def new_input(self, dealer, input, contract_id):
        self.input_counts[dealer] += 1
        var_name = (dealer, self.input_counts[dealer])
        
        self.inputs[var_name] = (input, contract_id)
        
        pos = len(self.BC)
        self.BC.append( (MessageTag.DEFINED_VAR, var_name, contract_id, pos) )
        
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
                self.outputs.append((MessageTag.OUTPUT, (contract_id, varname), val, pos))
                self.contracts[contract_id].set_output(varname)              
            elif type == TransitionType.ADD:
                coeffs, vars, outvar = vars
                self.contracts[contract_id].set_var(outvar, np.dot(coeffs, vars))
            elif type == TransitionType.MULT:
                in1, in2, outvar = vars
                self.contracts[contract_id].set_var(outvar, in1*in2)
            
        self.generate_outputs(pos)
        self.leak((MessageTag.OUTPUT, self.outputs))
        self.write('f2a', (MessageTag.OK,))
    
    def new_contract(self, contract):
        if issubclass(contract, Contract):
            contract_id = len(self.contracts)
            self.contracts.append(contract())
            pos = len(self.BC)
            self.BC.append( (MessageTag.DEFINED_CONTRACT, contract, contract_id, pos) )
            self.generate_outputs(pos)
        self.write('f2a', (MessageTag.OK,))
        
    def generate_outputs(self, pos):
        for party in self.parties:
            self.eventually(self._generate_outputs, [pos, party], (MessageTag.GEN_OUTPUTS, pos, (self.sid, party)))
            
    def _generate_outputs(self, pos, party):
        if pos <= self.last[party]: return
        
        for i, out in enumerate(self.outputs):
            if not (out[3] > self.last[party] and out[3] <= pos): continue
            self.eventually(self.append, [party, out[0:3]], (MessageTag.OUTPUT, (self.sid, party), i))
                
        msgs = self.BC[self.last[party]+1 : pos+1]
        self.last[party] = pos
        self.messages[party].extend(msgs)
        self.write('f2a', (MessageTag.OK,))
        
    def append(self, party, msg):
        self.messages[party].append(msg)
        self.write('f2a', (MessageTag.OK,))
        
        
    def deliver(self, party):
        self.eventually(self.deliver, [party], (MessageTag.DELIVER, (self.sid, party)))
        if len(self.messages[party]) > 0:
            msgs = self.messages[party].copy()
            self.messages[party].clear()
            self.write('f2p', ((self.sid, party), (MessageTag.OUTPUT, msgs)))
        else:
            self.pump.write("pump")
        