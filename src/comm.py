from collections import defaultdict

global commap
global corrupted
global itmmap
global adversary

commap = {}
itmmap = {}
adversary = None
corrupted = defaultdict(bool)


FUNCTIONALITY = 0
PARTY = 1
ADVERSARY = 2
SIMULATOR = 3

def cset(sid,pid,tag,itm):
    if (sid,pid) not in commap:
        commap[sid,pid] = tag
        itmmap[sid,pid] = itm

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
        return itmmap[sid,pid]
    except KeyError:
        return None

def itmstring(sid,pid):
    try:
        return str(getitm(sid,pid))
    except:
        return ''

def setAdversary(itm):
    global adversary
    sid,pid = itm.sid,itm.pid
    cset(sid,pid,ADVERSARY,itm)
    adversary = itm
    print('ADVERSARY', sid, pid)

def setFunctionality(itm):
    sid,pid = itm.sid,itm.pid
    cset(sid,pid,FUNCTIONALITY,itm)
    print('FUNCTIONALITY', sid, pid)

def setParty(p):
    sid,pid = p.sid,p.pid
    cset(sid,pid,PARTY,p)
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
