#-*- coding:utf-8 -*-
import logging
from base import *
import itertools
from misc import *
import datetime
import trade
import order

class ExecAlgoBase(object):
    def __init__(self, xtrade, stop_price = None, max_vol = 20):
        self.xtrade = xtrade
        self.instIDs = xtrade.instIDs
        self.max_vol = max_vol
        self.stop_price = stop_price
        self.agent = xtrade.agent

    def unwind(self, pair):
        strat = self.agent.strategies[self.xtrade.strategy]
        strat.add_unwind(pair, book = self.xtrade.book)

    def on_partial_cancel(self):
        pass

    def execute(self):
        pass

class ExecAlgo1DFixTimer(ExecAlgoBase): 
    def __init__(self, xtrade, stop_price = None, max_vol = 20, time_period = 100, price_type = OPT_LIMIT_ORDER, tick_num = 1, order_type = 'SP'):
        super(ExecAlgoFixTimer, self).__init__(xtrade, stop_price = stop_price, max_vol = max_vol)        
        self.exchange_name = xtrade.instIDs[0]
        if order_type in ['SP', 'SPD', 'SPC']:
            if len(self.instIDs)
            self.exchange_name = order_type + ' ' + '&'.join(self.instIDs)
        self.timer_period = time_period
        self.next_timer = self.agent.tick_id + time_period
        self.price_type = price_type
        self.tick_num = tick_num

    def execute(self):
        status = self.xtrade.status
        if (status in [trade.TradeStatus.Pending, trade.TradeStatus.Done, trade.TradeStatus.StratConfirm]):
            return status
        direction = 1 if self.xtrade.vol > 0 else -1
        cancel_flag = False
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
        next_price = 0
        if status == trade.TradeStatus.PFilled:
            for seq in self.inst_rank:
                unfilled = abs(self.working_vol * self.xtrade.units[seq]) - self.xtrade.order_filled[seq]
                if unfilled > 0:
                    next_inst = self.xtrade.instIDs[seq]
                    next_vol = unfilled * sign(self.working_vol * self.xtrade.units[seq])
                    traded_prices = [ iorder.filled_price for iorder in reversed(self.xtrade.order_dict[next_inst]) if iorder.filled_vol > 0 ]
                    inst_obj = self.agent.instruments[next_inst]
                    next_price = max(traded_prices[0], inst_obj.shift_price(next_vol, self.tick_num)) if next_vol > 0 \
                                        else min(traded_prices[0], inst_obj.shift_price(next_vol, self.tick_num))
                    break
            if next_vol == 0:
                print "something wrong with trade status = PFilled, while no actually no unfilled volume"
                self.xtrade.working_filled()
                return self.xtrade.status
        elif (self.xtrade.status == trade.TradeStatus.Ready) and (self.next_timer < self.agent.tick_id):
            self.xtrade.working_vol =  min(self.max_vol, abs(self.xtrade.remaining_vol)) * direction
            self.xtrade.remaining_vol -= self.xtrade.working_vol
            next_inst = self.xtrade.instIDs[self.inst_rank[0]] 
            self.xtrade.order_dict[next_inst] = []
            next_vol = self.xtrade.units[self.inst_rank[0]] * self.xtrade.working_vol
            inst_obj = self.agent.instruments[next_inst]
            next_price = inst_obj.shift_price(next_vol, self.tick_num) if next_vol > 0 else inst_obj.shift_price(next_vol, self.tick_num)
        elif status == trade.TradeStatus.Cancelled:
            self.on_partial_cancel()
            return status
        if next_vol != 0:
            gway = self.agent.gateway_map(self.instIDs[0])
            new_orders = gway.book_order(next_inst, next_vol, self.price_type, next_price, trade_ref = self.xtrade.id, order_num = self.order_num)
            self.xtrade.order_dict[next_inst] += new_orders
            self.xtrade.status = trade.TradeStatus.OrderSent
            self.next_timer += self.timer_period
            status = trade.TradeStatus.OrderSent
        return status
    
    def on_partial_cancel(self):
        pass   
        
class ExecAlgoFixTimer(ExecAlgoBase):
    '''send out order by fixed period, cancel the trade when hit the stop price '''
    def __init__(self, xtrade, stop_price = None, max_vol = 20, time_period = 600, price_type = OPT_LIMIT_ORDER, \
                       order_offset = True, inst_rank = None, tick_num = 1):
        super(ExecAlgoFixTimer, self).__init__(xtrade, stop_price = stop_price, max_vol = max_vol)
        if inst_rank == None:
            inst_rank = range(len(self.instIDs))
        self.inst_rank = inst_rank
        self.instIDs = [self.xtrade.instIDs[inst_rank[i]] for i in inst_rank]
        self.timer_period = time_period
        self.next_timer = self.agent.tick_id
        self.price_type = price_type
        self.order_num = 3 if order_offset else 1
        self.tick_num = tick_num

    def execute(self):
        status = self.xtrade.status
        if (status in [trade.TradeStatus.Pending, trade.TradeStatus.Done, trade.TradeStatus.StratConfirm]):
            return status
        direction = 1 if self.xtrade.vol > 0 else -1
        cancel_flag = False
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
        next_price = 0
        if status == trade.TradeStatus.PFilled:
            for seq in self.inst_rank:
                unfilled = abs(self.working_vol * self.xtrade.units[seq]) - self.xtrade.order_filled[seq]
                if unfilled > 0:
                    next_inst = self.xtrade.instIDs[seq]
                    next_vol = unfilled * sign(self.working_vol * self.xtrade.units[seq])
                    traded_prices = [ iorder.filled_price for iorder in reversed(self.xtrade.order_dict[next_inst]) if iorder.filled_vol > 0 ]
                    inst_obj = self.agent.instruments[next_inst]
                    next_price = max(traded_prices[0], inst_obj.shift_price(next_vol, self.tick_num)) if next_vol > 0 \
                                        else min(traded_prices[0], inst_obj.shift_price(next_vol, self.tick_num))
                    break
            if next_vol == 0:
                print "something wrong with trade status = PFilled, while no actually no unfilled volume"
                self.xtrade.working_filled()
                return self.xtrade.status
        elif (self.xtrade.status == trade.TradeStatus.Ready) and (self.next_timer < self.agent.tick_id):
            self.xtrade.working_vol =  min(self.max_vol, abs(self.xtrade.remaining_vol)) * direction
            self.xtrade.remaining_vol -= self.xtrade.working_vol
            next_inst = self.xtrade.instIDs[self.inst_rank[0]] 
            self.xtrade.order_dict[next_inst] = []
            next_vol = self.xtrade.units[self.inst_rank[0]] * self.xtrade.working_vol
            inst_obj = self.agent.instruments[next_inst]
            next_price = inst_obj.shift_price(next_vol, self.tick_num) if next_vol > 0 else inst_obj.shift_price(next_vol, self.tick_num)
        elif status == trade.TradeStatus.Cancelled:
            self.on_partial_cancel()
            return status
        if next_vol != 0:
            gway = self.agent.gateway_map(self.instIDs[0])
            new_orders = gway.book_order(next_inst, next_vol, self.price_type, next_price, trade_ref = self.xtrade.id, order_num = self.order_num)
            self.xtrade.order_dict[next_inst] += new_orders
            self.xtrade.status = trade.TradeStatus.OrderSent
            self.next_timer += self.timer_period
            status = trade.TradeStatus.OrderSent
        return status
    
    def on_partial_cancel(self):
        direction = sign(self.xtrade.vol)
        fillvol = min([int(abs(filled/unit)) for (filled, unit) in zip(self.xtrade.order_filled, self.xtrade.units)]) * direction
        price_filled = [sum([o.filled_price * o.filled_vol for o in self.xtrade.order_dict[instID]])/filled \
                                            for instID, filled in zip(self.xtrade.instIDs, self.order_filled)]
        leftvol = self.xtrade.order_filled
        if fillvol != 0:
            leftvol = [ (filled - abs(unit * fillvol))*sign(unit*direction) for (filled, unit) in zip(leftvol, self.xtrade.units)]
            self.xtrade.working_vol = 0
            self.xtrade.order_dict = {}
            self.xtrade.order_filled = []
            self.xtrade.status = trade.TradeStatus.Done
            working_price = self.xtrade.underlying.price(prices=price_filled)
            self.xtrade.on_trade(working_price, fillvol)            
        for instID, vol, p in zip(self.xtrade.instIDs, leftvol, price_filled):
            if vol != 0:
                pair = (instID, vol, p)
                self.unwind(pair)
