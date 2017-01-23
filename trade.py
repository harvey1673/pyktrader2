#-*- coding:utf-8 -*-
import logging
from base import *
from misc import *
import itertools
import datetime
import csv
import os.path
import order
from trade_executor import *

class ETradeStatus:
    Pending, Processed, PFilled, Done, Cancelled, StratConfirm = range(6)

class TradeStatus:
    Pending, Ready, OrderSent, PFilled, Done, Cancelled, StratConfirm, Suspended = range(8)

Alive_Trade_Status = [TradeStatus.Pending, TradeStatus.Ready, TradeStatus.OrderSent, TradeStatus.PFilled]

class TradeManager(object):
    def __init__(self, agent):
        self.agent = agent
        self.tradebook = {}
        self.ref2trade = {}

    def initialize(self):
        self.ref2trade = self.load_trade_list(self.agent.scur_day, self.agent.folder)
        for trade_id in self.ref2trade:
            xtrade = self.ref2trade[trade_id]
            orderdict = xtrade.order_dict
            for inst in orderdict:
                xtrade.order_dict[inst] = [ self.agent.ref2order[order_ref] for order_ref in orderdict[inst] ]
            xtrade.update()

    def get_trade(self, trade_id):
        return self.ref2trade[trade_id]

    def get_trades_by_strat(self, strat_name):
        return [xtrade for xtrade in self.ref2trade.values() if xtrade.strategy == strat_name]

    def save_pfill_trades(self):
        pfilled_dict = {}
        for trade_id in self.ref2trade:
            xtrade = self.ref2trade[trade_id]
            xtrade.update()
            if xtrade.status == TradeStatus.Pending or xtrade.status == TradeStatus.OrderSent:
                xtrade.status = TradeStatus.Cancelled
                strat = self.agent.strategies[xtrade.strategy]
                strat.on_trade(xtrade)
            elif xtrade.status == TradeStatus.PFilled:
                xtrade.status = TradeStatus.Cancelled
                self.agent.logger.warning('Still partially filled after close. trade id= %s' % trade_id)
                pfilled_dict[trade_id] = xtrade
        if len(pfilled_dict)>0:
            file_prefix = self.agent.folder + 'PFILLED_'
            self.save_trade_list(self.agent.scur_day, pfilled_dict, file_prefix)

    def add_trade(self, xtrade):
        if xtrade.id not in self.ref2trade:
            self.ref2trade[xtrade.id] = xtrade
        if xtrade.status in Alive_Trade_Status:
            key = xtrade.underlying.name
            self.working_trades[key].append(xtrade)

    def remove_trade(self, xtrade):
        key = xtrade.name
        self.working_trades[key].remove(xtrade, None)

    def process_trades(self, instID):
        pass

    def match_trade(self):
        pass

    def save_trade_list(self, curr_date, trade_list, file_prefix):
        filename = file_prefix + 'trade_' + curr_date.strftime('%y%m%d')+'.csv'
        with open(filename,'wb') as log_file:
            file_writer = csv.writer(log_file, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL);
            file_writer.writerow(['id', 'insts', 'units', 'price_unit', 'vol', 'limitprice',
                                  'filledvol', 'filledprice', 'order_dict', 'aggressive',
                                  'start_time', 'end_time', 'strategy','book', 'status'])
            for xtrade in trade_list.values():
                insts = ' '.join(xtrade.instIDs)
                units = ' '.join([str(i) for i in xtrade.units])
                if len(xtrade.order_dict)>0:
                    order_dict = ' '.join([inst +':'+'_'.join([str(o.order_ref) for o in trade.order_dict[inst]])
                                        for inst in trade.order_dict])
                else:
                    order_dict = ''
                file_writer.writerow([trade.id, insts, units, xtrade.price_unit, xtrade.vol, xtrade.limit_price,
                                      xtrade.filled_vol, xtrade.filled_price, order_dict, xtrade.aggressive_level,
                                      xtrade.start_time, xtrade.end_time, xtrade.strategy, xtrade.book, xtrade.status])

    def load_trade_list(self, curr_date, file_prefix):
        logfile = file_prefix + 'trade_' + curr_date.strftime('%y%m%d')+'.csv'
        if not os.path.isfile(logfile):
            return {}
        trade_dict = {}
        with open(logfile, 'rb') as f:
            reader = csv.reader(f)
            for idx, row in enumerate(reader):
                if idx > 0:
                    instIDs = row[1].split(' ')
                    units = [ int(n) for n in row[2].split(' ')]
                    price_unit = float(row[3])
                    vol = int(row[4])
                    limit_price = float(row[5])
                    filled_vol = int(row[6])
                    filled_price = float(row[7])
                    aggressiveness = float(row[9])
                    start_time = int(row[10])
                    end_time = int(row[11])
                    order_dict = {}
                    if ':' in row[8]:
                        str_dict =  dict([tuple(s.split(':')) for s in row[8].split(' ')])
                        for inst in str_dict:
                            if len(order_dict[inst])>0:
                                order_dict[inst] = [int(o_id) for o_id in str_dict[inst].split('_')]
                    strategy = row[10]
                    book = row[11]
                    xtrade = XTrade(instIDs, units, vol, limit_price, price_unit = price_unit, strategy = strategy, book = book, \
                                    agent = self.agent, start_time = start_time, end_time = end_time, aggressiveness = aggressiveness)
                    xtrade.id = int(row[0])
                    xtrade.status = int(row[12])
                    xtrade.order_dict = order_dict
                    xtrade.filled_vol = filled_vol
                    xtrade.filled_price = filled_price
                    xtrade.refresh_status()
                    trade_dict[xtrade.id] = xtrade
        return trade_dict

class XTrade(object):
    # instances = weakref.WeakSet()
    id_generator = itertools.count(int(datetime.datetime.strftime(datetime.datetime.now(), '%d%H%M%S')))
    def __init__(self, instIDs, units, vol, limit_price, price_unit=1, strategy="dummy", book="0", \
                 agent=None, start_time = 300000, end_time = 2115000, aggressiveness = 1):
        self.id = next(self.id_generator)
        self.instIDs = instIDs
        self.units = units
        self.vol = vol
        self.filled_vol = 0
        self.filled_price = 0
        self.limit_price = limit_price
        self.price_unit = price_unit
        self.underlying = None
        self.strategy = strategy
        self.book = book
        self.agent = agent
        self.status = TradeStatus.Pending
        self.order_dict = {}
        self.order_vol = []
        self.working_vol = 0
        self.aggressive_level = aggressiveness
        self.start_time = start_time
        self.end_time = end_time
        self.exec_algo = ExecAlgoBase(self, agent)
        if agent != None:
            self.set_agent(agent)

    def set_agent(self, agent):
        self.agent = agent
        self.underlying = agent.get_underlying(self.instIDs, self.units, self.price_unit)

    def set_exec_algo(self, exec_algo):
        self.exec_algo = exec_algo

    def final_price(self):
        if len(self.instIDs) == 1:
            return self.filled_price[0]
        else:
            return self.underlying.price(prices=self.filled_price)

    def refresh_status(self):
        if self.status in [TradeStatus.StratConfirm, TradeStatus.Done, TradeStatus.Cancelled]:
            return
        if self.filled_vol == self.vol:
            self.status = TradeStatus.Done
            self.order_dict = {}
            self.working_vol = 0
        elif (self.filled_vol > 0) and len(self.order_dict) == 0:
            self.status = TradeStatus.PFilled
            self.order_vol = []
        elif len(self.order_dict) > 0:
            self.order_vol = [sum([self.agent.ref2order[oref].filled_volume for oref in self.order_dict[instID]]) \
                                    if instID in self.order_dict else 0 for instID in self.instIDs]
            remain_vol = sum([self.working_vol * abs(u) - v for u, v in zip(self.units, self.order_vol)])
            if remain_vol > 0:
                self.status = TradeStatus.OrderSent
        else:
            self.status = TradeStatus.Pending
            self.order_vol = []
            self.working_vol = 0

    def execute(self):
        self.exec_algo.process()
