from collections import defaultdict
from enum import Enum
            
class TransitionType(Enum):
    ADD = 1
    MULT = 2
    OUT = 3
    
class Contract:
    def __init__(self):
        self.inputs = defaultdict(int)
        self.inner_vars = defaultdict(int)
        self.outputs = list()
    def set_var(self, var, val, party = False):
        Exception("need to define behavior for setting variables")
    def set_output(self, var):
        self.outputs.append(var)
    def get_transition(self):
        '''
        We define three types of transitions for contracts:
        'add':  output should be of form ('add', (coeffs, vars, outvar))
                where coeffs: [a_0, a_1, ..., a_n]
                      vars:   [1, x_1, ..., x_n]
                      outvar: string, representing the name of the variable
                              where a_0 + sum(a_1 * x_n, n) should be stored
        'mult': output should be of form ('mult', (in1, in2, outvar))
                where in1/in2: values of multiplicand and multiplier
                      outvar: string representing the name of the variable
                              where in1*in2 should be stored
        'out':  output should be of form ('out', (varname, val))
                where varname: name of variable being output
                      val: value stored in contract for *varname, whether actual or secret shared
        '''
        Exception("need to define transitions")

class ExampleContract(Contract):
    def __init__(self, n=5):
        self.n = n
        self.t = n // 3
        self.add = list()
        self.mult2 = None
        Contract.__init__(self)
    def set_var(self, var, val, party = False):
        if party and len(self.inputs) < self.t + 1:
            self.inputs[var] = val
            self.add.append(val)
        elif party and self.mult2 is None:
            self.inputs[var] = val
            self.mult2 = val
        else:
            self.inner_vars[var] = val
    def get_transition(self):
        if len(self.inputs) == self.t + 1 and 'mult1' not in self.inner_vars:
            return (TransitionType.ADD, ([1]*(self.t+1), list(self.inputs.values()), 'mult1'))
        if 'mult1' in self.inner_vars and self.mult2 is not None and 'out' not in self.inner_vars:
            return (TransitionType.MULT, (self.inner_vars['mult1'], self.mult2, 'out'))
        if 'out' in self.inner_vars and 'out' not in self.outputs:
            print("DO out")
            return (TransitionType.OUT, ('out', self.inner_vars['out']))