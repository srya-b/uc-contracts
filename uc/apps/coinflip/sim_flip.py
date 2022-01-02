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
            self.env_commit_bit = None
            self.flip = None
            self.deliver_receiver = False
            self.z2a2p_msgs['sendmsg'] = self.sendmsg
            self.z2a2p_msgs['commit'] = self.flipper_commit
            self.z2a2p_msgs['reveal'] = self.flipper_open
        elif self.is_dishonest(self.sid, self.receiver):
            self.flipper_bit = None
            self.func_msgs['askflip'] = self.receiver_askflip
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
        print('askflip')
        if who == self.flipper:
            self.write( ch='a2f', msg=('yes',) )
        elif self.deliver_receiver:
            print('deliver to receiver')
            self.write( ch='a2f', msg=('yes',) )
        else:
            print('dont deliver to receiver')
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
        self.write( ch='a2z', msg=('P2A', ('commit',)) )
        self.z2a2p_msgs['sendmsg'] = self.receiver_sendmsg

    def receiver_sendmsg(self, to, who):
        try:
            if msg[0] == 'bit' and to == (self.sid, self.receiver):
                assert msg[1] == 0 or msg[1] == 1
                self.receiver_bit = msg[1]
                self.write( ch='a2p', msg=(to, ('getflip',)) )
                askflip = self.read('f2a')
                self.write( ch='a2f', msg=('yes',) )
                receiver,(_,self.flip) = self.read('p2a')
                self.b = self.receiver_bit ^ self.flip
                self.write( ch='a2z', msg=('P2A', (to, ('open', self.b))) )
            else: self.sendmsg(to, who)
        except:
            self.sendmsg(to, msg)
         
