#-*- coding:utf-8 -*-
import logging
from base import *
from misc import *
import datetime
import order

class TradeExecBase(object):
    def __init__(self, etrade, use_fak = True):
        self.use_fak = use_fak
        self.etrade = etrade
        self.child_orders = []
        self.filled_vol = 0

    def update_status(self, status):
        self.etrade.status = status

    def