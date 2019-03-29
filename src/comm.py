from collections import defaultdict
global commap
global corrupted

commap = {}
currupted = defaultdict(bool)


FUNCTIONALITY = 0
PARTY = 1
ADVERSARY = 2
SIMULATOR = 3

def cset(sid,pid,itm):
    if (sid,pid) not in commap:
        commap[sid,pid] = itm

def isf(sid,pid):
    try:
        return commap[sid,pid] == FUNCTIONALITY
    except KeyError:
        return False

def isadversary(sid,pid):
    try:
        return commap[sid,pid] == ADVERSARY
    except KeyError:
        return False

def isparty(sid,pid):
    try:
        return commap[sid,pid] == PARTY
    except KeyError:
        return False

def getitm(sid,pid):
    try:
        return commap[sid,pid]
    except KeyError:
        return None

def setAdversary(itm):
    sid,pid = itm.sid,itm.pid
    cset(sid,pid,ADVERSARY)
    print('ADVERSARY', sid, pid)

def setFunctionality(itm):
    sid,pid = itm.sid,itm.pid
    cset(sid,pid,FUNCTIONALITY)
    print('FUNCTIONALITY', sid, pid)

def setParty(p):
    sid,pid = p.sid,p.pid
    cset(sid,pid,PARTY)
    print('PARTY', sid, pid)

def setParties(parties):
    for p in parties:
        setParty(p)

def corrupt(sid,pid):
    corrupted[sid,pid] = True

def isdishonest(sid,pid):
    return corrupted[sid,pid]
def ishonest(sid,pid):
    return not corrupted[sid,pid]
