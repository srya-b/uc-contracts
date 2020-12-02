from uc.itm import UCWrappedFunctionality, ITM
from uc.utils import wait_for, waits
import gevent
import logging

class F_Pay(UCWrappedFunctionality):
    def __init__(self, k, buts, crupt, sid, pid, channels, pump, poly, importargs):
        self.ssid = sid[0]
        self.P_s = sid[1]
        self.P_r = sid[2]
        self.b_s = sid[3]
        self.b_r = sid[4]
        self.delta = sid[5]
        self.r = 3
        UCWrappedFunctionality.__init__(self, k, buts, crupt, sid, pid, channels, poly, pump, importargs)

        self.flag = "OPEN"

    def process_pay(self, v):
        if self.flag == "OPEN" and self.b_s >= v:
            self.b_s -= v
            self.b_r += v
            self.write('f2p', ((self.sid, self.P_r), ('pay', v)))
        else:
            self.pump.write('')

    def pay(self, v):
        self.leak( ("pay", v), 0 )
        self.write_and_wait_expect(
            ch='f2w', msg=('schedule', 'process_pay', (v,), 1),
            read='w2f', expect=('OK',)
        )
        self.write( 'f2p', ((self.sid, self.P_s), 'OK') )

    def send_to(self, to, msg, imp):
        self.write('f2p', ((self.sid, to), msg), imp)

    def process_close(self):
        if self.flag == "OPEN":
            self.flag = "CLOSE"
            msg = ('close', self.b_s, self.b_r)
            self.write_and_wait_expect(
                ch='f2w', msg=('schedule', 'send_to', (self.P_s, msg, 0), 1),
                read='w2f', expect=('OK',)
            )
            self.write_and_wait_expect(
                ch='f2w', msg=('schedule', 'send_to', (self.P_r, msg, 0), 1),
                read='w2f', expect=('OK',)
            )
        self.pump.write('')

    def close(self, sender):
        if sender == self.P_r or self.is_honest(self.sid, self.P_s):
            self.write_and_wait_expect(
                ch='f2w', msg=('schedule', 'process_close', (), self.delta),
                read='w2f', expect=('OK',)
            )
            self.write( 'f2p', ((self.sid, sender), 'OK') )
        else:
            self.write_and_wait_expect(
                ch='f2w',  msg=('schedule', 'process_close', (), self.r * self.delta),
                read='w2f', expect=('OK',)
            )
            self.write('f2p', ((self.sid, self.P_s), 'OK') )


    def party_msg(self, d):
        msg = d.msg
        imp = d.imp
        (_sid, sender), msg = msg
        
        if sender != self.P_s and sender != self.P_r: self.pump.write('')
        if msg[0] == 'pay' and sender == self.P_s:
            _, v = msg
            self.pay(v)
        elif msg[0] == 'close':
            self.close( sender )
        elif msg[0] == 'balance':
            if sender == self.P_s: self.write('f2p', ((_sid, sender), ('balance',self.b_s)))
            else: self.write('f2p', ((_sid, sender), ('balance',self.b_r)))
        else:
            self.pump.write('')


    def wrapper_msg(self, d):
        msg = d.msg
        imp = d.imp

        if msg[0] == 'exec':
            _, name, args = msg
            f = getattr(self, name)
            f(*args)
        else:
            self.pump.write('')



from uc.execuc import createWrappedUC
from contract_pay import Contract_Pay_and_bcast_and_channel
from uc.itm import wrappedProtocolWrapper
from uc.syn_ours import Syn_FWrapper
from uc.adversary import DummyWrappedAdversary

def payment_simulator(prot):
    def f(k, bits, crupt, sid, pid, channels, pump, poly, importargs):
        return Payment_Simulator(k, bits, crupt, sid, pid, channels, pump, prot, poly, importargs)
    return f

class Payment_Simulator(ITM):
    '''
    k: security param
    bits: random bits
    crupt: currupted parties
    sid: session id
    pid: process id
    channels: channels communicating with each other ITMs
    pump: write-back to environment
    prot: protocol that is run internally in the simulator
    poly: import
    importargs: import arguments
    '''
    def __init__(self, k, bits, crupt, sid, pid, channels, pump, prot, poly, importargs):
        self.crupt = crupt
        self.prot = prot
        self.ssid = sid[0]
        self.P_s = sid[1]
        self.P_r = sid[2]
        self.b_s = sid[3]
        self.b_r = sid[4]
        self.delta = sid[5]

        # Maintain a copy of the ideal world wrapper queue
        self.ideal_queue = {}
        self.ideal_delay = 0
        # Maintain a list of leaks that should be pulled back to environment
        self.sim_leaks = []
        # Maintain a queue to see which (rnd, idx) should be exec
        # This queue is updated whenever get_leak from wrapper
        self.run_queue = {}

        # internal state for the simulated world
        self.nonce = 0
        self.state = (self.b_s, self.b_r, self.nonce)
        self.flag = 'OPEN'
        self.first_close = True
        self.states = [] # (nonce) => {nonce, balances}
        self.sigs = [] # (nonce) => [None] * self.n

        self.log = logging.getLogger("\033[1mPayment_Simulator\033[0m")

        '''
        Outside handlers in the ideal world
        -----------------------------------
        Z (environment):   environment in the ideal world
        P (dummy parties): controlled by Z, so they are dummy
        W (wrapper):       wrapper in the ideal world
        F (functionality): ideal functionality
        '''
        handlers = {
            channels['p2a']: self.party_msg,
            channels['z2a']: self.env_msg,
            channels['w2a']: self.wrapper_msg,
            channels['f2a']: self.func_msg,
        }

        ITM.__init__(self, k, bits, sid, pid, channels, handlers, poly, pump, importargs)

        # Spawn internal real world (local to the simulator)
        self.sim_channels, static, _pump = createWrappedUC(
            k,
            [('F_contract', Contract_Pay_and_bcast_and_channel)],
            wrappedProtocolWrapper(prot), # internal simulated protocol
            Syn_FWrapper,
            DummyWrappedAdversary,
            None
        )

        # Forward the same 'sid' to the simulation
        # TODO forward crupt parties as well
        # TODO possibly wait to do the `static.write` below until execuc.py
        #   tells us who the crupted parties are
        self.sim_sid = self.sid
        self.sim_pump = _pump
        static.write(
            (('sid', self.sim_sid), ('crupt', *[x for x in self.crupt]))
        )

        self.handlers.update({
            self.sim_channels['p2z']: self.sim_party_msg,
            self.sim_channels['a2z']: self.sim_adv_msg,
            self.sim_channels['f2z']: self.sim_func_msg,
            self.sim_channels['w2z']: self.sim_wrapper_msg,
        })

    '''
    On each activation should be called:
        Grab leaks from the ideal world wrapper and
        react to any schedule messages by adding to internal delay
        and talks to simulation if dealer input is seen.
    '''
    def get_ideal_wrapper_leaks(self):
        # grab leaks from the ideal world wrapper
        self.channels['a2w'].write( ('get-leaks',) )
        m = wait_for( self.channels['w2a'] )
        leaks = m.msg

        n = 0
        while leaks:
            leak = leaks.pop(0)
            print('get_ideal_wrapper_leaks:: leaks: {}'.format(leaks))
            print('get_ideal_wrapper_leaks:: current leak: {}'.format(leak))
            sender,msg,imp = leak
            # self.tick(1) => no tick now
            if msg[0] == 'pay':
                # update idealqueue & increase idealdelay by 1
                self.update_queue(leaks, msg, 1)

                v = msg[1]
                if v <= self.b_s:
                    # update nonce & state (probably optional)
                    self.nonce += 1
                    self.b_s -= v
                    self.b_r += v
                    state = (self.b_s, self.b_r, self.nonce)

                self.log.debug('\033[94m Simulation begins: pay\033[0m')
                m = self.sim_write_and_wait(
                    'z2p',
                    ((self.sim_sid,self.P_s),msg),
                    imp,
                    'a2z', 'p2z'
                )
                assert m.msg[1] == 'OK', str(m.msg)
                self.log.debug('\033[94m Simulation ends: pay\033[0m')

            elif msg[0] == 'close':
                # update idealqueue & increase idealdelay by 2
                self.update_queue(leaks, msg, 2)

                self.log.debug('\033[94m Simulation begins: pay\033[0m')
                m = self.sim_write_and_wait(
                    'z2p',
                    ((self.sim_sid, sender), msg),
                    imp,
                    'a2z', 'p2z'
                )
                assert m.msg[1] == 'OK', str(m.msg)
                self.log.debug('\033[94m Simulation ends: pay\033[0m')

            elif msg[0] == 'schedule':
                # some new codeblocks scheduled in simulated wrapper
                self.update_queue(None, msg, 1)

            else: raise Exception("new kind of leak " + str(msg))

        self.sim_get_leaks()

    '''
    update ideal_queue & run_queue
    '''
    def update_queue(self, leaks, msg, n):
        self.ideal_delay += n
        if leaks == None:
            scheduled_block = msg
            command, rnd, idx, f = scheduled_block
            assert command == 'schedule'
            if rnd not in self.ideal_queue:
                self.ideal_queue[rnd] = []
            self.ideal_queue[rnd].append(msg)
            if msg not in self.run_queue:
                self.run_queue[msg] = []
            self.run_queue[msg].append((rnd, idx))
        else:
            for _ in range(n):
                leak = leaks.pop(0)
                sender, scheduled_block, imp = leak
                print('update_queue:: leak: {}'.format(leak))
                command, rnd, idx, f = scheduled_block
                assert command == 'schedule'
                if rnd not in self.ideal_queue:
                    self.ideal_queue[rnd] = []
                self.ideal_queue[rnd].append(msg)
                if msg not in self.run_queue:
                    self.run_queue[msg] = []
                self.run_queue[msg].append((rnd, idx))
                # run_queue: {'codeblock': [(rnd, idx), (rnd, idx)]}
                # mapping of codeblock to list of (rnd, idx)
                # should maintiain the index, exec first on if there's more than one

    '''
    Entrypoints:
    - wrapper_poll: wrapper delivers "poll" message to the simulator
    - env_get_leaks: environment asks the adverasry for latest leaks
    - env_delay: environment tells the adversary to add delay to the codeblock
    - env_exec: environment tells the adversary to execute a code block
    '''
    def wrapper_poll(self):
        # The ideal wrapper decreased its delay, so we do the same
        print('wrapper_poll:: ideal_delay: {}'.format(self.ideal_delay))
        self.ideal_delay -= 1
        if self.ideal_delay == 0:
            self.write_and_wait_expect(
                ch='a2w', msg=('delay', 1),
                read='w2a', expect=('OK',)
            )
            self.ideal_delay += 1


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
            #self.write('a2z', ('poll',))

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

    def env_delay(self, d, imp):
        # first send this to the emulated wrapper
        self.sim_channels['z2a'].write( ('A2W', ('delay', d), 0))
        assert waits(self.sim_channels['a2z']).msg[1] == 'OK'

        # now send it to the ideal world wrapper
        self.write( 'a2w', ('delay',d), imp)
        assert waits(self.pump, self.channels['w2a']).msg == 'OK'
        # update our copy of the ideal delay
        self.ideal_delay += d

        #self.pump.write("dump")
        self.write('a2z', ('W2A', 'OK'))

    '''
    Env exec:
        Pass exec to the simulated wrapper and check for the outcome of that 
        execute with sim_get_leaks. Handle the output the same as above function
    '''
    def env_exec(self, rnd, idx):
        # pass the exec onto the internel wrapper and check for output by some party
        # self.tick(1) => TODO: no tick now
        self.sim_write_and_wait(
            'z2a',
            ('A2W', ('exec', rnd, idx), 0),
            0, #imp
            'a2z', 'p2z', self.sim_pump
        )
        self.sim_get_leaks()
        if r == self.sim_channels['p2z']:
            print('env_exec::p2z output')
            self.sim_party_output(m)
        elif r == self.sim_channels['a2z']:
            print('env_exec::a2z output')
            self.write( 'a2z', m.msg )
        else:
            self.pump.write("dump")


    '''
    Sim related functions
    '''
    def sim_write_and_wait(self, ch, msg, imp, *waiters):
        self.sim_channels[ch].write( msg, imp )
        return waits(self.sim_pump, *[self.sim_channels[w] for w in waiters])

    def sim_poll(self):
        # simulate the 'poll' call
        # self.tick(1) -> TODO: no tick now
        self.log.debug('\t\t\033[94m wrapper_poll Simulation beginning\033[0m')
        self.sim_channels['z2w'].write( ('poll',), 1)
        r = gevent.wait(objects=[self.sim_pump, self.sim_channels['a2z'], self.sim_channels['p2z']], count=1)[0]
        # here we use gevent.wait instead of waits is that we need to know not only the message but the corresponding internal channel
        m = r.read()
        r.reset()
        return r,m

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
        self.log.debug('sim_get_leaks asking for leaks from internal wrapper')
        # self.tick(1) => TODO
        leaks = self.sim_write_and_wait(
            'z2a',
            ('A2W', ('get-leaks',), 0),
            0,
            'a2z'
        )
        self.log.debug('\n\t sim_get_leaks = {} \n'.format(leaks))

        # TODO added a tag
        _,leaks = leaks.msg
        n = 0
        if len(leaks):
            # check and count new "schedules" in simulated wrapper
            for x in leaks:
                _from,msg,imp = x
                if msg[0] == 'schedule':
                    n += 1

        # self.tick(1) => TODO
        # add delay from new "schedules" in simulated wrapper to ideal-world wrapper
        self.log.debug('Add n={} delay to ideal world wrapper'.format(n))
        # TODO: check if we really need to increament wrapper delay by n
        self.ideal_delay += n
        self.write('a2w', ('delay',n), n)
        m = waits(self.pump, self.channels['w2a']);
        assert m.msg == "OK", str(m.msg)
        self.sim_leaks.extend(leaks)

    def sim_party_output(self, m):
        # If we got output from the party, it outputed a msg to
        # tell the ideal wrapper to execute the corresponding codeblock
        fro,msg = m.msg
        _sid,_pid = fro
        self.log.debug('\033[91m sim_party_output:: pid={}, msg={}\033[0m'.format(_pid,msg))

        if self.is_dishonest(_sid,_pid):
            # self.tick(1) => no tick now
            # forward this output to the environment
            self.write('a2z', ('P2A', msg) )
            # don't do anything else since corrupt output in the ideal world doesn't get delivered
            return

        elif msg[0] == 'pay' and fro == self.P_r: # receiver receives 'pay'
            if self.ishonest(_sid, self.P_s):
                rnd, idx = get_rnd_idx_and_update(msg)
                self.write_and_wait_expect(
                    ch='a2w', msg=(('exec', rnd, idx), 1),
                    read='w2a', expect=('OK',)
                )
            else:
                # TODO: when P_s is corrupt
                pass

        elif msg[0] == 'close':
            if self.first_close:
                self.first_close = False
                rnd, idx = get_rnd_idx_and_update(msg)
                if rnd != None and idx != None:
                    self.write_and_wait_expect(
                        ch='a2w', msg=(('exec', rnd, idx), 1),
                        read='w2a', expect=('OK',)
                    )
                else: # implies a corrupt party => Q: why?
                    pass
            else:
                rnd, idx = get_rnd_idx_and_update(msg)
                self.write_and_wait_expect(
                    ch='a2w', msg=(('exec', rnd, idx), 1),
                    read='w2a', expect=('OK',)
                )

    '''
    search corresponding (rnd, idx) based on the message `m` in `ideal_queue`,
    and at the same time updating the mapping `run_queue`
    '''
    def get_rnd_idx_and_update(self, m):
        # get (rnd, idx) from the first matched msg `m`
        try:
            rnd, idx = self.run_queue[m].pop(0)
        except:
            print('get_rnd_idx_and_update:: no such msg exists')
            return None, None

        # update `ideal_queue`
        del(self.ideal_queue[rnd][idx])

        # update `run_queue` mapping
        # run_queue = {
        #     'msg_a': [(rnd1, idx1), (rnd2, idx2), ...],
        #     'msg_b': [(rnd1, idx1), (rnd2, idx2), ...],
        #     ...
        # }
        for key, values in run_queue.items():
            if len(values) == 0: # no (rnd, idx) for a specific msg
                del(run_queue[key])
            for index, pair in enumarate(values):
                _rnd, _idx = pair
                if _rnd == rnd:
                    run_queue[key][index] = (_rnd, _idx-1) # due to .pop(0)

        return rnd, idx

    '''
    Handlers
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
                self.channels['a2w'].write(msg, imp)
        else:
            self.pump.write("dump")

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

    ''' Forward crupt party output to the environment '''
    def party_msg(self, d):
        msg = d.msg
        imp = d.imp
        #self.channels['a2z'].write( msg, imp)
        self.pump.write('dump')

    ''' Same reason as below '''
    def sim_party_msg(self, d):
        self.pump.write("dump")

    ''' Simulated adversary should never write to the simulator on it's own.
        Simulator will activate simulation and wait for the adversary manually.
    '''
    def sim_adv_msg(self, d):
        self.write( 'a2z', d.msg )

    ''' Functionality writing to the environment. Should't happen '''
    def sim_func_msg(self, d):
        self.pump.write("dump")

    ''' The simulated wrapper writing to the enviroment. Shouldn't happen '''
    def sim_wrapper_msg(self, d):
        self.pump.write("dump")

    '''
    Helper functions
    '''
    def is_dishonest(self, sid, pid):
        return (sid, pid) in self.crupt

    def is_honest(self, sid, pid):
        return not self.is_dishonest(sid, pid)
