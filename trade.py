#-*- coding:utf-8 -*-
import logging
from base import *
from misc import *
import itertools
import datetime
import csv
import os.path
import order
from trade_executor import *

class ETradeStatus:
    Pending, Processed, PFilled, Done, Cancelled, StratConfirm = range(6)

class TradeStatus:
    Pending, Ready, OrderSent, PFilled, Done, Cancelled, StratConfirm, Suspended = range(8)
# Pending: trigger trade, Ready: ok to start process with zero vol, OrderSent: wait for order update

Alive_Trade_Status = [TradeStatus.Pending, TradeStatus.Ready, TradeStatus.OrderSent, TradeStatus.PFilled]

class XTrade(object):
    # instances = weakref.WeakSet()
    id_generator = itertools.count(int(datetime.datetime.strftime(datetime.datetime.now(), '%d%H%M%S')))
    def __init__(self, instIDs, units, vol, limit_price, price_unit=1, strategy="dummy", book="0", \
                 agent=None, start_time = 300000, end_time = 2115000, aggressiveness = 1):
        self.id = next(self.id_generator)
        self.instIDs = instIDs
        self.units = units
        self.vol = vol
        self.filled_vol = 0
        self.filled_price = 0
        self.limit_price = limit_price
        self.price_unit = price_unit
        self.underlying = None
        self.strategy = strategy
        self.book = book
        self.agent = agent
        self.status = TradeStatus.Pending
        self.order_dict = {}
        self.order_vol = []
        self.working_vol = 0
        self.remaining_vol = self.vol - self.filled_vol - self.working_vol
        self.aggressive_level = aggressiveness
        self.start_time = start_time
        self.end_time = end_time
        self.exec_algo = ExecAlgoBase(self, agent)
        if agent != None:
            self.set_agent(agent)

    def set_agent(self, agent):
        self.agent = agent
        self.underlying = agent.get_underlying(self.instIDs, self.units, self.price_unit)

    def set_exec_algo(self, exec_algo):
        self.exec_algo = exec_algo

    def final_price(self):
        if len(self.instIDs) == 1:
            return self.filled_price[0]
        else:
            return self.underlying.price(prices=self.filled_price)

    def refresh_status(self):
        if self.status in [TradeStatus.StratConfirm, TradeStatus.Done, TradeStatus.Cancelled]:
            return
        if self.filled_vol == self.vol:
            self.status = TradeStatus.Done
            self.order_dict = {}
            self.working_vol = 0
        elif len(self.order_dict) == 0:
            self.status = TradeStatus.Ready
            self.order_vol = []
            self.working_vol = 0
        elif len(self.order_dict) > 0:
            self.order_vol = [sum([o.filled_volume for o in self.order_dict[instID]]) \
                                    if instID in self.order_dict else 0 for instID in self.instIDs]
            remain_vol = [self.working_vol * abs(u) - v for u, v in zip(self.units, self.order_vol)]
            if sum(remain_vol) == 0:
                new_vol = self.filled_vol + self.working_vol
                weighted_price = [sum([o.filled_price * o.filled_volume  for o in self.order_dict[instID]]) \
                     if instID in self.order_dict else 0 for instID in self.instIDs]
                self.filled_price = self.filled_price * self.filled_vol + weighted_price
                self.order_dict = {}
                self.working_vol = 0
                self.status = TradeStatus.PFilled
            elif (0 in remain_vol):
                self.status = TradeStatus.OrderSent
        else:
            self.status = TradeStatus.Pending
            self.order_vol = []
            self.working_vol = 0

    def execute(self):
        self.exec_algo.process()
