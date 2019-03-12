global commap
commap = {}

FUNCTIONALITY = 0
PARTY = 1
ADVERSARY = 2
SIMULATOR = 3

def cset(sid,pid,itm):
    if (sid,pid) not in commap:
        commap[sid,pid] = itm

def isf(sid,pid):
    try:
        return comman[sid,pid] == FUNCTIONALITY
    except KeyError:
        return False

def isadversary(sid,pid):
    try:
        return commap[sid,pid] == ADVERSARY
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

def setFunctionality(itm):
    sid,pid = itm.sid,itm.pid
    cset(sid,pid,FUNCTIONALITY)

def setParty(p):
    sid,pid = p.sid,p.pid
    cset(sid,pid,PARTY)

def setParties(parties):
    for p in parties:
        setParty(p)
