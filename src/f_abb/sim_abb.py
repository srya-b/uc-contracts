from itm import ITM, WrappedProtocolWrapper, WrappedPartyWrapper
from adversary import DummyWrappedAdversary
from prot_online import OnlineMPCProtocol, ContractHandler
from asyncwrapper import AsyncWrapper
from f_atomic import AtomicBroadcastFunctionality
from f_offline import OfflinePhaseFunctionality
from f_async import AsyncBroadcastFunctionality
from f_abb import AsyncABBFunctionality
from prot_online import Functionalities as F
from contract import ExampleContract, TransitionType
from execuc import execWrappedUC, createWrappedUC
from utils import z_get_leaks, waits, MessageTag
from collections import deque, defaultdict
import comm

from honeybadgermpc.polywrapper import PolyWrapper

class Delay:
    """
        Wrapper class for ideal-world delay
        Whenever the delay counter drops below zero, it automatically increments
    """
    def __init__(self, sim_class, w2a, a2w):
        self.sim_class = sim_class
        
        a2w.write((MessageTag.DELAY, 1), 0)
        waits(*[w2a])
        
        self.delay = 1
    def __add__(self, other):
        self.delay += other
    def __sub__(self, other):
        self.delay -= other
        if (self.delay < 1):
            self.sim_class.write_and_wait('a2w', (MessageTag.DELAY, 2 - self.delay), 0, 'w2a')
            self.delay += (2 - self.delay)
    def __iadd__(self, other):
        self.__add__(other)
        return self
    def __isub__(self, other):
        self.__sub__(other)
        return self
        

class ABBSimulator(ITM):
        
    def __init__(self, sid, pid, channels, pump, poly):
        self.ssid, self.parties = sid
        self.pump = pump
        self.poly_ = poly
        self.BC = []
        self.ideal_run_queue = deque()
        
        self.outputs = []
        
        self.sim_channels,static,_pump = createWrappedUC([(F.F_ATOMIC, AtomicBroadcastFunctionality), (F.F_OFFLINE, OfflinePhaseFunctionality), (F.F_ASYNC, AsyncBroadcastFunctionality)], WrappedProtocolWrapper, AsyncWrapper, OnlineMPCProtocol, DummyWrappedAdversary, poly)
        self.sim_sid = (str(self.ssid) + "_s", self.parties)
        self.sim_ssid, self.sim_parties = self.sim_sid
        self.sim_pump = _pump
        
        self.corruptions = []
        for pid in (i for i in range(len(self.parties)) if not comm.ishonest(sid, i)):
            self.corruptions.append(pid)
            
        self.contract_handlers = dict.fromkeys(self.corruptions, defaultdict(lambda: ContractHandler(self)))         
        
        static.write( (('sid', self.sim_sid), ('crupt',*[(self.sim_sid, pid) for pid in self.corruptions])) )        
        waits(self.sim_channels['p2z'], self.sim_channels['a2z'], self.sim_channels['f2z'], self.sim_channels['w2z'], self.sim_pump)
        
        handlers = {
            channels['p2a']: self.party_msg,
            channels['z2a']: self.env_msg,
            channels['w2a']: self.wrapper_msg,
            channels['f2a']: self.func_msg,
            self.sim_channels['p2z']: self.sim_party_msg,
            self.sim_channels['a2z']: self.sim_adv_msg,
            self.sim_channels['f2z']: self.sim_func_msg,
            self.sim_channels['w2z']: self.sim_wrapper_msg,
            self.sim_pump: self.sim_pump_handler
        }
        
        self.ideal_delay = Delay(self, channels['w2a'], channels['a2w'])

        self.polywrapper = PolyWrapper(len(self.parties))
        
        self.outputpoly = {}
        self.corruptoutputs = defaultdict(lambda: set())

        ITM.__init__(self, sid, pid, channels, handlers, poly)

    def sim_pump_handler(self, d):
        """
            Whenever a simulated honest party returns control to Z,
            S should do that as well
        """
        self.pump.write("pump")
        
    def sim_party_msg(self, d):
        """
            This function handles outputs from simulated real-world parties
            The simulator must do two things:
            1. Maintain indistinguishability w.r.t. honest party outputs by
               instructing the ideal functionality to provide outputs
               to the actual dummy honest parties
            2. Maintain indistinguishability w.r.t. adversarial inputs by
               instructing dummy corrupt parties and the ideal functionality
               to include corrupt inputs
        """
        party, outputs = d.msg
        sid, pid = party
        assert sid == self.sim_sid
        tag, outputs = outputs
        outputs = self.replace_sid(outputs, False)
        for output in outputs:
            self.get_leaks()
            if output[0] == MessageTag.DEFINED_VAR or output[0] == MessageTag.DEFINED_CONTRACT:
                pos = output[3]
                assert pos <= len(self.BC)

                if pos == len(self.BC) and output[0] == MessageTag.DEFINED_VAR:
                    atomic = comm.itmmap[sid, F.F_ATOMIC]
                    offline = comm.itmmap[sid, F.F_OFFLINE]

                    contract_id = output[2]
                    dealer = output[1][0]
                    dealer_sid, dealer_pid = dealer
                    msg = (MessageTag.INPUT_VAL, contract_id, dealer)
                    self.BC.append(msg)
                    try:
                        queue_pos = self.ideal_run_queue.index(msg)
                    except:
                        # this means that this is an adversarial input                        
                        dealer_sid, dealer_pid = dealer
                        tx = atomic.BC[pos][0]
                        input_sub_val = tx[1]
                        label = tx[2]
                        val = offline.poly_wrapper.secret(offline.poly_dict[(dealer, label)])
                        input_ = input_sub_val + val
                        out = self.write_and_wait('a2p', (dealer, ((self.sid, 'F_abb'), (MessageTag.INPUT_VAL, input_, contract_id)) ), 0, 'w2a', 'f2a', 'p2a' )
                        self.get_leaks()
                        queue_pos = self.ideal_run_queue.index(msg)
                    del self.ideal_run_queue[queue_pos]
                    self.write_and_wait('a2w', (MessageTag.EXECUTE, queue_pos), 0, 'w2a', 'f2a')
                    
                    for c_pid in self.corruptions:
                        self.c_pid = c_pid
                        tx = atomic.BC[pos][0]
                        input_sub_val = tx[1]
                        label = tx[2]
                        val = offline.poly_wrapper.share(offline.poly_dict[((self.sim_sid, dealer_pid), label)], c_pid)
                        input_share = input_sub_val + val
                        self.contract_handlers[c_pid][contract_id].add_input((dealer[1], input_share))
                        self.c_pid = None
                    
                    self.get_leaks()
                if pos == len(self.BC) and output[0] == MessageTag.DEFINED_CONTRACT:
                    atomic = comm.itmmap[sid, F.F_ATOMIC]
                    contract_class = output[1]
                    msg = (MessageTag.CREATE_CONTRACT, contract_class)
                    self.BC.append(msg)
                    try:
                        queue_pos = self.ideal_run_queue.index(msg)
                    except:
                        dealer = atomic.BC[pos][1]
                        out = self.write_and_wait('a2p', (dealer, ((self.sid, 'F_abb'), (MessageTag.CREATE_CONTRACT, contract_class)) ), 0, 'w2a', 'f2a', 'p2a')
                        self.get_leaks()
                        queue_pos = self.ideal_run_queue.index(msg)
                        
                    for c_pid in self.corruptions:
                        self.c_pid = c_pid
                        contract_id = len([x for x in self.BC if x[0] == MessageTag.CREATE_CONTRACT])-1
                        self.contract_handlers[c_pid][contract_id].set_contract(contract_class(),contract_id)
                        self.c_pid = None
                    
                    del self.ideal_run_queue[queue_pos]
                    self.write_and_wait('a2w', (MessageTag.EXECUTE, queue_pos), 0, 'w2a', 'f2a')
                    self.get_leaks()
                msg = (MessageTag.GEN_OUTPUTS, pos, (self.sid, pid))
                queue_pos = self.ideal_run_queue.index(msg)
                del self.ideal_run_queue[queue_pos]
                self.write_and_wait('a2w', (MessageTag.EXECUTE, queue_pos), 0, 'w2a', 'f2a')
            elif output[0] == MessageTag.OUTPUT:
                var = output[1]
                pos = [idx for idx, msg in enumerate(self.outputs) if msg[0] == MessageTag.OUTPUT and msg[1] == var][0]
                msg = (MessageTag.OUTPUT, (self.sid, pid), pos)
                queue_pos = self.ideal_run_queue.index(msg)
                del self.ideal_run_queue[queue_pos]
                self.write_and_wait('a2w', (MessageTag.EXECUTE, queue_pos), 0, 'w2a', 'f2a')
        self.get_leaks()
        msg = (MessageTag.DELIVER, (self.sid, pid))
        queue_pos = self.ideal_run_queue.index(msg)
        del self.ideal_run_queue[queue_pos]
        self.channels['a2w'].write((MessageTag.EXECUTE, queue_pos))
        
    def sim_func_msg(self, d):
        """
            Function to handle messages from the simulated functionalities
            Functionalities never write to Z, so this is a placeholder
        """
        self.pump.write("pump")

    def sim_wrapper_msg(self, d):
        """
            Function to handle messages from the simulated wrapper
            Wrappers never write to Z, so this is a placeholder
        """
        self.pump.write("pump")
        
    def sim_adv_msg(self, d):
        """ 
            The simulator must forward simulated dummy adv. messages to Z
            Messages with shares of public reconstructions from simulated honest
            parties must be changed to be consistent with views of corrupt parties
            
            The major purpose of this function is to maintain indistinguishability
            based on simulated honest party messages 
        """
        self.get_leaks()
        if len(d.msg) > 1:
            c_party, msg = d.msg
            c_sid, c_pid = c_party
            func, msg = msg
            if func[1] == F.F_ASYNC:
                tag, senderpid, msg = msg
                contract_id = msg[0]
                msg = msg[1]

                if msg[0] != TransitionType.OUT:
                    self.c_pid = c_pid
                    self.contract_handlers[c_pid][contract_id].add_msg(senderpid, msg)
                    self.c_pid = None
                elif (contract_id, msg[1]) in self.outputpoly:
                    share = self.polywrapper.share(self.outputpoly[(contract_id, msg[1])], senderpid)
                    _ = d.msg
                    d.msg = (c_party, (func, (tag, senderpid, (contract_id, (msg[0], msg[1], share)))))
                    #d.msg[1][1][2][1][2] = share
                elif len(self.corruptoutputs[(contract_id, msg[1])]) == len(self.corruptions):
                    secret_idx = [idx for (idx, out) in enumerate(self.outputs) if out[0] == MessageTag.OUTPUT and out[1] == (contract_id, msg[1][1])][0]
                    _ = list(self.corruptoutputs[(contract_id, msg[1])])
                    _.append((self.polywrapper.n, self.outputs[secret_idx][2]))
                    self.outputpoly[(contract_id, msg[1])] = self.polywrapper.random_with_pairs(_)
                    share = self.polywrapper.share(self.outputpoly[(contract_id, msg[1])], senderpid)
                    d.msg = (c_party, (func, (tag, senderpid, (contract_id, (msg[0], msg[1], share)))))
                else:
                    wrapper = comm.wrapmap[self.sim_sid]
                    msgs = [(sender[0][2][1], args[0]) for (sender, (func, args)) in wrapper.runqueue if sender[1] == F.F_ASYNC and sender[0][2][1] in self.corruptions and sender[0][1][1] not in self.corruptions]
                    for (c_pid, msg) in msgs:
                        contract_id = msg[0]
                        msg = msg[1]
                        if msg[0] != TransitionType.OUT:
                            self.c_pid = c_pid
                            self.contract_handlers[c_pid][contract_id].add_msg(senderpid, msg)
                            self.c_pid = None
                    assert len(self.corruptoutputs[(contract_id, msg[1])]) == len(self.corruptions)
                    
                    secret_idx = [idx for (idx, out) in enumerate(self.outputs) if out[0] == MessageTag.OUTPUT and out[1] == (contract_id, msg[1][1])][0]
                    _ = list(self.corruptoutputs[(contract_id, msg[1])])
                    _.append((self.polywrapper.n, self.outputs[secret_idx][2]))
                    self.outputpoly[(contract_id, msg[1])] = self.polywrapper.random_with_pairs(_)
                    share = self.polywrapper.share(self.outputpoly[(contract_id, msg[1])], senderpid)
                    d.msg = (c_party, (func, (tag, senderpid, (contract_id, (msg[0], msg[1], share)))))
                    
        self.channels['a2z'].write(self.replace_sid(d.msg, False), d.imp) # TODO: this means any leaks or any adversarial outputs/messages - need to be routed to environment
        
    def party_msg(self, d):
        """ 
            This means a corrupt party *in the ideal world* has an output.
            We just suppress it.
        """
        self.pump.write("pump")
    
    def env_msg(self, d):
        """
            This handles messages from Z to S
            Usually directly forwards messages to the simulated A
        """
        self.get_leaks()
        msg = d.msg
        imp = d.imp
                
        if msg[0] == 'A2F': 
            _,msg = msg
            self.channels['a2f'].write( msg, imp ) # this shouldn't happen
        elif msg[0] == 'A2P':
            _,(to,m) = msg
            # Only crupt parties can be written to by the adversary
            if comm.ishonest(*to):
                raise Exception
            else:
                self.sim_channels['z2a'].write( self.replace_sid(msg) , imp )
        elif msg[0] == 'A2W':
            _,msg = msg
            if msg[0] == MessageTag.EXECUTE:
                self.execute(msg)
            elif msg[0] == MessageTag.DELAY:
                self.delay(msg)
            elif msg[0] == MessageTag.SEND_LEAKS:
                self.get_leaks()
                out = self.sim_write_and_wait('z2a', ('A2W', (MessageTag.SEND_LEAKS,)), 1, 'a2z')
                self.channels['a2z'].write(self.replace_sid(out.msg, False), out.imp)
            else:
                self.channels['a2w'].write( msg, imp )
        elif msg[0] == 'corrupt':
            self.pump.write("pump") # this is a static adversary, so we ignore it
        else:
            self.pump.write("pump") # do nothing
            
    def replace_sid(self, msg, to_sim = True):
        """
            Replaces the real sid with simulated sid and vice versa
        """
        old, new = (self.ssid, self.sim_ssid) if to_sim else (self.sim_ssid, self.ssid)
        new_msg = []
        for elem in msg:
            if elem == old:
                new_msg.append(new)
            elif type(elem) is tuple:
                new_msg.append(self.replace_sid(elem, to_sim))
            elif type(elem) is list:
                new_msg.append([self.replace_sid(i, to_sim) for i in elem])
            else:
                new_msg.append(elem)

        return tuple(new_msg)
            
    def wrapper_msg(self, d):
        """
            Handles messages from the ideal-world wrapper
            Wrapper either forwards advances or sends ideal-world leaks
        """
        self.get_leaks()
        msg = d.msg
        imp = d.imp
        if msg[0] == MessageTag.ADVANCE:
            self.advance()
        elif msg[0] == MessageTag.SEND_LEAKS:
            self.parse_leaks(msg[1])
        else:
            self.channels['a2z'].write(self.replace_sid(msg, False), imp) # forward to environment, but no clue what it is
    
    def func_msg(self, d):
        """
            Handles messages from the ideal-world functionality
            Not a concern in this protocol
        """
        self.pump.write("pump")
   
    def write_and_wait(self, ch, msg, imp, *waiters):
        """
            Helper function that writes a message to an ideal-world channel
            and automatically waits and forwards any output to the caller
        """
        self.channels[ch].write( self.replace_sid(msg, False), imp )
        return waits(*[self.channels[w] for w in waiters])

    def sim_write_and_wait(self, ch, msg, imp, *waiters):
        """
            Helper function that writes a message to a simulatedd channel
            and automatically waits and forwards any output to the caller
        """
        self.sim_channels[ch].write( self.replace_sid(msg), imp )
        return waits(self.sim_pump, *[self.sim_channels[w] for w in waiters])
        
    def execute(self, msg):
        """
            Helper function that handles "execute" message from Z
            Forwards message to the simulated channel
        """
        self.sim_channels['z2a'].write(self.replace_sid(('A2W', msg)))
        
    def delay(self, msg):
        """
            Helper function that handles "delay" message from Z
            Needs to send to simulated real world 
        """
        self.sim_channels['z2a'].write(('A2W', msg), 0)
        output = waits(self.sim_pump, self.sim_channels['a2z'])
        assert output.msg == (MessageTag.OK,)

        #self.write('a2w', msg, 0)
        #assert waits(self.pump, self.channels['w2a']).msg == (MessageTag.OK,)

        self.channels['a2z'].write(self.replace_sid(output.msg, False))
    
    def advance(self):
        """
            Helper function that handles "advance" message from W
            Message from W means that "advance" should be done in simulated world
        """
        self.ideal_delay -= 1
        self.sim_channels['z2w'].write((MessageTag.ADVANCE,))
        
    def get_leaks(self):
        """
            Helper function that get leaks from ideal world
        """
        out = self.write_and_wait('a2w', (MessageTag.SEND_LEAKS,), 1, 'w2a')
        self.parse_leaks(out.msg[1])
        
    def parse_leaks(self, leaks):
        """
            Function to parse leaks from the ideal world
        """
        for leak in leaks:
            if leak[0] == MessageTag.EXECUTE:
                pass #do nothing, since the simulator should never let this happen 
            elif leak[0] == MessageTag.EVENTUALLY:
                sender, func_name, msg = leak[1]
                self.ideal_delay += 1
                if msg[0] == MessageTag.INPUT_VAL:
                    tag, contract_id, dealer = msg
                    self.ideal_run_queue.append((tag, contract_id, dealer))
                    if comm.ishonest(*dealer):
                        self.sim_write_and_wait('z2p', (dealer, (MessageTag.INPUT_VAL, 0, contract_id)), 0, 'p2z', 'a2z', 'w2z', 'f2z')
                elif msg[0] == MessageTag.CREATE_CONTRACT:
                    tag, contract, dealer = msg
                    self.ideal_run_queue.append((tag, contract))
                    if comm.ishonest(*dealer):
                        self.sim_write_and_wait('z2p', (dealer, (MessageTag.CREATE_CONTRACT, contract)), 0, 'p2z', 'a2z', 'w2z', 'f2z')
                elif msg[0] == MessageTag.GEN_OUTPUTS:
                    self.ideal_run_queue.append(msg) # this is handled when receiving outputs from the emulated real world
                elif msg[0] == MessageTag.OUTPUT:
                    self.ideal_run_queue.append(msg) # this is handled when receiving outputs from the emulated real world
                elif msg[0] == MessageTag.DELIVER:
                    self.ideal_run_queue.append(msg) # this is handled when receiving outputs from the emulated real world
                else:
                    self.ideal_run_queue.append(msg) # append it, but not much you can do
            elif leak[0] == MessageTag.LEAK:
                sender, msg = leak[1]
                if msg[0] == MessageTag.OUTPUT:
                    if len(msg[1]) > len(self.outputs):
                        self.outputs = msg[1]
                    
    def write_to_party(self, party, d):
        """
            Dummy function to use ContractHandler out of the box
            Stores shares of public reconstructions for each corrupt party
        """
        assert self.c_pid is not None
        id, msg = d
        if msg[0] == TransitionType.OUT:
            point = (self.c_pid, msg[2])
            var = (id, msg[1])
            self.corruptoutputs[var].add(point)
    
    def write_to_functionality(self, func, d):
        """
            Dummy function to use ContractHandler out of the box
            Forwards messages to the simulated offline functionality
        """
        assert func == F.F_OFFLINE
        inner_msg = ((self.sim_sid, func), d)
        party_msg = ((self.sim_sid, self.c_pid), ('P2F', inner_msg))
        adv_msg = ('A2P', party_msg)
        out = self.sim_write_and_wait('z2a', adv_msg, 0, 'a2z')
        out.msg = out.msg[1]
        return out
        