from math import floor, ceil
from uc.itm import UCWrappedFunctionality
from uc.utils import wait_for
from collections import defaultdict
import logging

class Contract_Test:
    def __init__(self, initvalue):
        self.initvalue = initvalue

    def add(self, d, tx):
        self.initvalue += d

    def party_msg(self, tx):
        print('tx', tx)
        getattr(self, tx['func'])(*tx['args'], tx)
                

