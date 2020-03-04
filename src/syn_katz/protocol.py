import dump
import gevent
from itm import UCProtocol

class ITMSyncProtocol(UCProtocol):
    def __init__(self, sid, pid, channels, handlers):
        #self.channels = channels
        #self.handlers = handlers
        self.sid = sid
        self.ssid = self.sid[0]
        self.parties = self.sid[2]
        self.pid = pid
        self.clock_round = 1
        self.roundok = False
        # n-1 length todo function to ensure that many future activations
        print('sid', self.sid, 'parties', self.parties)
        self.todo = [ (lambda: dump.dump(),()) for p in self.parties if p != self.pid]
        self.startsync = True
        # TODO change the name of this because it's not broadcast specific
        self.outputset = False
        UCProtocol.__init__(self, sid, pid, channels, handlers)

        #print('[{}] Sending start synchronization...'.format(self.pid))
        #self.p2f.write( ((self.sid,'F_clock'),('RoundOK',)) )
        #self.roundok = True

    def sync(self):
        if self.startsync and not self.roundok:
            print('[{}] Sending start synchronization...'.format(self.pid))
            self.p2f.write( ((self.sid,'F_clock'),('RoundOK',)) )
            self.roundok = True

    def wait_for(self, chan):
        r = gevent.wait(objects=[chan],count=1)
        r = r[0]
        fro,msg = r.read()
        chan.reset()
        return fro,msg

    def p2p_handler(self, fro, msg):
        raise Exception("p2p_handler must be implemented by deriving class")

    def fetch(self, fbdsid):
        fro = fbdsid[1]
        self.p2f.write( ((fbdsid, 'F_bd'), ('fetch',)) )
        _fro,_msg = self.wait_for(self.f2p)
        _,msg = _msg
        if msg is None: return
        else: self.p2p_handler(fro, msg)

    def send_message(self, fbdsid, msg):
        _ssid,_fro,_to,_r = fbdsid
        self.p2f.write( ((fbdsid,'F_bd'), msg) )

    def send_in_o1(self, pid, msg):
        fbdsid = (self.ssid, (self.sid,self.pid), (self.sid,pid), self.clock_round)
        self.todo.append( (self.send_message, (fbdsid, ('send', msg))) )
   
    # The way it's goint to work:
    # Regular Party: 
    #     At the start of every round, read all the incoming messages and
    #     load the `todo` queue with the messages that need to be sent to
    #     the other n-1 parties (don'nt need to send to yourself unless
    #     you're the dealer. You also pop off todo and send the first message
    #     in the first activation so that the last activation only does 
    #     RoundOK to F_clock
    # Dealer:
    #     On input from the dealer, the dealer needs to send himself the 
    #     input as well to trigger the sending of ECHO messages. This 
    #     means that all `n` activations must be used for sending the first
    #     VAL messages and leaving no activation for the RoundOK. Therefore
    #     the dealer must do something else to send ECHO messages in the next
    #     round. Perhaps a hardcoded behavior would be the best where the
    #     dealer will check in 1st activation of round2 whether a VAL was
    #     sent. If so initiate the subroutine as if a VAL messages had been
    #     received.
    def check_round_ok(self):
        if self.outputset:
            if len(self.todo) > 0: self.todo.pop(0); dump.dump()
            else:
                self.p2z.write( self.val )
            return

        # If RoundOK has been sent, then wait until we have a new round
        if self.roundok:
            self.p2f.write( ((self.sid,'F_clock'),('RequestRound',)) )
            fro,di = self.wait_for(self.f2p)
            if di == 0:     # this means the round has ended
                self.clock_round += 1
                self.read_messages()    # reads messagesna dn queues the messages to be sent
                self.roundok = False
            else: 
                self.p2z.write( ('early',) )
                return #TODO change to check

        if len(self.todo) > 0:
            # pop off todo and do it
            f,args = self.todo.pop(0)
            if f: f(*args)
            else: dump.dump()
        elif len(self.todo) == 0 and not self.outputset:      
            self.p2f.write( ((self.sid,'F_clock'),('RoundOK',)) )
            self.roundok = True
        else: dump.dump()

    def start_sync(self):
        if self.roundok and self.startsync:
            self.p2f.write( ((self.sid, 'F_clock'),('RequestRound',)) )
            fro,di = self.wait_for(self.f2p)
            if di == 1: raise Exception('Start synchronization not done')
            self.roundok = False
            self.startsync = False

    #def run(self):
    #    while True:
    #        ready = gevent.wait(
    #            objects=self.channels,
    #            count=1
    #        )
    #        assert len(ready) == 1
    #        r = ready[0]
    #        self.start_sync()
    #        msg = r.read()
    #        r.reset()
    #        self.handlers[r](msg)
