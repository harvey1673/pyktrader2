#-*- coding:utf-8 -*-
import logging
from base import *
from misc import *
import itertools
import datetime
import csv
import os.path
import order

class ETradeStatus:
    Pending, Processed, PFilled, Done, Cancelled, StratConfirm = range(6)

def save_trade_list(curr_date, trade_list, file_prefix):
    filename = file_prefix + 'trade_' + curr_date.strftime('%y%m%d')+'.csv'
    with open(filename,'wb') as log_file:
        file_writer = csv.writer(log_file, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL);
        
        file_writer.writerow(['id', 'insts', 'volumes', 'filledvol', 'filledprice', 'otypes', 'slipticks',
                              'order_dict','limitprice', 'validtime',
                              'strategy','book','status', 'price_unit', 'conv_f'])
        for trade in trade_list.values():
            insts = ' '.join(trade.instIDs)
            volumes = ' '.join([str(i) for i in trade.volumes])
            filled_vol = ' '.join([str(i) for i in trade.filled_vol])
            filled_price = ' '.join([str(i) for i in trade.filled_price])
            otypes = ' '.join([str(i) for i in trade.order_types])
            slip_ticks = ' '.join([str(i) for i in trade.slip_ticks])
            cfactors = ' '.join([str(i) for i in trade.conv_f])
            if len(trade.order_dict)>0:
                order_dict = ' '.join([inst +':'+'_'.join([str(o.order_ref) for o in trade.order_dict[inst]]) 
                                    for inst in trade.order_dict])
            else:
                order_dict = ''
                                
            file_writer.writerow([trade.id, insts, volumes, filled_vol, filled_price, otypes, slip_ticks,
                                  order_dict, trade.limit_price, trade.valid_time,
                                  trade.strategy, trade.book, trade.status, trade.price_unit, cfactors])

def load_trade_list(curr_date, file_prefix):
    logfile = file_prefix + 'trade_' + curr_date.strftime('%y%m%d')+'.csv'
    if not os.path.isfile(logfile):
        return {}

    trade_dict = {} 
    with open(logfile, 'rb') as f:
        reader = csv.reader(f)
        for idx, row in enumerate(reader):
            if idx > 0:
                instIDs = row[1].split(' ')
                volumes = [ int(n) for n in row[2].split(' ')]
                filled_vol = [ int(n) for n in row[3].split(' ')]
                filled_price = [ float(n) for n in row[4].split(' ')]
                otypes = [ int(n) for n in row[5].split(' ')]
                ticks = [ int(n) for n in row[6].split(' ')]
                if ':' in row[7]:
                    order_dict =  dict([tuple(s.split(':')) for s in row[7].split(' ')])
                    for inst in order_dict:
                        if len(order_dict[inst])>0:
                            order_dict[inst] = [int(o_id) for o_id in order_dict[inst].split('_')]
                        else:
                            order_dict[inst] = []
                else:
                    order_dict = {}
                limit_price = float(row[8])
                valid_time = int(row[9])
                strategy = row[10]
                book = row[11]
                price_unit = float(row[13])
                conv_factor = [ int(n) for n in row[14].split(' ')]
                etrade = ETrade(instIDs, volumes, otypes, limit_price, ticks, valid_time, strategy, book, price_unit, conv_factor)
                etrade.id = int(row[0])
                etrade.status = int(row[12])
                etrade.order_dict = order_dict
                etrade.filled_vol = filled_vol 
                etrade.filled_price = filled_price 
                trade_dict[etrade.id] = etrade    
    return trade_dict
    
class ETrade(object):
    #instances = weakref.WeakSet()
    id_generator = itertools.count(int(datetime.datetime.strftime(datetime.datetime.now(),'%d%H%M%S')))

    #@classmethod
    #def get_instances(cls):
    #    return list(ETrade.instances)
            
    def __init__(self, instIDs, volumes, otypes, limit_price, ticks, valid_time, strategy, book, price_unit = 1, conv_factor = []):
        self.id = next(self.id_generator)
        self.instIDs = instIDs
        self.volumes = volumes
        self.filled_vol = [0]*len(volumes)
        self.filled_price = [0]*len(volumes)
        self.order_types = otypes
        self.slip_ticks  = ticks
        self.limit_price = limit_price
        self.price_unit = price_unit
        self.valid_time = valid_time
        self.strategy = strategy
        self.book = book
        self.status = ETradeStatus.Pending
        self.conv_f = [1] * len(instIDs)
        if len(conv_factor) > 0:
            self.conv_f = conv_factor
        self.order_dict = {}
        #ETrade.instances.add(self)

    def final_price(self):
        return sum([ v*p*cf for (v,p,cf) in zip(self.filled_vol, self.filled_price, self.conv_f)])/self.price_unit
    
    def update(self):
        pending_orders = []
        if self.status in [ETradeStatus.Done, ETradeStatus.Cancelled, ETradeStatus.StratConfirm]:
            return pending_orders
        elif len(self.order_dict) == 0:
            self.status = ETradeStatus.Pending
            return pending_orders
        Done_status = True
        PFill_status = False
        Zero_Volume = True
        volumes = [0] * len(self.instIDs)
        for idx, inst in enumerate(self.instIDs):
            for iorder in self.order_dict[inst]:
                if (iorder.status in [order.OrderStatus.Done, order.OrderStatus.Cancelled]) and (len(iorder.conditionals) == 0):
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
                elif len(iorder.conditionals)> 0:
                    for o in iorder.conditionals:
                        if ((o.status == order.OrderStatus.Cancelled) and (iorder.conditionals[o] == order.OrderStatus.Done)) \
                            or ((o.status == order.OrderStatus.Done) and (iorder.conditionals[o] == order.OrderStatus.Cancelled)):
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
                self.filled_price[idx] = sum([iorder.filled_volume*iorder.filled_price for iorder in self.order_dict[inst]])/self.filled_vol[idx]
            volumes[idx] = sum([iorder.volume for iorder in self.order_dict[inst]])                    
            if volumes[idx] > 0:
                Zero_Volume = False
            if self.filled_vol[idx] < volumes[idx]:
                Done_status = False
            if self.filled_vol[idx] > 0:
                PFill_status = True                            
        if Zero_Volume:
            self.status = ETradeStatus.Cancelled
        elif Done_status:
            self.status = ETradeStatus.Done
        elif PFill_status:
            self.status = ETradeStatus.PFilled
        return pending_orders


class XTrade(object):
    # instances = weakref.WeakSet()
    id_generator = itertools.count(int(datetime.datetime.strftime(datetime.datetime.now(), '%d%H%M%S')))
    # @classmethod
    # def get_instances(cls):
    #    return list(ETrade.instances)

    def __init__(self, instIDs, vols, pos, limit_price, strategy, book, price_unit=1, conv_factor=[]):
        self.id = next(self.id_generator)
        self.instIDs = instIDs
        self.volumes = vols
        self.filled_vol = [0] * len(vols)
        self.filled_price = [0] * len(vols)
        self.limit_price = limit_price
        self.price_unit = price_unit
        self.strategy = strategy
        self.book = book
        self.status = ETradeStatus.Pending
        self.conv_f = [1] * len(instIDs)
        if len(conv_factor) > 0:
            self.conv_f = conv_factor
        self.order_dict = {}
        # ETrade.instances.add(self)

    def final_price(self):
        return sum(
            [v * p * cf for (v, p, cf) in zip(self.filled_vol, self.filled_price, self.conv_f)]) / self.price_unit

    def update(self):
        pending_orders = []
        if self.status in [ETradeStatus.Done, ETradeStatus.Cancelled, ETradeStatus.StratConfirm]:
            return pending_orders
        elif len(self.order_dict) == 0:
            self.status = ETradeStatus.Pending
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
            self.status = ETradeStatus.Cancelled
        elif Done_status:
            self.status = ETradeStatus.Done
        elif PFill_status:
            self.status = ETradeStatus.PFilled
        return pending_orders