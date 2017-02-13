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
        self.order_filled = []
        self.working_vol = 0
        self.remaining_vol = self.vol - self.filled_vol - self.working_vol
        self.aggressive_level = aggressiveness
        self.start_time = start_time
        self.end_time = end_time
        self.algo = None
        if agent != None:
            self.set_agent(agent)

    def set_agent(self, agent):
        self.agent = agent
        self.underlying = agent.get_underlying(self.instIDs, self.units, self.price_unit)

    def set_algo(self, algo):
        self.algo = algo

    def calc_filled_price(self, order_dict):
        filled_prices = [sum([o.filled_price * o.filled_volume for o in order_dict[instID]])/sum([o.filled_volume \
                                    for o in order_dict[instID]]) for instID in self.instIDs]
        if len(self.instIDs) == 1:
            return self.filled_price[0]
        else:
            return self.underlying.price(prices=filled_prices)

    def refresh(self):
        fill_status = []
        filled_vol = []
        open_vol = 0
        total_vol = 0
        for instID, unit in zip(self.instIDs, self.units):
            if instID in self.order_dict:
                fill_vol = sum([o.filled_volume for o in self.order_dict[instID]])
                full_vol = sum([o.volume for o in self.order_dict[instID]])
            else:
                fill_vol = 0
                full_vol = 0
            open_vol += full_vol - fill_vol
            total_vol += abs(unit * self.working_vol)
            filled_vol.append(fill_vol)
        self.order_filled = filled_vol
        if open_vol > 0:
            self.status = TradeStatus.OrderSent
        elif sum(fill_vol) >= total_vol:
            self.working_filled()
        elif self.status == TradeStatus.Cancelled:
            self.algo.on_partial_cancel()
        else:
            self.status = TradeStatus.PFilled
        if (self.filled_vol == self.vol) or ((self.status == TradeStatus.Cancelled) and len(self.order_dict)==0):
            self.status = TradeStatus.Done
            self.order_dict = {}
            self.order_filled = []
            self.working_vol = 0
            self.remaining_vol = 0
            self.update_strat()
        return self.status

    def on_trade(self, price, volume):
        new_vol = self.filled_vol + volume
        self.filled_price = (self.filled_prie * self.filled_vol + price * volume)/new_vol
        self.filled_vol = new_vol
        self.remaining_vol = self.vol - self.working_vol - self.filled_vol
        if self.filled_vol == self.vol:
            self.status = TradeStatus.Done
            self.algo = None
            self.update_strat()

    def working_filled(self):
        working_price = self.calc_filled_price(self.order_dict)
        working_vol = self.working_vol
        self.working_vol = 0
        self.order_dict = {}
        self.order_filled = []
        self.on_trade(working_price, working_vol)
        self.status = TradeStatus.Ready    
    
    def cancel(self):
        self.status = TradeStatus.Cancelled
        self.remaining_vol = 0
        self.working_vol = 0
        self.order_dict = {}
        self.order_filled = []
        self.update_strat()

    def update_strat(self):
        strat = self.agent.strategies[self.strategy]
        strat.on_trade(self)

    def execute(self):
        if self.algo:
            self.algo.execute()
