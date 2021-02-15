import logging 
import gevent
from uc.utils import wait_for, waits 
from uc.itm import wrappedProtocolWrapper, ITM
from uc.execuc import createWrappedUC
from uc.syn_ours import Syn_Channel, Syn_FWrapper
from uc.adversary import SynWrapperSimulator, DummyWrappedAdversary
from prot_bracha import Syn_Bracha_Protocol

def brachaSimulator(prot):
    def f(k, bits, crupt, sid, pid, channels, pump, poly, importargs):
        return RBC_Simulator(k, bits, crupt, sid, pid, channels, pump, prot, poly, importargs)
    return f

#class RBC_Simulator(ITM):
class RBC_Simulator(SynWrapperSimulator):
    def __init__(self, k, bits, crupt, sid, pid, channels, pump, prot, poly, importargs):
        self.parties = sid[1]
        self.delta = sid[2]

        # Track idx in queue for each party's output
        self.pid_to_queue = {}
        # whether input was provided to the functionality
        self.dealer_input = None
        self.total_extra_delay_added = 0
        self.log = logging.getLogger("\033[1mRBC_Simulator\033[0m")
   
        self.party_output_value = None
        self.expect_output = False
        
        SynWrapperSimulator.__init__(self, k, bits, crupt, sid, pid, channels, pump, prot, poly, importargs)

        # Spawn UC experiment of real world (local to the simulator)
        self.sim_channels,static,_pump = createWrappedUC(k, [('F_chan',Syn_Channel)], wrappedProtocolWrapper(prot), Syn_FWrapper, DummyWrappedAdversary, poly, importargs={'ctx': self.ctx, 'impflag':False})

        # Forward the same 'sid' to the simulation 
        # TODO forward crupt parties as well
        # TODO so far the comm.py enforces cruption in the simulation as well
        # TODO possibly wait to do the `static.write` below until execuc.py
        #   tells us who the crupted parties are
        self.sim_sid = (sid[0]+' simulation', sid[1], sid[2])
        self.sim_pump = _pump
        static.write( (('sid', self.sim_sid), ('crupt', *[x for x in self.crupt])) )
    
        self.handlers.update(
        {
            self.sim_channels['p2z']: self.sim_party_msg,
            self.sim_channels['a2z']: self.sim_adv_msg,
            self.sim_channels['f2z']: self.sim_func_msg,
            self.sim_channels['w2z']: self.sim_wrapper_msg,
        })


        print('\n<><><><>\nSimulator channel w2a: {}\n<><><><>\n'.format(self.channels['w2a'].i))
   


    def is_dishonest(self, sid, pid):
        return (sid,pid) in self.crupt

    def is_honest(self, sid, pid):
        return not self.is_dishonest(sid,pid)

    '''
        Entrypoints:
        - wrapper_poll: wrapper delivers "poll" message to the simulator
        - env_exec: environment tells the adversary to execute a code block
        - env_delay: environment tells the adversary to add delay to the codeblock
        - env_get_leaks: environment asks the adverasry for latest leaks
    '''

    '''
    Wrapper poll:
        Simulator passes "poll" to the simulated wrapper. It calles sim_get_leaks
        to get leaks from the simulation to check for newly scheduled codeblocks
        or output from a party (sim_party_output) or the adversary.
    '''
    def wrapper_poll(self):
        # The ideal wrapper decreased its delay, so we do the same
        self.internal_delay -= 1
        print('\n<><><><>\n[Simulator] wrapper_poll: delay={}\n<><><><>\n'.format(self.internal_delay))
        if self.internal_delay == 0:
            print('adding 1 delay to the wrapper')
            self.DELAY(1)
            self.total_extra_delay_added += 1

        # simulate the 'poll' call
        r,m = self.sim_poll()
        self.sim_get_leaks()

        self.log.debug('\t\t\033[94m poll Simulation finished\033[0m')
        if r == self.sim_channels['p2z']:
            # If we got output from the party, it outputed a committed value (or bot)
            # tell the ideal wrapper to execute the corresponding codeblock
            self.sim_party_output(m)
        elif r == self.sim_channels['a2z']:
            # Forward any crupt party output to the environment
            self.write( 'a2z', m.msg )
        else:
            # Something was executed from the wrapper in the simulation, we already
            # got the leaks above
            self.pump.write( 'dump' )
   
    '''
    Env exec:
        Pass exec to the simulated wrapper and check for the outcome of that 
        execute with sim_get_leaks. Handle the output the same as above function
    '''
    def env_exec(self, rnd, idx):
        # pass the exec onto the internel wrapper and check for output by some party
        self.tick(1)
        r,m = self.EXECUTE(self.sim_channels['z2a'], self.sim_channels['a2z'], self.sim_channels['p2z'], self.sim_pump, rnd, idx)
        self.sim_get_leaks()

        if r == self.sim_channels['p2z']:
            print('p2z output')
            self.sim_party_output(m)
        elif r == self.sim_channels['a2z']:
            print('a2z output')
            self.write( 'a2z', m.msg )
        else:
            self.pump.write("dump")

    def env_delay(self, d, imp):
        # first send this to the emulated wrapper
        self.sim_channels['z2a'].write( ('A2W', ('delay', d), 0))
        assert waits(self.sim_pump, self.sim_channels['a2z']).msg[1] == 'OK'

        # now send it to the ideal world wrapper
        self.DELAY(d)

        # update our copy of the ideal delay
        #self.internal_delay += d

        #self.pump.write("dump")
        self.write('a2z', ('W2A', 'OK'))
    
    ''' 
    env_get_leaks:
        Process leaks from the simulated wrapper. sim_get_leaks will handle how 
        to process the leaks. Return the leaks saved in the leak buffer and empty
        it.
    '''
    def env_get_leaks(self):
        self.sim_get_leaks()
        leaks = list(self.sim_leaks)
        self.sim_leaks = []
        self.write('a2z', ('W2A', leaks), 0)

    '''
        Grab leaks from the ideal world wrapper and
        react to any schedule messages by adding to internal delay
        and talks to simulation if dealer input is seen.
    '''
    def get_ideal_wrapper_leaks(self):
        # grab leaks from the ideal world wrapper
        self.channels['a2w'].write( ('get-leaks',) )
        m = wait_for( self.channels['w2a'] )
        msg = m.msg
        
        n = 0
        pid_idx = None
        for leak in msg:
            self.tick(1)
            sender,msg,imp = leak
            if msg[0] == 'input' and sender == (self.sid, 'F_bracha'):               
                self.dealer_input = msg[2]; assert type(msg[2]) == int
                # F_bracha leaks the dealer input, simulated it
                n = len(self.parties)
                self.log.debug('\033[94m Simulation beginning\033[0m')
                m = self.sim_write_and_wait('z2p', ((self.sim_sid,1),('input',msg[2])), imp, 'a2z', 'p2z')
                assert m.msg[1] == 'OK', str(m.msg)
                self.log.debug('\033[94m Simulation ending\033[0m')
            elif msg[0] == 'schedule':  
                # some new codeblocks scheduled in simulated wrapper
                if sender == (self.sid, 'F_bracha'):
                    if not pid_idx:
                        pid_idx = 1
                    self.add_output_schedule(msg, pid_idx)
                    pid_idx += 1
                else:
                    self.add_new_schedule(msg)
            else: raise Exception("new kind of leak " + str(msg))
        if pid_idx: assert pid_idx-1 == len(self.parties), "n={}, pid_idx={}".format(len(self.parties), pid_idx)

    '''
    Helper functions
    '''

    def add_output_schedule(self, leak, pid_idx):
        self.tick(1)
        _,rnd,idx,fname = leak
        if rnd not in self.internal_run_queue:
            self.internal_run_queue[rnd] = []
        self.internal_run_queue[rnd].insert(idx,leak)
        self.pid_to_queue[pid_idx] = (rnd, idx)
        self.internal_delay += 1


    '''New "schedule" in ideal wrapper, add to local copy of it'''
    def add_new_schedule(self, leak):
        self.tick(1)
        _,rnd,idx,fname = leak
        if rnd not in self.internal_run_queue:
            self.internal_run_queue[rnd] = []
        # Add ideal world codeblocks to our copy of the wrapper
        self.internal_run_queue[rnd].insert(idx, leak)
        #self.pid_to_queue[len(self.internal_run_queue[rnd])] = (rnd, idx)
        # TODO do we also give delay to the simulated wrapper?
        self.internal_delay += 1

    '''
    sim_get_leaks:
        Function will get leaks from the simulated wrapper. If there are 'n' new codeblocks
        scheduled (simulated wrapper delay has increased by 'n'), add the same delay to the
        ideal world wrapper. Since a delay of 'n' requires 'n+1' polls to execute the next 
        codeblock (see wrapper code) eventually the ideal world gets to 0 so add a delay
        of 1 when that happens. Finally store the leaks in the "leak buffer" since we
        consumed them when checking for leaks.
    '''
    def sim_get_leaks(self):
        # Ask for leaks from the simulated wrapper
        self.log.debug('sin_get_leaks asking for leaks')
        self.tick(1)
        leaks = self.sim_write_and_wait('z2a', ('A2W', ('get-leaks',), 0), 0, 'a2z')
        n = 0
        self.log.debug('\n\t leaks = {} \n'.format(leaks))

        # TODO added a tag
        _,leaks = leaks.msg
        if len(leaks):
            # check and count new "schedules" in in simulated wrapper
            for x in leaks:
                fro,s,i = x
                if s[0] == 'schedule': 
                    n += 1
   
        self.tick(1)
        # add delay from new "schedules" in simulated wrapper to ideal-world wrapper
        self.log.debug('Add n={} delay to ideal world wrapper'.format(n))
        #self.internal_delay += n
        #self.DELAY(n)
        self.sim_leaks.extend(leaks)


    ''' 
        Messages from the Environment
    '''
    def env_msg(self, d):
        msg = d.msg
        imp = d.imp
        self.get_ideal_wrapper_leaks()
        if msg[0] == 'A2F':
            t,msg,iprime = msg
            self.channels['a2f'].write( msg, iprime )
        elif msg[0] == 'A2P':
            _,(to,m),iprime = msg
            # Only crupt parties can be written to by the adversary
            if self.is_honest(*to):#ishonest(*to):
                raise Exception("Environment send message to A for honest party")
            else:
                self.sim_channels['z2a'].write( msg , iprime )
        elif msg[0] == 'A2W':
            t,msg,iprime = msg
            if msg[0] == 'get-leaks':
                self.env_get_leaks()
            elif msg[0] == 'exec':
                self.env_exec(msg[1], msg[2])
            elif msg[0] == 'delay':
                self.env_delay(msg[1], imp)
            else:
                self.channels['a2w'].write( msg, imp )
        else:
            self.pump.write("dump")

    def sim_poll(self):
        # simulate the 'poll' call
        self.tick(1)
        self.log.debug('\t\t\033[94m wrapper_poll Simulation beginning\033[0m')
        self.sim_channels['z2w'].write( ('poll',), 0)
        r = gevent.wait(objects=[self.sim_pump, self.sim_channels['a2z'], self.sim_channels['p2z']], count=1)[0]
        m = r.read()
        r.reset()
        return r,m


    def sim_party_output(self, m):
        # If we got output from the party, it outputed a committed value (or bot)
        # tell the ideal wrapper to execute the corresponding codeblock
        fro,msg = m.msg
        _sid,_pid = fro
        self.log.debug('\033[91m Got some output from pid={}, msg={}\033[0m'.format(_pid,msg))

        if self.is_dishonest(_sid,_pid):#isdishonest(_sid,_pid):
            self.tick(1)
            # forward this output to the environment
            self.write('a2z', ('P2A', msg) )
            # don't do anything else since corrupt output in the ideal world doesn't 
            #     get delivered
            return
        elif not self.dealer_input:
            assert len(self.internal_run_queue) == 0
            # If output and not dealer input, dealer is crupt. Call input on functonality
            self.tick(1)
            assert self.is_dishonest(self.sid, 1)#isdishonest(self.sid,1)
            n = len(self.parties)
            print('\n\t sending input to f_bracha \n\t')
            self.write( 'a2p', ((self.sid, 1), ('P2F', ((self.sid, 'F_bracha'), ('input',msg)) )), n*(4*n + 1))
            m = waits(self.pump, self.channels['p2a'])
            print('\n******m\n', m, '\n')
            _fro,_msg = m.msg
            self.dealer_input = msg; assert type(msg) == int, 'msg:{}, fro:{}'.format(msg, fro)
            assert _msg == 'OK', str('fro={}, msg={}'.format(_fro,_msg))
            # Now get leaks, and populate self.pid_to_queue
            #leaks = self.get_ideal_wrapper_leaks()
            self.tick(1)
            self.write( 'a2w', ('get-leaks',))
            m = wait_for(self.channels['w2a'])
            msg = m.msg
            pid_idx = None
            for leak in msg:
                self.tick(1)
                sender,msg,imp = leak
                if sender == (self.sid, 'F_bracha'):
                    if msg[0] == 'schedule':
                        if not pid_idx: pid_idx = 1
                        self.add_output_schedule(msg, pid_idx)
                        pid_idx += 1
            if pid_idx: assert pid_idx-1 == len(self.parties)
        self.expect_output = True

        # If dealer gave input to the functionality 
        rnd,idx = self.pid_to_queue[_pid]
        self.internal_run_queue[rnd].pop(idx)
        
        for p in self.pid_to_queue:
            self.tick(1)
            if p > _pid:
                r,i = self.pid_to_queue[p]
                self.pid_to_queue[p] = (r, i-1)
        self.write('a2w', ('exec', rnd, idx))

    def wrapper_msg(self, d):
        msg = d.msg
        imp = d.imp
        self.get_ideal_wrapper_leaks()
        if msg[0] == 'poll':
            self.wrapper_poll()
        else:
            self.channels['a2z'].write( ('W2A', msg), imp )

    def func_msg(self, d):
        msg = d.msg
        imp = d.imp
        self.get_ideal_wrapper_leaks()
        self.channels['a2z'].write( ('F2A', msg), imp )
    
    ''' Same reason as below '''
    def sim_party_msg(self, d):
        self.pump.write("dump")

    ''' Simulated adversary should never write to the simulator on it's own.
        Simulator will activated simulatio and wait for the adversary manually.
    '''
    def sim_adv_msg(self, d):
        self.write( 'a2z', d.msg )
   
    ''' Functionality writing to the environment. Should't happen '''
    def sim_func_msg(self, d):
        self.pump.write("dump")

    ''' The simulated wrapper writing to the enviroment. Shouldn't happen '''
    def sim_wrapper_msg(self, d):
        self.pump.write("dump")

    ''' Forward crupt party output to the environment '''
    def party_msg(self, d):
        msg = d.msg
        imp = d.imp
        #self.channels['a2z'].write( msg, imp)
        self.pump.write('dump')

    def sim_write_and_wait(self, ch, msg, imp, *waiters):
        self.sim_channels[ch].write( msg, imp )        
        return waits(self.sim_pump, *[self.sim_channels[w] for w in waiters])


