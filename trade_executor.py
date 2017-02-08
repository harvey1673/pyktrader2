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
        self.instIDs = xtrade.instIDs
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
    def __init__(self, xtrade, agent, stop_price = None, min_vol = 1, max_vol = 20, time_period = 600, price_type = OPT_LIMIT_ORDER, \
                       order_offset = True, tick_num = 1):
        super(ExecAlgoFixTimer, self).__init__(xtrade, agent, stop_price = stop_price, min_vol = min_vol, max_vol = max_vol)
        self.timer_period = time_period
        self.next_timer = self.agent.tick_id
        self.price_type = price_type
        self.order_num = 3 if order_offset else 1

    def process(self):
        if (self.xtrade.status in [trade.TradeStatus.Pending, trade.TradeStatus.Done, trade.TradeStatus.Cancelled]):
            return
        direction = 1 if self.xtrade.vol > 0 else -1
        if self.stop_price and (self.xtrade.underlying.mid_price - self.stop_price) * direction > 0:
            cancel_flag = True
        else:
            cancel_flag = False
        trade_vol = 0
        if (self.xtrade.status == trade.TradeStatus.Ready) and (not cancel_flag):
            trade_vol = min(self.max_vol, abs(self.xtrade.remaining_vol)) * direction
        elif (self.xtrade.status == trade.TradeStatus.OrderSent) and (self.agent.tick_id > self.next_timer):
            unfilled = 0
            for iorder in self.xtrade.order_dict[self.instIDs[0]]:                
                unfilled += (iorder.volume - iorder.filled_volume)
                if not iorder.is_closed():
                    self.agent.cancel_order(iorder)
                    cancel_flag = True
            trade_vol = unfilled * direction
        if (not cancel_flag) and (trade_vol != 0):
            limit_price = self.xtrade.underlying.ask_price1 if direction > 0 else self.xtrade.underlying.bid_price1
            gway = self.agent.gateway_map(self.instIDs[0])
            new_orders = gway.book_order(self.instIDs[0], trade_vol, self.price_type, limit_price, trade_ref = self.xtrade.id, order_num = self.order_num)
            self.xtrade.order_dict[self.instIDs[0]] += new_orders
            self.next_timer += self.timer_period
        elif cancel_flag and (self.xtrade.status != trade.TradeStatus.OrderSent):
            self.xtrade.cancel()
