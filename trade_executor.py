#-*- coding:utf-8 -*-
import logging
from base import *
from misc import *
import datetime
import order

class TradeExecBase(object):
    def __init__(self, etrade, use_fak = True):
        self.use_fak = use_fak
        self.child_orders = []
        self.filled_vol = 0
        pass

    def update_status():
        pass