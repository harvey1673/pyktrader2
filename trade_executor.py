#-*- coding:utf-8 -*-
import logging
from base import *
from misc import *
import datetime
import trade

class TradeStatus:
    Pending, OrderSent, PFilled, Done, Cancelled, StratConfirm = range(6)

class ExecAlgoBase(object):
    def __init__(self, xtrade, agent, min_vol = 1, max_vol = 20, start_time = None, end_time = None, stop_price = None):
        self.xtrade = xtrade
        self.agent = agent
        self.start_time = start_time
        self.end_time = end_time
        self.min_vol = min_vol
        self.max_vol = max_vol
        self.is_working = True if start_time == None or self.agent.tick_id >= start_time else False    
        
    def unwind(self):
        pass
    
    def update(self):
        self.xtrade.update()
        return self.xtrade.status
    
    def process(self):
        pass
                                
    def suspend(self):
        pass       

class ExecAlgoFixTimer(ExecAlgoBase):
    def __init__(self, xtrade, agent, min_vol = 1, max_vol = 20, start_time = None, end_time = None, stop_price = None, time_period = 600):
        super(ExecAlgoFixTimer, self).__init__(xtrade, agent, min_vol, max_vol, start_time, end_time, stop_price)
        self.timer_period = time_period
        self.next_timer = None

    def calc_price(self):
        sum([p * v * cf for p, v, cf in zip(order_prices, self.xtrade.volumes, self.xtrade.conv_f)]) / self.xtrade.price_unit

    def process(self):
        if self.xtrade.status == TradeStatus.Pending:
            pass
        pass




