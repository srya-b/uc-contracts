from uc.itm import UCAdversary

class Sim_Flip(UCAdversary):
    def __init__(self, k, bits, crupt, sid, pid, channels, pump):
        self.ssid = sid[0]
        self.flipper = sid[1]
        self.receiver = sid[2]

        UCAdversary.__init__(self, k, bits, crupt, sid, pid, channels, pump)

        self.z2a2p_msgs['sendmsg'] = self.sendmsg
        self.receiver_bit = None
        self.func_msgs['askflip'] = self.func_askflip
        self.party_msgs['recvmsg'] = self.recvmsg
        if self.is_dishonest(self.sid, self.flipper):
            self.deliver_receiver = False
            self.env_commit_bit = None
            self.flip = None
            self.z2a2p_msgs['sendmsg'] = self.sendmsg
            self.z2a2p_msgs['commit'] = self.flipper_commit
            self.z2a2p_msgs['reveal'] = self.flipper_open
        elif self.is_dishonest(self.sid, self.receiver):
            self.deliver_flipper = False
            self.flipper_bit = None
            #self.func_msgs['askflip'] = self.receiver_askflip
            #self.z2a2p_msgs['sendmsg'] = self.receiver_sendmsg
            self.func_msgs['flip'] = self.receiver_flip
       
    #
    # crupt flipper
    #
    def flipper_commit(self, to, bit):
        if to == (self.sid, self.flipper): 
            self.env_commit_bit = bit
            self.write( ch='a2p', msg=(to, ('flip',)) )
            flipleak = self.read('f2a')
            self.write( ch='a2p', msg=(to, ('getflip',)) )
            askflip = self.read('f2a')
            self.write( ch='a2f', msg=('yes',) )
            sender,(_,self.flip) = self.read('p2a')
            self.receiver_bit = self.flip ^ self.env_commit_bit
            self.write( ch='a2z', msg=('P2A', ((self.sid, self.flipper), ('recvmsg', ('bit', self.receiver_bit)))) )
        else: self.pump.write('')
   
    def func_askflip(self, who):
        if self.is_dishonest(self.sid, self.flipper):
            if who == (self.sid, self.receover) and self.deliver_receiver:
                self.write( ch='a2f', msg=('yes',) )
            else:
                self.write( ch='a2f', msg=('no',) )
        elif self.is_dishonest(self.sid, self.receiver):
            if who == (self.sid,self.flipper) and self.deliver_flipper:
                self.write( ch='a2f', msg=('yes',) )
            else:
                self.write( ch='a2f', msg=('no',) )

    def flipper_open(self, to):
        if to == (self.sid, self.flipper):
            self.deliver_receiver = True
        self.pump.write('')

    def sendmsg(self, to, msg):
        self.write( ch='a2p', msg=(to, ('sendmsg', msg)) )

    def recvmsg(self, sender, msg):
        self.write( ch='a2z', msg=('P2A', (sender, ('recvmsg', msg))) )
    #
    # crupt receiver
    #
    def receiver_flip(self):
        self.write( ch='a2z', msg=('P2A', ((self.sid,self.receiver), ('commit',))) )
        self.z2a2p_msgs['sendmsg'] = self.receiver_sendmsg

    def receiver_sendmsg(self, sender, msg):
        try:
            if msg[0] == 'bit':
                assert msg[1] == 0 or msg[1] == 1
                self.receiver_bit = msg[1]
                print('receiver sending msg\n\n')
                self.write( ch='a2p', msg=(sender, ('getflip',)) )
                askflip = self.read('f2a')
                print('\n\nsending the open to Z\n\n')
                self.write( ch='a2f', msg=('yes',) )
                receiver,(_,self.flip) = self.read('p2a')
                self.b = self.receiver_bit ^ self.flip
                self.write( ch='a2z', msg=('P2A', (sender, ('open', self.b))) )
                self.deliver_flipper = True
            else: self.sendmsg(sender, msg)
        except AssertionError:
            print('\n\nthe except is being triggered\n\n')
            self.sendmsg(sender, msg)
         
