
def send_output(p_i):
    f2p.write( p_i, output )

def adv_decide_output(self):
    if adv_input:
        output = adv_input
    else:
        output = random(inputs)
    for p in parties:
        self.eventually( send_output, p )
        
def party_input(p_i, x):
    inputs.append(x)
    if output:
        self.eventually( send_output, p_i )
    elif all_honest_inputs_given():
        self.eventually( adv_decide_output )

def adv_deliver(b, p_i):
    if b in inputs and inputs[p_i]:
        output = b
        self.eventually( send_output, p_i )
        for p in parties:
            self.eventually( send_output, p )


'''----------------------------------------------------------'''
       

def party_input(p_i, x):
    inputs.append(x)
    if output:
        self.eventually( send_output, p_i )
    else:
    
