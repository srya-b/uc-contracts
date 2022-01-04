from uc.itm import UCAdversary

class Sim_Flip(UCAdversary):
    def __init__(self, k, bits, crupt, sid, pid, channels, pump):
        self.ssid = sid[0]
        self.flipper = sid[1]
        self.receiver = sid[2]

        UCAdversary.__init__(self, k, bits, crupt, sid, pid, channels, pump)

        self.receiver_bit = None
        self.z2a2p_msgs['sendmsg'] = self.sendmsg
        self.func_msgs['askflip'] = self.func_askflip
        self.party_msgs['recvmsg'] = self.recvmsg
        if self.is_dishonest(self.flipper):
            self.deliver_receiver = False
            self.env_commit_bit = None
            self.flip = None
            self.z2a2p_msgs['commit'] = self.flipper_commit
            self.z2a2p_msgs['reveal'] = self.flipper_open
        elif self.is_dishonest(self.receiver):
            self.deliver_flipper = False
            self.flipper_bit = None
            self.func_msgs['flip'] = self.receiver_flip
       
    #
    # crupt flipper
    #
    def flipper_commit(self, to, bit):
        """FLIPPER CRUPT: Z tells A to tell crupt flipper
        to initiate the commitment with F_Com

        Msg:
            From Z: ('A2P', ((sid,1), ('commit', bit)))

        Args:
            to: crupt party to give input to
            bit: bit in the commit msg
        """
        self.env_commit_bit = bit
        self.write( ch='a2p', msg=(to, ('flip',)) )
        flipleak = self.read('f2a')
        self.write( ch='a2p', msg=(to, ('getflip',)) )
        askflip = self.read('f2a')
        self.write( ch='a2f', msg=('yes',) )
        sender,(_,self.flip) = self.read('p2a')
        self.receiver_bit = self.flip ^ self.env_commit_bit
        self.write( ch='a2z', msg=('P2A', (self.flipper, ('recvmsg', ('bit', self.receiver_bit)))) )
   
    def func_askflip(self, who):
        """React to F_flip asking to deliver the flip to a party.

        Msg:
            From F_flip: ('askflip', who)

        Args:
            who: the party that requsted 'getflip' in F_flip
        """
        print('askflip')
        if self.is_dishonest(self.flipper):
            print('d flipper')
            if who == self.receiver and self.deliver_receiver:
                self.write( ch='a2f', msg=('yes',) )
            else:
                self.write( ch='a2f', msg=('no',) )
        elif self.is_dishonest(self.receiver):
            print(' d receiver')
            if who == self.flipper and self.deliver_flipper:
                self.write( ch='a2f', msg=('yes',) )
            else:
                self.write( ch='a2f', msg=('no',) )
        else:
            self.write( ch='a2f', msg=('yes',) )

    def flipper_open(self, to):
        """FLIPPER CRUPT: Z telling crupt flipper to open the commitment.

        Msg:
            From Z: ('A2P', ((sid,1), ('open',)))

        Args:
            to: person to give 'open' input to.
        """
        self.deliver_receiver = True
        self.pump.write('')

    def sendmsg(self, to, msg):
        """Z request to send a message from `to` to the other party.

        Msg:
            From Z: ('A2P', (to=(sid,pid), ('sendmsg', msg)))

        Args:
            to: crupt party to give input to
            msg: the message
        """
        self.write( ch='a2p', msg=(to, ('sendmsg', msg)) )

    def recvmsg(self, sender, msg):
        """Receive message from crupt party from F_flip

        Msg:
            From P: ('recvmsg', msg)

        Args:
            sender: the crupt party outputting recvmsg to A
        """
        self.write( ch='a2z', msg=('P2A', (sender, ('recvmsg', msg))) )
    #
    # crupt receiver
    #
    def receiver_flip(self):
        """RECEIVER CRUPT: receive a "flip" leak from F_flip

        Msg:
            From F_flip: ('flip',)
        """
        self.write( ch='a2z', msg=('P2A', (self.receiver, ('commit',))) )
        self.z2a2p_msgs['sendmsg'] = self.receiver_sendmsg

    def receiver_sendmsg(self, sender, msg):
        """RECEIVER CRUPT: a sendmsg request from Z for crupt receiver (msg=('bit', b)).
        If the message is the bit required by the protocol then gettheflip and
        simulate the bit `b` that the honest flipper committed to. If this operation
        fails, then don't reliver the flip to the flipper or the receiver.

        Msg:
            From Z: ('A2P', ((sid,2), ('sendmsg', msg)))
        
        Args:
            sender: the crupt party to give input to (will be receiver)
            msg: the message to give as input to crupt receiver
        """
        try:
            if msg[0] == 'bit':
                assert msg[1] == 0 or msg[1] == 1
                self.receiver_bit = msg[1]
                self.write( ch='a2p', msg=(sender, ('getflip',)) )
                askflip = self.read('f2a')
                self.write( ch='a2f', msg=('yes',) )
                receiver,(_,self.flip) = self.read('p2a')
                self.b = self.receiver_bit ^ self.flip
                self.write( ch='a2z', msg=('P2A', (sender, ('open', self.b))) )
                self.deliver_flipper = True
            else: self.sendmsg(sender, msg)
        except AssertionError:
            self.sendmsg(sender, msg)
         
