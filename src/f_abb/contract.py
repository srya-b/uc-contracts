from collections import defaultdict

class Contract:
    def __init__(self):
        self.public_vars = defaultdict(int)
        self.secret_vars = defaultdict(int)
    def set_var(self, var, val, party = False):
        Exception("need to define behavior for setting variables")
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