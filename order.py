#-*- coding:utf-8 -*-
import logging
from base import *
from misc import *
import itertools
import datetime
import csv
import json
import os.path
from trade import *

class OrderStatus:
    Waiting, Ready, Sent, Done, Cancelled = range(5)

Alive_Order_Status = [OrderStatus.Waiting, OrderStatus.Ready, OrderStatus.Sent]

####下单
class Order(object):
    id_generator = itertools.count(int(datetime.datetime.strftime(datetime.datetime.now(),'%d%H%M%S')))
    def __init__(self, **kwargs):
        self.instrument = kwargs['instID']
        self.exchange = kwargs.get('exchange', '')
        self.type = self.__class__.__name__
        self.instIDs = kwargs.get('instIDs', [self.instrument])
        self.units = kwargs.get('units', [1])
        self.limit_price = kwargs.get('limit_price', 0.0) #开仓基准价
        self.start_tick  = kwargs.get('start_tick', 0)
        self.order_ref = kwargs.get('order_ref', next(self.id_generator))
        self.local_id  = kwargs.get('local_id', self.order_ref)
        self.sys_id = kwargs.get('sys_id', '')
        self.trade_ref = kwargs.get('trade_ref', 0)
        self.direction = kwargs.get('direction', ORDER_BUY) # ORDER_BUY, ORDER_SELL
        self.action_type = kwargs.get('action_type', OF_OPEN) # OF_CLOSE_TDAY, OF_CLOSE, OF_OPEN
        self.price_type = kwargs['price_type']
        self.volume = kwargs['volume'] #目标成交手数,锁定总数
        self.filled_volume = kwargs.get('filled_volume', 0)  #实际成交手数
        self.filled_price  = kwargs.get('filled_price', 0.0)
        self.cancelled_volume = kwargs.get('cancelled_volume', 0)
        self.filled_orders = kwargs.get('filled_orders', {})
        self.positions = []
        self.status = kwargs.get('status', OrderStatus.Ready)
        self.gateway = None

    def set_gateway(self, gateway):
        self.gateway = gateway
        self.positions = [ self.gateway.positions[inst] for inst in self.instIDs]
        self.exchange = gateway.agent.instruments[self.instIDs[0]].exchange

    def recalc_pos(self):
        for pos in self.positions:
            pos.re_calc()

    def add_pos(self):
        for pos in self.positions:
            pos.orders.append(self)
            
    def remove_pos(self):
        for pos in self.positions:
            pos.orders.remove(self)

    def on_trade(self, price, volume, trade_id):
        ''' 返回是否完全成交
        '''
        if self.status == OrderStatus.Done:
            return True
        id_key = str(trade_id)
        if id_key in self.filled_orders:
            return False
        self.filled_orders[id_key] = [price, volume]
        self.update()
        if (self.filled_volume == self.volume):
            self.status = OrderStatus.Done
        logging.debug(u'成交纪录:price=%s,volume=%s,filled_vol=%s' % (price,volume,self.filled_volume))
        self.recalc_pos()
        return self.is_closed()

    def update(self):
        self.filled_volume = sum([v for p, v in self.filled_orders.values()])
        self.filled_price = sum([p * v for p, v in self.filled_orders.values()])/self.filled_volume

    def on_order(self, sys_id, price = 0, volume = 0):
        self.sys_id = sys_id
        if volume > self.filled_volume:
            self.filled_price = price
            self.filled_volume = volume
            if self.filled_volume == self.volume:
                self.status = OrderStatus.Done
                self.recalc_pos()
                return True
        return False

    def on_cancel(self):    #已经撤单
        if (self.status != OrderStatus.Cancelled) and (self.volume > self.filled_volume):
            self.status = OrderStatus.Cancelled
            self.cancelled_volume = max(self.volume - self.filled_volume, 0)
            self.volume = self.filled_volume    #不会再有成交回报
            logging.debug(u'撤单记录: OrderRef=%s, instID=%s, volume=%s, filled=%s, cancelled=%s' \
                % (self.order_ref, self.instrument, self.volume, self.filled_volume, self.cancelled_volume))
            self.recalc_pos()

    def is_closed(self): #是否已经完全平仓
        return (self.filled_volume == self.volume) 

    def __unicode__(self):
        return u'Order_A: order_ref = %s, 合约=%s,方向=%s,目标数=%s,开仓数=%s,状态=%s' % (self.order_ref, \
                    self.instrument, u'多' if self.direction==ORDER_BUY else u'空',
                    self.volume, self.filled_volume, self.status, )

    def __str__(self):
        return unicode(self).encode('utf-8')

    def to_json(self):
        return json.dumps(self, skipkeys = True)

class SpreadOrder(Order):
    def __init__(self, **kwargs):
        super(SpreadOrder, self).__init__(**kwargs)
        self.instIDs, self.units = spreadinst2underlying(self.instrument)
        self.sub_orders = []
        for idx, (inst, unit) in enumerate(zip(self.instIDs, self.units)):
            sorder = BaseObject(action_type = self.action_type[idx],
                                   direction = self.direction if unit > 0 else reverse_direction(self.direction),
                                   filled_volume = 0,
                                   volume = abs(unit * self.vol),
                                   filled_price = 0)
            self.sub_orders.append(sorder)

    def add_pos(self):
        for pos, sorder in zip(self.positions, self.sub_orders):
            pos.orders.append(sorder)

    def remove_pos(self):
        for pos, sorder in zip(self.positions, self.sub_orders):
            pos.orders.remove(sorder)        

    def update(self):
        super(SpreadOrder, self).update()
        curr_p = 0
        for pos, sorder, unit in zip(self.positions, self.sub_orders, self.units):
            p = pos.instrument.mid_price
            sorder.filled_volume = self.filled_volume * abs(unit)
            sorder.filled_price = p
            curr_p += p * unit
        self.sub_orders[0].filled_price -= (curr_p - self.filled_price)/self.units[0]
