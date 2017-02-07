#-*- coding:utf-8 -*-
import logging
from base import *
import itertools
from misc import *
import datetime
import trade
import order

class ExecAlgoBase(object):
    def __init__(self, xtrade, agent, stop_price = None, min_vol = 1, max_vol = 20):
        self.xtrade = xtrade
        self.min_vol = min_vol
        self.max_vol = max_vol
        self.stop_price = stop_price
        self.agent = agent
        
    def unwind(self):
        pass
    
    def process(self):
        pass
                                
    def suspend(self):
        pass

    def create_orders(self, volume):
        pass

class ExecAlgoFixTimer(ExecAlgoBase):
    def __init__(self, xtrade, agent, stop_price = None, min_vol = 1, max_vol = 20, time_period = 600):
        super(ExecAlgoFixTimer, self).__init__(xtrade, agent, stop_price = stop_price, min_vol = min_vol, max_vol = max_vol)
        self.timer_period = time_period
        self.next_timer = self.agent.tick_id

    def process(self):
        if (self.xtrade.status in [trade.TradeStatus.Pending, trade.TradeStatus.Done, trade.TradeStatus.Cancelled]) \
                or (self.next_timer > self.agent.tick_id):
            pass
        if self.xtrade.status in [trade.TradeStatus.PFilled, trade.TradeStatus.Ready]:
            next_vol = min(self.max_vol, self.remaining_vol)
            self.agent.gateway_map()


