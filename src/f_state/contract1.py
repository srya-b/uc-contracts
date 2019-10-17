class Contract1(object):
    def __init__(self, address, call, out):
        self.address = address
        self.call = call; self.out = out
        self.number = 0

    def init(self, _p1, _p2, _p3, tx):
        self.p1 = _p1
        self.p2 = _p2
        self.p3 = _p3
        self.ps = [_p1, _p2, _p3]

    def mult(self, a, tx):
        self.out(('mult',a), tx['sender'])

def U1(state, inputs, aux_in, rnd):
    if state == None: state=0
    print('INPUTS', inputs)

    add = 0
    sub = 0
    
    for inp in inputs:
        if inp == 'add': add += 1
        elif inp == 'sub': sub += 1

    if add > sub:
        new_state = state+1
    elif sub > add:
        new_state = state-1
    else:
        new_state = state

    if aux_in:
        new_state = state
        print('\t\tGot some aux in', aux_in)
        for i in aux_in:
            print('i', i)
            x = i[0]
            new_state = new_state*x
    aux_out = None
    return (new_state, aux_out)


