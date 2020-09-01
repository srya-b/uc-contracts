from messages import *

# haskell def
#   data ComP2F a = ComP2F_Commit a | ComP2F_Open deriving Show
class ComP2F: pass

class ComP2F_Commit(ComP2F):
    def __init__(self, a):
        self.bit = a

class ComP2F_Open(ComP2F): pass


# haskell def
#   data ComF2P a = ComF2P_OK | ComF2P_Commit | ComF2P_Open a deriving Show
class ComF2P: pass

class ComF2P_OK(ComF2P): pass

class ComF2P_Commit(ComF2P): pass

class ComF2P_Open(ComF2P):
    def __init__(self, a):
        self.bit = a

# haskell def
#   data RoP2F a b   = RoP2F_Ro a | RoP2F_m b
class RoP2F: pass

class RoP2F_Ro(RoP2F):
    def __init__(self, a):
        self.preimage = a

class RoP2F_m(RoP2F):
    def __init__(self, a):
        self.msg = a

# haskell def
#   data ProtComm_Msg a = ProtComm_Commit Int | ProtComm_Open Int a deriving Show
class ProtComm_Msg: pass

class ProtComm_Commit(ProtComm_Msg):
    def __init__(self, i):
        self.hash = i

class ProtComm_Open(ProtComm_Open):
    def __init__(self, a, b):
        self.nonce = a
        self.bit = b
