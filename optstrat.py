# -*- coding: utf-8 -*-
'''
optstrat.py
Created on Feb 03, 2015
@author: Harvey
'''
import json
import os
import csv
import pyktlib
import mysqlaccess
import trade
import instrument
import pandas as pd
import data_handler as dh
from eventType import *
from eventEngine import Event
from misc import *

class OptionStrategy(object):
    common_params = {'name': 'opt_m', 'products':{'m1705': {201705: [2800, 2850, 2900, 2950, 3000]}, \
                                                  'm1709': {201709: [2800, 2850, 2900, 2950, 3000]}}, \                     
                     'pos_scaler': 1.0, 'daily_close_buffer': 3, 'exec_class': 'ExecAlgo1DFixT', \
                     'is_disabled': True, 'risk_limit': {'pdelta': 100.0, 'pvega': 100.0}, \
                     'risk_bias': {'pdelta': 0.0, 'pvega': 0.0}}
    def __init__(self, config, agent = None):
        self.load_config(config)
        self.underliers = self.products.keys()                
        self.option_dict = self.get_option_dict(self.products)
        self.option_insts = self.option_dict.values()
        self.instIDs = self.underliers + self.option_insts        
        self.underlying = [None] * len(self.instIDs)
        self.expiry_map = {}
        self.inst_map = dict([(instID, i) for i, instID in enumerate(self.instIDs)])
        self.risk_table = dh.DynamicRecArray( \
            dtype = [('name', '|S50'), ('product', '|S50'), \
                    ('under', '|S50'), ('cont_mth', 'i8'), ('otype', '|S50'), \
                    ('strike', 'f8'), ('multiple', 'i8'), ('df', 'f8'), \
                    ('margin_long', 'f8'), ('margin_short', 'f8'), ('under_price', 'f8'), \
                    ('pos_long', 'i8'), ('pos_short', 'i8'), ('out_long', 'i8'), ('out_short', 'i8'), \
                    ('pv', 'f8'), ('delta', 'f8'), ('gamma', 'f8'), ('vega', 'f8'), ('theta', 'f8'), \
                    ('ppv', 'f8'), ('pdelta', 'f8'), ('pgamma', 'f8'), ('pvega', 'f8'), ('ptheta', 'f8')], \
            nlen = len(self.instIDs))
        self.risk_table.data['name'] = self.instIDs
        self.risk_table.data['under'] = self.risk_table.data['name']
        self.risk_table.data['df'] = 1.0
        self.agent = agent
        self.folder = ''
        self.submitted_pos = dict([(inst, []) for inst in self.instIDs])
        self.hedge_config = {'delta_algo': 'ExecAlgo1DFixT', 'delta_args': {'time_period': 50, 'tick_num': 1}, \
                             'vega_algo': 'ExecAlgo1DFixT', 'vega_args': {'time_period': 50, 'tick_num': 1}, }

    def load_config(self, config):
        d = self.__dict__
        for key in self.common_params:
            d[key] = config.get(key, self.common_params[key])

    def save_config(self):
        config = {}
        d = self.__dict__
        for key in self.common_params:
            config[key] = d[key]
        config['assets'] = []
        fname = self.folder + 'config.json'
        with open(fname, 'w') as ofile:
            json.dump(config, ofile)

    def save_state(self):
        filename = self.folder + 'strat_status.csv'
        self.on_log('save state for strat = %s' % self.name, level = logging.DEBUG)
        with open(filename,'wb') as log_file:
            file_writer = csv.writer(log_file, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL);
            for i in range(len(self.risk_table)):
                file_writer.writerow([self.risk_table.data['name'][i], \
                                      self.risk_table.data['pos_long'][i], self.risk_table.data['pos_short'][i], \
                                      self.risk_table.data['out_long'][i], self.risk_table.data['out_short'][i]])
            
    def load_state(self):
        self.on_log('load state for strat = %s' % self.name, level = logging.DEBUG)
        filename = self.folder + 'strat_status.csv'
        if not os.path.isfile(filename):
            return
        with open(filename, 'rb') as f:
            reader = csv.reader(f)
            pos_dict = {}
            for idx, row in enumerate(reader):
                pos_dict[str(row[0])] = {'pos_long': int(row[1]), 'pos_short': int(row[2]), \
                                         'out_long': int(row[3]), 'out_short': int(row[4])}
        for key in ['pos_long', 'pos_short', 'out_long', 'out_short']:
            self.risk_table.data[key] = [ 0 if inst not in pos_dict else pos_dict[inst][key] \
                                          for inst in self.risk_table.data['name']]
    
    def dep_instIDs(self):
        return self.instIDs

    def set_agent(self, agent):
        self.agent = agent
        self.folder = self.agent.folder + self.name + '_'
        self.underlying = [self.agent.instruments[instID] for instID in self.instIDs]   
        for inst in self.underlying:
            if inst.ptype == instrument.ProductType.Option:
               if (inst.underlying, inst.cont_mth) not in self.expiry_map:
                   self.expiry_map[(inst.underlying, inst.cont_mth)] = inst.expiry
        for key in ['product', 'cont_mth', 'multiple']:
            self.risk_table.data[key] = [ getattr(inst, key) for inst in self.underlying ]
        idx = len(self.underliers)
        for key in ['under', 'otype', 'strike', 'pv', 'delta', 'gamma', 'vega', 'theta']:
            self.risk_table.data[key][idx:] = [ getattr(inst, key) for inst in self.underlying[idx:] ]
        for under, inst in zip(self.underliers, self.underlying[:idx]):
            self.risk_table.data['under_price'][self.risk_table.data['under'] == under] = inst.mid_price
        self.register_func_freq()
        self.register_bar_freq()

    def register_func_freq(self):
        pass

    def register_bar_freq(self):
        pass

    def on_log(self, text, level = logging.INFO):
        event = Event(type=EVENT_LOG)
        event.dict['data'] = text
        event.dict['owner'] = "strategy_" + self.name
        event.dict['level'] = level
        self.agent.eventEngine.put(event)
        
    def initialize(self):
        self.load_state()
        idx = len(self.underliers)
        for key in ['pv', 'delta', 'gamma', 'vega', 'theta']:
            self.risk_table.data[key][idx:] = [getattr(inst, key) for inst in self.underlying[idx:]]
        self.update_pos_greeks()
        self.update_margin()
    
    def update_margin(self):
        for key in ['margin_long', 'margin_short']:
            self.risk_table.data[key] = [ inst.calc_margin_amount(ORDER_BUY, price) \
                                          for inst, price in zip(self.underlying, self.risk_table.data['under_price'])]

    def update_pos_greeks(self):
        '''update position greeks according to current positions'''
        keys = ['pv', 'delta', 'gamma', 'vega', 'theta']
        self.risk_table.data['ppos'] = self.risk_table.data['pos_long'] - self.risk_table.data['pos_short']
        for key in keys:
            pos_key = 'p' + key
            self.risk_table.data[pos_key] = self.risk_table.data[key] \
                                            * self.risk_table.data['ppos'] * self.risk_table.data['multiple']

    def risk_agg(self, risk_list):
        risks = [ r for r in list(self.risk_table.data.dtype.names) if str(r) in risk_list]
        risk_rec = self.risk_table.data[risks]
        res = dict([(instID, dict(zip(['pv','delta','gamma','vega','theta'], rec))) \
                     for instID, rec in zip(self.risk_table.data['name'], risk_rec)])
        return res

    def submit_trade(self, xtrade):
        book = xtrade.book
        exec_algo = eval(self.exec_class)(xtrade, **self.exec_args[book])
        xtrade.set_algo(exec_algo)
        self.submitted_trades[book].append(xtrade)
        self.agent.submit_trade(xtrade)

    def add_submitted_pos(self, xtrade):
        book = xtrade.book
        if book in self.submitted_pos:
            for trade in self.submitted_pos[book]:
                if trade.id == xtrade.id:
                    return False
        self.submitted_pos[book].append(xtrade)
        return True

    def day_finalize(self):
        self.logger.info('strat %s is finalizing the day - update trade unit, save state' % self.name)
        self.update_pos_greeks()
        self.update_margin()
        self.save_state()

    def get_option_dict(self, products):
        option_dict = {}
        for under in products:
            for cont_mth in products[under]:
                for strike in products[under][cont_mth]:
                    for otype in ['C', 'P']:
                        key = (str(under), cont_mth, otype, strike)
                        option_dict[key] = get_opt_name(under, otype, strike)
        return option_dict

    def run_tick(self, ctick):
        if self.is_disabled: return

    def run_min(self, inst, freq):
        if self.is_disabled: return
    
    def delta_hedge(self, under):
        ndata = self.risk_table.data
        curr_pdelta = ndata['pdelta'][ndata['under'] == under].sum()
        multiple = ndata['multiple'][self.inst_map[under]]
        volume = int((self.risk_bias['pdelta'] - curr_pdelta)/multiple)
        if volume!=0:
            curr_price = self.agent.instruments[under].mid_price
            start_time = self.agent.tick_id
            xtrade = trade.XTrade([under], [1], volume, curr_price,
                                  strategy=self.name,
                                  book = 'DeltaHedge', agent=self.agent, start_time=start_time)
            self.submit_trade(xtrade)

    def vega_hedge(self, opt_inst):
        ndata = self.risk_table.data
        under = ndata['under'][self.inst_map[opt_inst]]
        inst_vega = ndata['vega'][self.inst_map[opt_inst]]
        if inst_vega == 0:
            return
        multiple = ndata['multiple'][self.inst_map[opt_inst]]
        curr_pvega = ndata['pvega'][ndata['under'] == under].sum()
        volume = int((self.risk_bias['pvega'] - curr_pvega)/multiple/inst_vega)
        if volume!=0:
            curr_price = self.agent.instruments[opt_inst].mid_price
            start_time = self.agent.tick_id
            xtrade = trade.XTrade([opt_inst], [1], volume, curr_price,
                                  strategy=self.name,
                                  book = 'VegaHedge', agent=self.agent, start_time=start_time)
            self.submit_trade(xtrade)

    def on_trade(self, xtrade):
        pass

    def add_unwind(self, pair, book = ''):
        pass
        
class EquityOptStrat(OptionStrategy):
    def __init__(self, name, underliers, expiries, strikes, agent = None):
        OptionStrategy.__init__(self, name, underliers, expiries, strikes, agent)        
        #self.proxy_flag = {'delta': True, 'gamma': True, 'vega': True, 'theta': True}
        self.dividends = [(datetime.date(2015,4,20), 0.0), (datetime.date(2015,11,20), 0.10)]
        
    def get_option_dict(self, products):
        option_dict = {}
        for under in products:
            for cont_mth in products[under]:
                map = mysqlaccess.get_stockopt_map(under, [cont_mth], products[under][cont_mth])
                option_dict.update(map)
        return option_dict
    
class IndexFutOptStrat(OptionStrategy):
    def __init__(self, name, underliers, expiries, strikes, agent = None):
        OptionStrategy.__init__(self, name, underliers, expiries, strikes, agent)
        #self.proxy_flag = {'delta': True, 'gamma': True, 'vega': True, 'theta': True}

class CommodOptStrat(OptionStrategy):
    def __init__(self, name, underliers, expiries, strikes, agent = None):
        OptionStrategy.__init__(self, name, underliers, expiries, strikes, agent)
        #self.proxy_flag = {'delta': False, 'gamma': False, 'vega': True, 'theta': True}
        
class OptArbStrat(CommodOptStrat):
    def __init__(self, name, underliers, expiries, strikes, agent = None):
        CommodOptStrat.__init__(self, name, underliers, expiries, strikes, agent)
        self.callspd = dict([(exp, dict([(s, {'upbnd':0.0, 'lowbnd':0.0, 'pos':0.0}) for s in ss])) for exp, ss in zip(expiries, strikes)])
        self.putspd = dict([(exp, dict([(s, {'upbnd':0.0, 'lowbnd':0.0, 'pos':0.0}) for s in ss])) for exp, ss in zip(expiries, strikes)])
        self.bfly = dict([(exp, dict([(s, {'upbnd':0.0, 'lowbnd':0.0, 'pos':0.0}) for s in ss])) for exp, ss in zip(expiries, strikes)])

class OptSubStrat(object):
    def __init__(self, strat):
        self.strat = strat
    
    def tick_run(self, ctick):
        pass
