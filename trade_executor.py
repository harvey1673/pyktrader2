#-*- coding:utf-8 -*-
import logging
from base import *
import itertools
from misc import *
import datetime
import trade
import order

class ExecAlgoBase(object):
    def __init__(self, xtrade, agent, stop_price = None, max_vol = 20, inst_rank = None):
        self.xtrade = xtrade
        if inst_rank == None:
            inst_rank = range(len(self.xtrade.instIDs))
        self.instIDs = [xtrade.instIDs[i] for i in inst_rank]
        self.max_vol = max_vol
        self.stop_price = stop_price
        self.agent = agent

    def on_partial_cancel(self):
        pass

    def execute(self):
        pass

class ExecAlgoFixTimer(ExecAlgoBase):
    '''send out order by fixed period, cancel the trade when hit the stop price '''
    def __init__(self, xtrade, agent, stop_price = None, max_vol = 20, time_period = 600, price_type = OPT_LIMIT_ORDER, \
                       order_offset = True, inst_rank = None):
        super(ExecAlgoFixTimer, self).__init__(xtrade, agent, stop_price = stop_price, max_vol = max_vol, inst_rank = inst_rank)
        self.timer_period = time_period
        self.next_timer = self.agent.tick_id
        self.price_type = price_type
        self.order_num = 3 if order_offset else 1

    def execute(self):
        status = self.xtrade.status
        if (status in [trade.TradeStatus.Pending, trade.TradeStatus.Done, trade.TradeStatus.StratConfirm]):
            return status
        direction = 1 if self.xtrade.vol > 0 else -1
        if self.stop_price and (self.xtrade.underlying.mid_price - self.stop_price) * direction >= 0:
            stop_flag = True
            self.next_timer = self.agent.tick_id - 1
        else:
            stop_flag = False
        if (status in [trade.TradeStatus.OrderSent, trade.TradeStatus.Cancelled]) and (self.agent.tick_id > self.next_timer):
            unfilled = 0
            for instID in self.xtrade.order_dict:
                for iorder in self.xtrade.order_dict[instID]:
                    if not iorder.is_closed():
                        self.agent.cancel_order(iorder)
                        cancel_flag = True
        if stop_flag:
            self.xtrade.status = trade.TradeStatus.Cancelled
            status = trade.TradeStatus.Cancelled
        if cancel_flag:
            return status
        if status == trade.TradeStatus.Cancelled:
            self.on_partial_cancel()
            return status
        next_inst = ''
        next_vol = 0
        if status == trade.TradeStatus.PFilled:
            for idx, instID in enumerate(self.instIDs):
                unfilled = abs(self.working_vol * self.xtrade.units[idx]) - self.xtrade.order_filled[idx]
                if unfilled > 0:
                    next_inst = instID
                    next_vol = unfilled
        elif (self.xtrade.status == trade.TradeStatus.Ready) and (self.next_timer < self.agent.tick_id):
            self.xtrade.working_vol =  min(self.max_vol, abs(self.xtrade.remaining_vol)) * direction
            self.xtrade.remaining_vol -= self.xtrade.working_vol
            inst_seq = 0
            self.xtrade.order_dict[self.instIDs[inst_seq]] = []
            next_vol = self.xtrade.units[inst_seq] * self.xtrade.working_vol
        if next_vol != 0:
            limit_price = self.xtrade.underlying.ask_price1 if direction > 0 else self.xtrade.underlying.bid_price1
            gway = self.agent.gateway_map(self.instIDs[0])
            new_orders = gway.book_order(next_inst, next_vol, self.price_type, limit_price, trade_ref = self.xtrade.id, order_num = self.order_num)
            self.xtrade.order_dict[self.instIDs[0]] += new_orders
            self.xtrade.status = trade.TradeStatus.OrderSent
            self.next_timer += self.timer_period
