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

def save_order_list(curr_date, order_dict, file_prefix):
    orders = order_dict.keys()
    if len(order_dict)>1:
        orders.sort()
    order_list = [order_dict[key] for key in orders]
    filename = file_prefix + 'order_' + curr_date.strftime('%y%m%d')+'.csv'
    with open(filename,'wb') as log_file:
        file_writer = csv.writer(log_file, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL);
        
        file_writer.writerow(['order_ref', 'local_id', 'sysID', 'inst', 'volume', 'filledvolume', 'filledprice', 'action_type', 'direction',
                              'price_type','limitprice','order_time', 'status', 'conditionals', 'trade_ref'])

        for order in order_list:
            inst = order.position.instrument.name
            cond = [ str(o.order_ref)+':'+str(order.conditionals[o]) for o in order.conditionals]
            cond_str = ' '.join(cond)
            file_writer.writerow([order.order_ref, order.local_id, order.sys_id, inst, order.volume, order.filled_volume, order.filled_price,
                                  order.action_type, order.direction, order.price_type,
                                  order.limit_price, order.start_tick, order.status, cond_str, order.trade_ref])  
    pass

def load_order_list(curr_date, file_prefix, positions):
    logfile = file_prefix + 'order_' + curr_date.strftime('%y%m%d')+'.csv'
    if not os.path.isfile(logfile):
        return {}
    ref2order = {}
    with open(logfile, 'rb') as f:
        reader = csv.reader(f)
        for idx, row in enumerate(reader):
            if idx > 0:
                inst = row[3]
                pos = positions[inst]
                if ':' in row[13]:
                    cond = dict([ tuple([int(k) for k in n.split(':')]) for n in row[13].split(' ')])
                else:
                    cond = {}
                iorder = Order(pos, float(row[10]), int(row[4]), int(row[11]),
                               row[7], row[8], row[9], cond)
                iorder.sys_id = row[1]
                iorder.local_id = row[2]
                iorder.filled_volume = int(row[5])
                iorder.filled_price = float(row[6])
                iorder.order_ref = int(row[0])
                iorder.trade_ref = int(row[14])
                iorder.status = int(row[12])
                ref2order[iorder.order_ref] = iorder
                pos.add_order(iorder)                
    return ref2order

####下单
class Order(object):
    id_generator = itertools.count(int(datetime.datetime.strftime(datetime.datetime.now(),'%d%H%M%S')))
    def __init__(self,position,limit_price,vol,order_time,action_type,direction, price_type, conditionals={}, trade_ref = 0, gateway = 'CTP'):
        self.position = position
        self.limit_price = limit_price        #开仓基准价
        self.start_tick  = order_time
        self.order_ref = next(self.id_generator)
        self.local_id  = self.order_ref
        ##衍生
        self.instrument = position.instrument
        self.sys_id = ''
        self.trade_ref = trade_ref
        self.direction = direction # ORDER_BUY, ORDER_SELL
        ##操作类型
        self.action_type = action_type # OF_CLOSE_TDAY, OF_CLOSE, OF_OPEN
        self.price_type = price_type
        ##
        self.volume = vol #目标成交手数,锁定总数
        self.filled_volume = 0  #实际成交手数
        self.filled_price  = 0
        self.cancelled_volume = 0
        self.filled_orders = []
        self.conditionals = conditionals
        self.gateway = gateway
        if len(self.conditionals) == 0:
            self.status = OrderStatus.Ready
        else:
            self.status = OrderStatus.Waiting
        #self.close_lock = False #平仓锁定，即已经发出平仓信号

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
        self.position.re_calc()
        return self.filled_volume == self.volume

    def on_order(self, sys_id, price = 0, volume = 0):
        self.sys_id = sys_id
        if volume > 0:
            self.filled_price = price
            self.filled_volume = volume
            if self.filled_volume == self.volume:
                self.status = OrderStatus.Done
                self.position.re_calc()
                return True
        return False

    def on_cancel(self):    #已经撤单
        if self.status != OrderStatus.Cancelled:
            self.status = OrderStatus.Cancelled
            self.cancelled_volume = max(self.volume - self.filled_volume, 0)
            self.volume = self.filled_volume    #不会再有成交回报
            logging.debug(u'撤单记录: OrderRef=%s, instID=%s, volume=%s, filled=%s, cancelled=%s' \
                % (self.order_ref, self.instrument.name, self.volume, self.filled_volume, self.cancelled_volume))
        self.position.re_calc()

    def is_closed(self): #是否已经完全平仓
        return (self.status in [OrderStatus.Cancelled,OrderStatus.Done]) and (self.filled_volume == self.volume)

    #def release_close_lock(self):
    #    logging.info(u'释放平仓锁,order=%s' % self.__str__())
    #    self.close_lock = False

    def __unicode__(self):
        return u'Order_A: 合约=%s,方向=%s,目标数=%s,开仓数=%s,状态=%s' % (self.instrument.name,
                u'多' if self.direction==ORDER_BUY else u'空',
                self.volume,
                self.filled_volume,
                self.status,
            )

    def __str__(self):
        return unicode(self).encode('utf-8')
