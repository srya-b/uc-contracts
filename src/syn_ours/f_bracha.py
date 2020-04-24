import dump
from itm import UCWrappedFunctionality, ITM
from utils import wait_for, waits
from numpy.polynomial.polynomial import Polynomial
from comm import ishonest, isdishonest
import gevent
import logging

log = logging.getLogger(__name__)

class Syn_Bracha_Functionality(UCWrappedFunctionality):
    def __init__(self, sid, pid, channels, pump, poly):
        self.ssid = sid[0]
        self.parties = sid[1]
        self.n = len(self.parties)
        self.pump = pump
        self.round_upper_bound = 5
        self.delta = sid[2] * self.round_upper_bound
        UCWrappedFunctionality.__init__(self, sid, pid, channels, poly)

    def send_output(self, to, msg):
        self.f2p.write( (to, msg) )

    '''Dealer, assumed to be pid=1 gives some input and invokes
    the synchronous wrapper around it to deliver the output to all
    of the parties in O(1) time.'''
    def party_input(self, pid, inp):
        if pid == 1:
            for p in self.parties:
                self.f2w.write( ('schedule', self.send_output, (p, inp), self.delta), 0)
                m = wait_for(self.w2f).msg
                assert m == ('OK',)
            n = len(self.parties)
            self.leak( ('input', pid, inp), 0)
        self.write('f2p', 'OK')


    def party_msg(self, d):
        log.debug('Party msg in bracha {}'.format( d))
        msg = d.msg
        imp = d.imp
        sender,msg = msg
        sid,pid = sender
        if msg[0] == 'input':
            self.party_input(pid, msg[1])
        elif msg[0] == 'output':
            self.party_output(pid)
        else: self.pump.write("dump")#dump.dump()

    def wrapper_msg(self, msg):
        self.pump.write("dump")
    def adv_msg(self, msg):
        self.pump.write("dump")
    def env_msg(self, msg):
        self.pump.write("dump")

from itm import ProtocolWrapper
from execuc import createWrappedUC
from syn_ours import Syn_Channel, Syn_Bracha_Protocol
class RBC_Simulator(ITM):
    def __init__(self, sid, pid, channels, pump, poly):
        self.ssid = sid[0]
        self.parties = sid[1]
        self.delta = sid[2]
        self.pump = pump

        # Maintain a copy of the ideal world wrapper queue
        self.internal_run_queue = {}
        self.internal_delay = 0
        # Track idx in queue for each party's output
        self.pid_to_queue = {}
        # whether input was provided to the functionality
        self.dealer_input = False
        self.total_extra_delay_added = 0
        self.log = logging.getLogger("RBC_Simulator")
    
        # Spawn UC experiment of real world (local to the simulator)
        self.sim_channels,static,_pump = createWrappedUC([('F_chan',Syn_Channel)], ProtocolWrapper, Syn_FWrapper, Syn_Bracha_Protocol, DummyWrappedAdversary, poly)

        # Forward the same 'sid' to the simulation 
        # TODO forward crupt parties as well
        # TODO so far the comm.py enforces cruption in the simulation as well
        # TODO possibly wait to do the `static.write` below until execuc.py
        #   tells us who the crupted parties are
        self.sim_sid = (sid[0], sid[1], sid[2])
        self.sim_pump = _pump
        static.write( (('sid', self.sim_sid), ('crupt',)) )
        
        handlers = {
            channels['p2a']: self.party_msg,
            channels['z2a']: self.env_msg,
            channels['w2a']: self.wrapper_msg,
            channels['f2a']: self.func_msg,
            self.sim_channels['p2z']: self.sim_party_msg,
            self.sim_channels['a2z']: self.sim_adv_msg,
            self.sim_channels['f2z']: self.sim_func_msg,
            self.sim_channels['w2z']: self.sim_wrapper_msg,
        }

        ITM.__init__(self, sid, pid, channels, handlers, poly)
    
    # TODO get this the hell out of here
    def poly(self):
        return Polynomial([1, 1, 1, 1, 1])

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
        self.channels['a2z'].write( msg, imp)

    def sim_write_and_wait(self, ch, msg, imp, *waiters):
        self.sim_channels[ch].write( msg, imp )        
        return waits(self.sim_pump, *[self.sim_channels[w] for w in waiters])
 

    def get_ideal_wrapper_leaks(self):
        # grab leaks from the ideal world wrapper
        self.channels['a2w'].write( ('get-leaks',) )
        m = wait_for( self.channels['w2a'] )
        msg = m.msg

        n = 0
        for leak in msg:
            sender,msg,imp = leak
            if sender == (self.sid, 'F_bracha'):
                if msg[0] == 'input':               
                    self.dealer_input = True
                    # F_bracha leaks the dealer input, simulated it
                    n = len(self.parties)
                    self.log.debug('\033[94m Simulation beginning\033[0m')
                    m = self.sim_write_and_wait('z2p', ((self.sim_sid,1),('input',msg[2])), imp, 'a2z')
                    assert m.msg == 'dump'
                    self.log.debug('\033[94m Simulation ending\033[0m')
                elif msg[0] == 'schedule':  
                    # some new codeblocks scheduled in simulated wrapper
                    self.add_new_schedule(msg)
                else: raise Exception("new kind of leak " + str(msg))

        # Check simulated wrapper for any new stuff from the 'for' loop
        leaks = self.sim_get_leaks()
        return leaks

    ''' 
        Environment asking for leaks from the wrapper. Give it back
        leaks from the simulated world.
    '''
    def env_get_leaks(self):
        leaks = self.get_ideal_wrapper_leaks()
        ## grab leaks from the ideal world wrapper
        #self.channels['a2w'].write( ('get-leaks',) )
        #m = wait_for( self.channels['w2a'] )
        #msg = m.msg

        #n = 0
        #for leak in msg:
        #    sender,msg,imp = leak
        #    if sender == (self.sid, 'F_bracha'):
        #        if msg[0] == 'input':               
        #            self.dealer_input = True
        #            # F_bracha leaks the dealer input, simulated it
        #            n = len(self.parties)
        #            self.log.debug('\033[94m Simulation beginning\033[0m')
        #            m = self.sim_write_and_wait('z2p', ((self.sim_sid,1),('input',msg[2])), imp, 'a2z')
        #            assert m.msg == 'dump'
        #            self.log.debug('\033[94m Simulation ending\033[0m')
        #        elif msg[0] == 'schedule':  
        #            # some new codeblocks scheduled in simulated wrapper
        #            self.add_new_schedule(msg)
        #        else: raise Exception("new kind of leak " + str(msg))

        ## Check simulated wrapper for any new stuff from the 'for' loop
        #leaks = self.sim_get_leaks()

        # send emulated leaks to Z. Go on, fool the ol' bastard ;)
        self.write('a2z', leaks.msg, leaks.imp)

    '''New "schedule" in ideal wrapper, add to local copy of it'''
    def add_new_schedule(self, leak):
        _,rnd,idx,fname = leak
        if rnd not in self.internal_run_queue:
            self.internal_run_queue[rnd] = []
        # Add ideal world codeblocks to our copy of the wrapper
        self.internal_run_queue[rnd].insert(idx, leak)
        self.pid_to_queue[len(self.internal_run_queue[rnd])] = (rnd, idx)
        # TODO do we also give delay to the simulated wrapper?
        self.internal_delay += 1

    '''Check simulated wrapper for new "schedules", add to the delay in the ideal wrapper'''
    def sim_get_leaks(self):
        # Ask for leaks from the simulated wrapper
        self.log.debug('sin_get_leaks asking for leaks')
        leaks = self.sim_write_and_wait('z2a', ('A2W', ('get-leaks',)), 0, 'a2z')
        n = 0
        
        self.log.debug('\n\t leaks = {} \n'.format(leaks))

        if len(leaks.msg):
            # check and count new "schedules" in in simulated wrapper
            for x in leaks.msg:
                fro,s,i = x
                if s[0] == 'schedule': n += 1
    
        # add delay from new "schedules" in simulated wrapper to ideal-world wrapper
        self.log.debug('Add n={} delay to ideal world wrapper'.format(n))
        self.internal_delay += n
        # the ideal delay will eventually reach 0 and execute
        if self.internal_delay == n:
            # Add one delay to prevent (above) if ideal and simulated are equal
            self.internal_delay += 1
            self.total_extra_delay_added += 1
            self.log.debug('total_extra_delay_added: {}'.format(self.total_extra_delay_added))
            self.log.debug("the delays are the same")
            self.write('a2w', ('delay', n+1))
        else:
            # else just add the number of new "schedules" in simulated wrapper
            self.write('a2w', ('delay', n))
        m = waits(self.pump, self.channels['w2a']); assert m.msg == "OK", str(m.msg)

        return leaks

    def env_exec(self, rnd, idx):
        # pass the exec onto the internel wrapper and check for output by some party
        self.sim_channels['z2a'].write( ('A2W', ('exec', rnd, idx)) )
        m = waits(self.sim_pump, self.sim_channels['a2z'], self.sim_channels['p2z'])
        if m:
            # forward any output to the environment
            self.write( 'a2z', m )
        else:
            self.pump.write("dump")

    def env_delay(self, d):
        # first send this to the emulated wrapper
        self.sim_channels['z2a'].write( ('A2W', ('delay', d)) )
        assert waits(self.sim_pump, self.sim_channels['a2z']).msg == 'OK'

        # now send it to the ideal world wrapper
        self.write( 'a2w', ('delay',d) )
        assert waits(self.pump, self.channels['w2a']).msg == 'OK'
        # update our copy of the ideal delay
        self.internal_delay += d

        self.pump.write("dump")


    ''' 
        Messages from the Environment
    '''
    def env_msg(self, d):
        msg = d.msg
        imp = d.imp
        if msg[0] == 'A2F':
            t,msg = msg
            self.channels['a2f'].write( msg, imp )
        elif msg[0] == 'A2P':
            _,(to,m) = msg
            # Only crupt parties can be written to by the adversary
            if ishonest(*to):
                raise Exception("Environment send message to A for honest party")
            else:
                print('msg', msg)
                self.sim_channels['z2a'].write( msg , imp )
        elif msg[0] == 'A2W':
            t,msg = msg
            if msg[0] == 'get-leaks':
                self.env_get_leaks()
            elif msg[0] == 'exec':
                self.env_exec(self, r, idx)
            elif msg[0] == 'delay':
                self.env_delay(msg[1])
            else:
                self.channels['a2w'].write( msg, imp )
        else:
            self.pump.write("dump")

    def wrapper_poll(self):
        # The ideal wrapper decreased its delay, so we do the same
        self.internal_delay -= 1
         
        # simulate the 'poll' call
        self.log.debug('\t\t\033[94m wrapper_poll Simulation beginning\033[0m')
        self.sim_channels['z2w'].write( ('poll',), 0)
        r = gevent.wait(objects=[self.sim_pump, self.sim_channels['a2z'], self.sim_channels['p2z']], count=1)[0]
        m = r.read()
        r.reset()
        self.sim_get_leaks()
        self.log.debug('\t\t\033[94m poll Simulation finished\033[0m')
        if r == self.sim_channels['p2z']:
            # If we got output from the party, it outputed a committed value (or bot)
            # tell the ideal wrapper to execute the corresponding codeblock
            fro,msg = m.msg
            _sid,_pid = fro
            self.log.debug('\033[91m Got some output from pid={}, msg={}\033[0m'.format(_pid,msg))

            if not self.dealer_input:
                # If output and not dealer input, dealer is crupt. Call input on functonality
                assert isdishonest(self.sid,1)
                self.sim_channels['a2p'].write( ('P2F', ((self.sid,1), ('input',msg))) )
                waits(self.pump)

                # Now get leaks, and populate self.pid_to_queue
                leaks = self.get_ideal_wrapper_leaks()

            # If dealer gave input to the functionality 
            rnd,idx = self.pid_to_queue[_pid]
            self.internal_run_queue[rnd].pop(idx)
            
            for p in self.pid_to_queue:
                if p > _pid:
                    r,i = self.pid_to_queue[p]
                    self.pid_to_queue[p] = (r, i-1)
            self.write('a2w', ('exec', rnd, idx))
            return
        elif r == self.sim_channels['p2a']:
            # Forward any crupt party output to the environment
            self.write( 'a2z', m.msg )
        else:
            # Something was executed from the wrapper in the simulation, we already
            # got the leaks above
            self.pump.write( 'dump' )

    def wrapper_msg(self, d):
        msg = d.msg
        imp = d.imp

        if msg[0] == 'poll':
            self.wrapper_poll()
        else:
            self.channels['a2z'].write( msg, imp )

    def func_msg(self, d):
        msg = d.msg
        imp = d.imp
        self.channels['a2z'].write( msg, imp )



from itm import WrappedPartyWrapper, PartyWrapper
from adversary import DummyWrappedAdversary
from syn_ours import Syn_FWrapper
from execuc import execWrappedUC
def env1(static, z2p, z2f, z2a, z2w, a2z, p2z, f2z, w2z, pump):
    n = 3
    sid = ('one', (1,2,3), 3)
    static.write( ('sid', sid) )

    z2p.write( ((sid,1), ('input',1)), n*(4*n + 1) )
    waits(pump, a2z)#wait_for(a2z)

    z2a.write( ('A2W', ('get-leaks',)) )
    m = waits(a2z, pump)#wait_for(a2z)

#    z2w.write( ('poll',) )
#    m = wait_for(a2z).msg; assert m == ('poll',), str(m)
#    z2w.write( ('poll',) )
#    wait_for(a2z)
#    z2w.write( ('poll',) )
#    wait_for(a2z)
#
#    z2a.write( ('A2W', ('callme', 3)) )
#    m = wait_for(a2z).msg; assert m == ('OK',)
#    z2w.write( ('poll',) )
#    m = wait_for(a2z).msg; assert m == ('shoutout',)
#
#    z2a.write( ('A2W', ('exec', 6, 1)) ) 
#    m = wait_for(p2z).msg
#    assert m[1] == 1, str(m)


if __name__=='__main__':
    #execWrappedUC(env1, [('F_bracha',Syn_Bracha_Functionality)], PartyWrapper, Syn_FWrapper, 'F_bracha', DummyWrappedAdversary)
    execWrappedUC(env1, [('F_bracha',Syn_Bracha_Functionality)], WrappedPartyWrapper, Syn_FWrapper, 'F_bracha', RBC_Simulator)

