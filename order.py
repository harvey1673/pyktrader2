#-*- coding:utf-8 -*-
import logging
from base import *
from misc import *
import itertools
import datetime
import csv
import os.path
from trade import *

class OrderStatus:
    Waiting, Ready, Sent, Done, Cancelled = range(5)

####下单
class Order(object):
    id_generator = itertools.count(int(datetime.datetime.strftime(datetime.datetime.now(),'%d%H%M%S')))
    def __init__(self, instID, limit_price, vol, order_time, action_type, direction, price_type, trade_ref = 0, gateway = None):
        self.instrument = instID
        self.instIDs = [instID]
        self.units = [1]
        self.limit_price = limit_price        #开仓基准价
        self.start_tick  = order_time
        self.order_ref = next(self.id_generator)
        self.local_id  = self.order_ref
        self.sys_id = ''
        self.trade_ref = trade_ref
        self.direction = direction # ORDER_BUY, ORDER_SELL
        self.action_type = action_type # OF_CLOSE_TDAY, OF_CLOSE, OF_OPEN
        self.price_type = price_type
        self.volume = vol #目标成交手数,锁定总数
        self.filled_volume = 0  #实际成交手数
        self.filled_price  = 0
        self.cancelled_volume = 0
        self.filled_orders = []
        self.gateway = gateway
        self.positions = []
        self.status = OrderStatus.Ready
        if gateway != None:
            self.set_gateway(gateway)

    def set_gateway(self, gateway):
        self.gateway = gateway
        self.positions = [ self.gateway.positions[inst] for inst in self.instIDs]
        self.add_to_positions()

    def add_to_position(self):
        self.positions[0].orders.append(self)

    def recalc_pos(self):
        for pos in self.positions:
            pos.re_calc()

    def on_trade(self, price, volume, trade_id):
        ''' 返回是否完全成交
        '''
        if self.status == OrderStatus.Done:
            return True
        if trade_id in [o.trade_id for o in self.filled_orders]:
            return False
        self.filled_orders.append(BaseObject(price = price, volume = volume, trade_id = trade_id))
        self.filled_volume = sum([o.volume for o in self.filled_orders])
        self.filled_price = sum([o.volume*o.price for o in self.filled_orders])/self.filled_volume
        if self.filled_volume > self.volume:
            self.filled_volume = self.volume
            self.status = OrderStatus.Done
            logging.warning(u'a new trade confirm exceeds the order volume price=%s, filled_vol=%s, order_vol =%s' % \
                                (price, volume, self.volume))
        elif (self.filled_volume == self.volume) and (self.volume>0):
            self.status = OrderStatus.Done
        logging.debug(u'成交纪录:price=%s,volume=%s,filled_vol=%s, is_closed=%s' % (price,volume,self.filled_volume,self.is_closed()))
        self.recalc_pos()
        return self.filled_volume == self.volume

    def on_order(self, sys_id, price = 0, volume = 0):
        self.sys_id = sys_id
        if volume > 0:
            self.filled_price = price
            self.filled_volume = volume
            if self.filled_volume == self.volume:
                self.status = OrderStatus.Done
                self.recalc_pos()
                return True
        return False

    def on_cancel(self):    #已经撤单
        if self.status != OrderStatus.Cancelled:
            self.status = OrderStatus.Cancelled
            self.cancelled_volume = max(self.volume - self.filled_volume, 0)
            self.volume = self.filled_volume    #不会再有成交回报
            logging.debug(u'撤单记录: OrderRef=%s, instID=%s, volume=%s, filled=%s, cancelled=%s' \
                % (self.order_ref, self.instrument.name, self.volume, self.filled_volume, self.cancelled_volume))
        self.recalc_pos()

    def is_closed(self): #是否已经完全平仓
        return (self.status in [OrderStatus.Cancelled,OrderStatus.Done]) and (self.filled_volume == self.volume)

    def __unicode__(self):
        return u'Order_A: 合约=%s,方向=%s,目标数=%s,开仓数=%s,状态=%s' % (self.instrument.name,
                u'多' if self.direction==ORDER_BUY else u'空',
                self.volume,
                self.filled_volume,
                self.status,
            )

    def __str__(self):
        return unicode(self).encode('utf-8')

class SpreadOrder(Order):
    def __init__(self, instID, limit_price, vol, order_time, action_type, direction, price_type, trade_ref=0, gateway=None):
        super(SpreadOrder, self).__init__(instID, limit_price, vol, order_time, action_type, direction, price_type, trade_ref)
        self.instIDs, self.units = spreadinst2underlying(instID)
        if gateway != None:
            self.set_gateway(gateway)

    def recalc_pos(self):
        super(SpreadOrder, self).recalc_pos()

    def add_to_postions(self):
        pass

