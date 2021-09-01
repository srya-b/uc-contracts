
from ecdsa import SigningKey, VerificationKey

class G_cert_inner(UCWrappedFunctionality):
    def __init__(self, k, bits, crupt, sid, pid, channels, pump, poly, importargs, target_pid):
        UCWrappedFunctionality.__init__(self, k, bits, crupt, sid, pid, channels, poly, importargs)
        self.handlers[self.channels['_2w']] = self.gfunc_msg

        #self.target_pid = pid
        #self.first = True
        self.first = defaultdict(lambda:True)

        #self.sk = None
        #self.vk = None
        self.sk = {}
        self.vk = {}
        self.sigs = defaultdict(dict)
        self.adv_sigs = defaultdict(dict)
        self.keys = {}

        def exec_genkey(self, sender):
            if not self.sk and not self.vk:
                _sid,_pid = sender
                self.sk[pid] = SigningKey.generate()
                self.vk[pid] = sk.verifyingkey
            self.write_and_wait_expect(
                ch='w2_', msg=((self.sid, 'G_bb'), ('register', _pid, self.vk[pid])),
                read='_2w', expect=('OK',)
            )
            self.write( 'w2p', (sender, ('KeyGenOK',)) )

        def keygen(self, sender):
            _sid,_pid = sender
            if self.is_honest(_sid, _pid):
                self.schedule('exec_genkey', (sender,), 1)

        # TODO adversary can control both??
        def exec_sign(self, sender, msg):
            _sid,_pid = sender
            if (msg, 0) in self.sigs[_pid]:
                self.write( 'w2p', (sender, ('SignFail', msg)) )
            elif msg in self.adv_sigs[_pid]:
                self.sigs[_pid][ (msg, 1) ] = self.adv_sigs[_pid][msg]
                self.write( 'w2p', (sender, ('Signature', msg, self.sigs[_pid][(msg,1)])) )
            else:
                msg_sig = self.sk[_pid].sign(str(msg).encode())
                self.sigs[_pid][ (msg,1) ] = msg_sig
                self.write('w2p', (sender, ('Signature', msg, msg_sig))) 

        def sign(self, sender, msg):
            _sid,_pid = sender
            if self.is_honest(_sid, _pid):
                self.schedule('exec_sign', (sender,), 1)
            else: 
                fro,msg = self.write_and_wait_for(
                    ch='w2_', msg=('retrieve', _pid),
                    read='_2w'
                )
                (retrieve, party, v) = msg
                if v is None: self.pump.write(''); return
                else:
                    self.schedle('exec_sig', (sender,), 1)
            self.pump.write('')
    
        def verify(self, sender, msg, sig):
            _sid, _pid = sender
            if _pid not in self.keys:
                self.write_and_wait_for(
                    ch='w2_', msg=('retrieve', _pid), read='_2w'
                )
                (retrieve, party, v) = msg
                if v is None:
                    self.write( 'w2p', (sender, msg, 0) )
                else:
                    self.keys[_pid] = v
                    self.schedule('exec_verify', (sender, msg, sig), 1)


        def party_msg(self, d):
            msg = d.msg
            imp = d.imp
            sender,msg = msg
            (sid,pid) = sender

            if msg[0] == 'keygen' and self.first[pid]:
                self.keygen(self, sender)
                self.first[pid] = False
            elif msg[0] == 'sign' and not self.first[pid]:
                self.sign(self, msg[1], msg[2])
            elif msg[0] == 'verify':
                self.verify(self, msg[1], msg[2], msg[3])
            else:
                self.write('w2p', (sender, ('OK',)))

        def adv_msg(self, d):
            msg = d.msg
            imp = d.imp
            
            if msg[0] == 'setkey':
                if not self.sk and not self.vk:
                    self.sk = msg[1]; self.vk = msg[2];
            else:
                self.pump.write('')
