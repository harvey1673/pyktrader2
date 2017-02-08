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

class OrderFillStatus:
    Empty, Partial, Full = range(3)
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
        self.order_status = []
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

    def calc_filled_price(self, order_dict):
        filled_prices = [sum([o.filled_price * o.filled_volume for o in order_dict[instID]])/sum([o.filled_volume \
                                    for o in order_dict[instID]]) for instID in self.instIDs]
        if len(self.instIDs) == 1:
            return self.filled_price[0]
        else:
            return self.underlying.price(prices=filled_prices)

    def update_status(self):
        if len(self.order_dict) == 0:
            return self.status
        fill_status = []
        for instID, unit in zip(self.instIDs, self.units):                
            if instID in self.order_dict:
                fill_vol = sum([o.filled_volume for o in self.order_dict[instID]])
            else:
                fill_vol = 0
            if fill_vol == abs(unit * self.working_vol):
                curr_status = OrderFillStatus.Full
            elif fill_vol == 0:
                curr_status = OrderFillStatus.Empty
            else:
                curr_status = OrderFillStatus.Partial
            fill_status.append(curr_status)            
        if (OrderFillStatus.Partial in fill_status) or (OrderFillStatus.Full not in fill_status):
            self.status = TradeStatus.OrderSent
        elif OrderFillStatus.Empty not in fill_status:
            working_price = self.calc_filled_price(self.order_dict)
            new_vol = self.filled_vol + self.working_vol
            self.filled_price = (self.filled_price * self.filled_vol + working_price * self.working_vol)/new_vol
            self.filled_vol = new_vol
            self.working_vol = 0
            self.order_dict = {}
            fill_status = []
            self.status = TradeStatus.Ready
        else:
            self.status = TradeStatus.PFilled
        self.order_status = fill_status
        if self.filled_vol == self.vol:
            self.status = TradeStatus.Done
            self.order_dict = {}
            self.order_status = []
            self.working_vol = 0            
        return self.status

    def execute(self):
        self.exec_algo.process()
