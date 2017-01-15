#-*- coding:utf-8 -*-
import logging
from base import *
import itertools
from misc import *
import datetime
import trade
import order

class TradeStatus:
    Pending, OrderSent, PFilled, Done, Cancelled, StratConfirm = range(6)

class XTrade(object):
    # instances = weakref.WeakSet()
    id_generator = itertools.count(int(datetime.datetime.strftime(datetime.datetime.now(), '%d%H%M%S')))

    def __init__(self, instIDs, units, vol, limit_price, price_unit = 1, strategy = "dummy", agent = None ):
        self.id = next(self.id_generator)
        self.instIDs = instIDs
        self.units = units
        self.vol = vol        
        self.filled_vol = [0] * len(instIDs)
        self.filled_price = [0] * len(units)
        self.limit_price = limit_price
        self.price_unit = price_unit
        self.underlying = None
        self.book = "dummy"
        self.agent = agent
        if agent != None:
            self.set_agent(agent)                
        self.status = TradeStatus.Pending
        self.order_dict = dict([(inst, []) for inst in instIDs])
        self.exec_algo = ExecAlgoBase(self, agent)
        
    def set_agent(self, agent):
        self.agent = agent
        self.book = agent.name
        self.underlying = agent.get_underlying(self.instIDs, self.units, self.price_unit)
    
    def set_exec_algo(self, exec_algo):
        self.exec_algo = exec_algo

    def final_price(self):
        if len(self.instIDs) == 1:
            return self.filled_price[0]
        else:
            return self.underlying.price(prices = self.filled_price)

    def update(self):
        pending_orders = []
        if self.status in [TradeStatus.Done, TradeStatus.Cancelled, TradeStatus.StratConfirm]:
            return pending_orders
        elif len(self.order_dict) == 0:
            self.status = TradeStatus.Pending
            return pending_orders
        Done_status = True
        PFill_status = False
        Zero_Volume = True
        volumes = [0] * len(self.instIDs)
        for idx, inst in enumerate(self.instIDs):
            for iorder in self.order_dict[inst]:
                if (iorder.status in [order.OrderStatus.Done, order.OrderStatus.Cancelled]) and (
                    len(iorder.conditionals) == 0):
                    continue
                if len(iorder.conditionals) == 1 and (order.OrderStatus.Cancelled in iorder.conditionals.values()):
                    sorder = iorder.conditionals.keys()[0]
                    if sorder.status == order.OrderStatus.Cancelled and iorder.status == order.OrderStatus.Waiting:
                        iorder.volume = sorder.cancelled_volume
                        iorder.status = order.OrderStatus.Ready
                        iorder.conditionals = {}
                        pending_orders.append(iorder.order_ref)
                        logging.debug('order %s is ready after %s is canceld, the remaining volume is %s' \
                                      % (iorder.order_ref, sorder.order_ref, iorder.volume))
                elif len(iorder.conditionals) > 0:
                    for o in iorder.conditionals:
                        if ((o.status == order.OrderStatus.Cancelled) and (
                            iorder.conditionals[o] == order.OrderStatus.Done)) \
                                or ((o.status == order.OrderStatus.Done) and (
                                    iorder.conditionals[o] == order.OrderStatus.Cancelled)):
                            iorder.on_cancel()
                            iorder.conditions = {}
                            break
                        elif (o.status != iorder.conditionals[o]):
                            break
                    else:
                        logging.debug('conditions for order %s are met, changing status to be ready' % iorder.order_ref)
                        iorder.status = order.OrderStatus.Ready
                        pending_orders.append(iorder.order_ref)
                        iorder.conditionals = {}
            self.filled_vol[idx] = sum([iorder.filled_volume for iorder in self.order_dict[inst]])
            if self.filled_vol[idx] > 0:
                self.filled_price[idx] = sum(
                    [iorder.filled_volume * iorder.filled_price for iorder in self.order_dict[inst]]) / self.filled_vol[
                                             idx]
            volumes[idx] = sum([iorder.volume for iorder in self.order_dict[inst]])
            if volumes[idx] > 0:
                Zero_Volume = False
            if self.filled_vol[idx] < volumes[idx]:
                Done_status = False
            if self.filled_vol[idx] > 0:
                PFill_status = True
        if Zero_Volume:
            self.status = TradeStatus.Cancelled
        elif Done_status:
            self.status = TradeStatus.Done
        elif PFill_status:
            self.status = TradeStatus.PFilled
        return pending_orders

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

    def process(self):
        if self.xtrade.status == TradeStatus.Pending:
            pass
        pass

