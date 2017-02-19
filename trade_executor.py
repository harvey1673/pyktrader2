#-*- coding:utf-8 -*-
import logging
from base import *
import itertools
from misc import *
import datetime
import trade
import order

class ExecAlgoBase(object):
    def __init__(self, xtrade, stop_price = None, max_vol = 20, inst_order = None):
        self.xtrade = xtrade
        if inst_order == None:
            self.inst_order = range(len(xtrade.instIDs))
        else:
            self.inst_order = inst_order
        self.instIDs = [xtrade.instIDs[seq] for seq in self.inst_order]
        self.units = [xtrade.units[seq] for seq in self.inst_order]
        self.order_filled = []
        self.max_vol = max_vol
        self.stop_price = stop_price
        self.set_agent(xtrade.agent)

    def set_agent(self, agent):
        self.agent = agent
        if self.agent!= None:
            self.inst_objs = [ self.agent.instruments[instID] for instID in self.instIDs]
        else:
            self.inst_objs = [None] * len(self.instIDs)

    def unwind(self, pair):
        strat = self.agent.strategies[self.xtrade.strategy]
        strat.add_unwind(pair, book = self.xtrade.book)

    def on_partial_cancel(self):
        pass

    def execute(self):
        pass

    def calc_filled_price(self, order_dict):
        filled_prices = []
        for instID in self.instIDs:
            if instID in order_dict:
                filled_prices.append(sum([o.filled_price * o.filled_volume for o in order_dict[instID]]) \
                                     /sum([o.filled_volume for o in order_dict[instID]]))
            else:
                filled_prices.append(0.0)
        if len(self.instIDs) == 1:
            return filled_prices[0]
        else:
            filled_prices = [filled_prices[i] for i in self.inst_order]
            return self.xtrade.underlying.price(prices=filled_prices)

class ExecAlgo1DFixT(ExecAlgoBase):
    def __init__(self, xtrade, stop_price = None, max_vol = 20, time_period = 100, price_type = OPT_LIMIT_ORDER, \
                 tick_num = 1, order_type = '', inst_order = None):
        super(ExecAlgo1DFixT, self).__init__(xtrade, stop_price = stop_price, max_vol = max_vol, inst_order = inst_order)
        if order_type in ['SP', 'SPD', 'SPC'] and len(xtrade.instIDs) > 1:
            self.instIDs = [order_type + ' ' + '&'.join(xtrade.instIDs)]
            self.units = [1]
            self.book_func = 'book_spd_orders'
            self.book_args = {}
        elif len(xtrade.instIDs) == 1:
            self.instIDs = xtrade.instIDs
            self.units = [1]
            self.book_func = 'book_order'
            self.book_args = {'order_num': 3}
        else:
            print "error on ExecAlgo1DFixT for asset %s" % xtrade.instIDs
        self.inst_objs = [self.xtrade.underlying]
        self.timer_period = time_period
        self.next_timer = self.agent.tick_id
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
            for iorder in self.xtrade.order_dict[self.instIDs[0]]:
                if not iorder.is_closed():
                    self.agent.cancel_order(iorder)
                    cancel_flag = True
        if stop_flag:
            status = self.xtrade.status = trade.TradeStatus.Cancelled
        if cancel_flag:
            return status
        if status == trade.TradeStatus.Cancelled:
            self.on_partial_cancel()
            return status
        if (self.xtrade.status == trade.TradeStatus.Ready) and (self.next_timer < self.agent.tick_id):
            self.xtrade.working_vol =  min(self.max_vol, abs(self.xtrade.remaining_vol)) * direction
            self.xtrade.remaining_vol -= self.xtrade.working_vol
            self.xtrade.order_dict[self.instIDs[0]] = []
            next_vol = self.units[0] * self.xtrade.working_vol
            inst_obj = self.xtrade.underlying
            next_price = inst_obj.shift_price(next_vol, self.tick_num) if next_vol > 0 else inst_obj.shift_price(next_vol, self.tick_num)
        elif status == trade.TradeStatus.Cancelled:
            self.on_partial_cancel()
            return status
        elif status == trade.TradeStatus.PFilled:
            next_vol = self.xtrade.working_vol - self.order_filled[0]*sign(self.xtrade.working_vol)
            traded_prices = [iorder.filled_price for iorder in reversed(self.xtrade.order_dict[self.instIDs[0]]) if
                            iorder.filled_vol > 0]
            last_price = traded_prices[0] if len(traded_prices) > 0 else 0
            next_price = max(last_price, self.xtrade.underlying.shift_price(next_vol, self.tick_num)) if next_vol > 0 \
                                else min(last_price, self.xtrade.underlying.shift_price(next_vol, self.tick_num))
        if next_vol != 0:
            gway = self.agent.gateway_map(self.instIDs[0])
            new_orders = getattr(gway, self.book_func)(self.instIDs[0], next_vol, self.price_type, next_price, trade_ref = self.xtrade.id, **self.book_args)
            self.xtrade.order_dict[self.instIDs[0]] += new_orders
            self.next_timer += self.timer_period
            status = self.xtrade.status = trade.TradeStatus.OrderSent
        return status
    
    def on_partial_cancel(self):
        curr_vol = self.order_filled[0]
        self.xtrade.working_vol = 0
        if curr_vol != 0 :
            curr_p = sum([iorder.filled_price * iorder.filled_vol for iorder in self.xtrade.order_dict[self.instIDs[0]]]) / curr_vol
            self.xtrade.on_trade(curr_p, curr_vol)
        self.cancel()
        
class ExecAlgoFixTimer(ExecAlgoBase):
    '''send out order by fixed period, cancel the trade when hit the stop price '''
    def __init__(self, xtrade, stop_price = None, max_vol = 20, time_period = 600, price_type = OPT_LIMIT_ORDER, \
                       order_offset = True, inst_order = None, tick_num = 1):
        super(ExecAlgoFixTimer, self).__init__(xtrade, stop_price = stop_price, max_vol = max_vol, inst_order = inst_order)
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
            for instID in self.xtrade.order_dict:
                for iorder in self.xtrade.order_dict[instID]:
                    if not iorder.is_closed():
                        self.agent.cancel_order(iorder)
                        cancel_flag = True
        if stop_flag:
            status = self.xtrade.status = trade.TradeStatus.Cancelled
        if cancel_flag:
            return status
        if status == trade.TradeStatus.Cancelled:
            self.on_partial_cancel()
            return status
        next_inst = ''
        next_vol = 0
        next_price = 0
        if status == trade.TradeStatus.PFilled:
            for instID, unit, ofilled, inst_obj in zip(self.instIDs, self.units, self.order_filled, self.inst_objs):
                unfilled = abs(self.xtrade.working_vol * unit) - ofilled
                if unfilled > 0:
                    next_inst = instID
                    next_vol = unfilled * sign(self.xtrade.working_vol * unit)
                    traded_prices = [ iorder.filled_price for iorder in reversed(self.xtrade.order_dict[instID]) if iorder.filled_vol > 0 ]
                    last_price = traded_prices[0] if len(traded_prices) > 0 else 0
                    next_price = max(last_price, inst_obj.shift_price(next_vol, self.tick_num)) if next_vol > 0 \
                                        else min(last_price, inst_obj.shift_price(next_vol, self.tick_num))
                    break
            if next_vol == 0:
                self.agent.logger("something wrong with trade status = PFilled, while no actually no unfilled volume")
                return self.xtrade.status
        elif (self.xtrade.status == trade.TradeStatus.Ready) and (self.next_timer < self.agent.tick_id):
            self.xtrade.working_vol =  min(self.max_vol, abs(self.xtrade.remaining_vol)) * direction
            self.xtrade.remaining_vol -= self.xtrade.working_vol
            next_inst = self.instIDs[0]
            self.xtrade.order_dict[next_inst] = []
            next_vol = self.units[0] * self.xtrade.working_vol
            next_price = self.inst_objs[0].shift_price(next_vol, self.tick_num) if next_vol > 0 \
                                        else self.inst_objs[0].shift_price(next_vol, self.tick_num)
        elif status == trade.TradeStatus.Cancelled:
            self.on_partial_cancel()
        if next_vol != 0:
            gway = self.agent.gateway_map(next_inst)
            new_orders = gway.book_order(next_inst, next_vol, self.price_type, next_price, trade_ref = self.xtrade.id, order_num = self.order_num)
            self.xtrade.order_dict[next_inst] += new_orders
            self.next_timer += self.timer_period
            status = self.xtrade.status = trade.TradeStatus.OrderSent
        return status
    
    def on_partial_cancel(self):
        direction = sign(self.xtrade.vol)
        seqs = sorted(range(len(self.inst_order)), key=lambda k: self.inst_order[k])
        order_filled = [self.order_filled[seq] for seq in seqs]
        fillvol = min([int(abs(filled/unit)) for (filled, unit) in zip(order_filled, self.xtrade.units)]) * direction
        price_filled = [sum([o.filled_price * o.filled_vol for o in self.xtrade.order_dict[instID]])/filled \
                                            for instID, filled in zip(self.xtrade.instIDs, order_filled)]
        if fillvol != 0:
            leftvol = [ (filled - abs(unit * fillvol)) * sign(unit*direction) for (filled, unit) in zip(order_filled, self.xtrade.units)]
            self.xtrade.working_vol = 0
            self.xtrade.order_dict = {}
            self.order_filled = []
            self.xtrade.status = trade.TradeStatus.Done
            working_price = self.xtrade.underlying.price(prices=price_filled)
            self.xtrade.on_trade(working_price, fillvol)            
        for instID, vol, p in zip(self.xtrade.instIDs, leftvol, price_filled):
            if vol != 0:
                pair = (instID, vol, p)
                self.unwind(pair)