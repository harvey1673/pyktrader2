#-*- coding:utf-8 -*-
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
import numpy as np
import pandas as pd
import data_handler as dh
from misc import *

def fut2opt(fut_inst, expiry, otype, strike):
    product = inst2product(fut_inst)
    if product == 'IF':
        optkey = fut_inst.replace('IF','IO')
    else:
        optkey = product
    if product == 'Stock':
        optkey = optkey + otype + expiry.strftime('%y%m')
    else:
        optkey + '-' + otype.upper() + '-'
    opt_inst = optkey + str(int(strike))
    return opt_inst

def get_opt_margin(fut_price, strike, type):
    return 0.0

class OptionStrategy(object):
    common_params = {'name': 'opt_m', 'products':{'m1705': {201705: [2800, 2850, 2900, 2950, 3000]}, \
                                                  'm1709': {201709: [2800, 2850, 2900, 2950, 3000]}}, \                     
                     'pos_scaler': 1.0, 'daily_close_buffer': 3, 'exec_class': 'ExecAlgo1DFixT'}
    def __init__(self, config, agent = None):
        self.load_config(config)
        self.underliers = self.products.keys()                
        self.option_insts = self.get_option_map(self.products)
        self.instIDs = self.underliers + self.option_insts.values()
        self.inst_map = dict([(instID, i) for i, instID in enumerate(self.instIDs)])        
        self.underlying = [None] * len(self.instIDs)
        self.risk_table = dh.DynamicRecArray(dtype = \
                               [('name', '|S50'), ('product', '|S50'), ('underlying', '|S50'), ('cont_mth', 'i8'), \
                                ('otype', '|S10'), ('strike', 'f8'), ('multiple', 'i8'), ('df', 'f8'),\
                                ('pos_long', 'i8'), ('pos_short', 'i8'), ('out_short', 'i8'), ('out_short', 'i8'), \
                                ('margin_long', 'f8'), ('margin_short', 'f8'), \
                                ('pv', 'f8'), ('delta', 'f8'), ('gamma', 'f8'), ('vega', 'f8'), ('theta', 'f8'), \
                                ('ppv', 'f8'), ('pdelta', 'f8'), ('pgamma', 'f8'), ('pvega', 'f8'), ('ptheta', 'f8')])                 
        self.agent = agent
        self.folder = ''
        self.submitted_pos = dict([(inst, []) for inst in self.instIDs])
        self.proxy_flag = {'delta': False, 'gamma': True, 'vega': True, 'theta': True} 
        self.hedge_config = {'order_type': OPT_LIMIT_ORDER, 'num_tick':1}        

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

    def dep_instIDs(self):
        return self.instIDs

    def set_agent(self, agent):
        self.agent = agent
        self.folder = self.agent.folder + self.name + '_'
        self.underlying = [self.agent.instruments[instID] for instID in self.instIDs]   
        for inst in self.underlying:
            data_dict = {'name': inst.name, 'product': inst.product, 'underlying': inst.name, 'cont_mth': inst.cont_mth, \
                        'otype': '', 'strike': 0, 'multiple': inst.multiple, 'df': 1.0, \
                        'delta': 1.0, 'gamma': 0.0, 'vega': 0.0, 'theta': 0.0, }
            if inst not in self.underliers:
                for key in ['underlying', 'otype', 'strike']:
                    data_dict[key] = getaatr(inst, key)
            self.risk_table.append_by_dict(data_dict)
        self.register_func_freq()
        self.register_bar_freq()

    def register_func_freq(self):
        pass

    def register_bar_freq(self):
        pass

    def on_log(self, text, level = logging.INFO, args = {}):    
        event = Event(type=EVENT_LOG)
        event.dict['data'] = text
        event.dict['owner'] = "strategy_" + self.name
        event.dict['level'] = level
        self.agent.eventEngine.put(event)
        
    def initialize(self):
        self.load_state()
        for idx, inst in enumerate(self.underlying):
            if inst.ptype == ProductType.Option:
                for key in ['pv', 'delta', 'gamma', 'vega', 'theta']
                    self.risk_table[key][idx] = getattr(inst, key)
                prod = inst.product
                expiry = inst.expiry
                self.risk_table['df'][idx] = self.agent.volgrid[prod].df[expiry]
        self.update_pos_greeks()
        self.update_group_risk()
        self.update_margin()
        self.update_trade_unit()
    
    def update_margin(self):
        for inst in self.instIDs:
            if inst in self.underliers:
                self.option_map.loc[inst, 'margin_long'] = self.agent.instruments[inst].calc_margin_amount(ORDER_BUY)
                self.option_map.loc[inst, 'margin_short'] = self.agent.instruments[inst].calc_margin_amount(ORDER_SELL)
            else:
                under = self.agent.instruments[inst].underlying
                under_price = self.agent.instruments[under].price
                self.option_map.loc[inst, 'margin_long'] = self.agent.instruments[inst].calc_margin_amount(ORDER_BUY, under_price)
                self.option_map.loc[inst, 'margin_short'] = self.agent.instruments[inst].calc_margin_amount(ORDER_SELL, under_price)
                 
    def update_greeks(self, inst): 
        '''update option instrument greeks'''
        #multiple = self.option_map.loc[inst, 'multiple']
        pv = self.option_insts[inst].price() 
        delta = self.option_insts[inst].delta()
        gamma = self.option_insts[inst].gamma()
        vega  = self.option_insts[inst].vega()/100.0
        theta = self.option_insts[inst].theta()
        df = self.option_map.loc[inst, 'df']
        opt_info = {'pv': pv, 'delta': delta/df, 'gamma': gamma/df/df, 'vega': vega, 'theta': theta}
        self.option_map.loc[inst, opt_info.keys()] = pd.Series(opt_info)
    
    def update_pos_greeks(self):
        '''update position greeks according to current positions'''
        keys = ['pv', 'delta', 'gamma', 'vega', 'theta']
        for key in keys:
            pos_key = 'p' + key
            self.option_map[pos_key] = self.option_map[key] * self.option_map['pos'] * self.option_map['multiple']
        
    def risk_reval(self, expiry, is_recalib=True):
        '''recalibrate vol surface per fwd move, get greeks update for instrument greeks'''
        dtoday = date2xl(self.agent.scur_day) + max(self.agent.tick_id - 600000, 0)/2400000.0
        cont_mth = expiry.year * 100 + expiry.month
        indices = self.option_map[(self.option_map.cont_mth == cont_mth) & (self.option_map.otype != 0)].index
        dexp = datetime2xl(expiry)
        idx = self.expiries.index(expiry)
        fwd = self.get_fwd(idx)
        if is_recalib:
            self.last_updated[expiry]['fwd'] = fwd
            self.last_updated[expiry]['dtoday'] = dtoday
            self.volgrids[expiry].setFwd(fwd)
            self.volgrids[expiry].setToday(dtoday)            
            self.volgrids[expiry].initialize()                
        for inst in indices:
            self.option_insts[inst].setFwd(fwd)
            self.option_insts[inst].setFwd(dtoday)
            self.update_greeks(inst)
    
    def reval_all(self):
        for expiry in self.expiries:
            self.risk_reval(expiry, is_recalib=True)
        self.update_pos_greeks()
        self.update_group_risk()
        self.update_margin()
    
    def update_group_risk(self):
        group_keys = ['cont_mth', 'ppv', 'pdelta', 'pgamma','pvega','ptheta']
        self.group_risk = self.option_map[group_keys].groupby('cont_mth').sum()
    
    def add_submitted_pos(self, etrade):
        is_added = False
        for trade in self.submitted_pos:
            if trade.id == etrade.id:
                is_added = False
                return
        self.submitted_pos.append(etrade)
        return True

    def day_finalize(self):    
        self.save_state()
        self.logger.info('strat %s is finalizing the day - update trade unit, save state' % self.name)
        
    def get_option_map(self, products):
        option_map = {}
        for under in self.products:
            for cont_mth in self.products[under]:
                for strike in self.products[under][cont_mth]:
                    for otype in ['C', 'P']:
                        key = (str(under), cont_mth, otype, strike)
                        instID = under
                        if instID[:2] == "IF":
                            instID = instID.replace('IF', 'IO')
                        if exch == 'CZCE':
                            instID = instID + otype + str(strike)
                        else:
                            instID = instID + '-' + otype + '-' + str(strike)
                        option_map[key] = instID
        return option_map
 
    def tick_run(self, ctick):
        pass

    def run_min(self, inst):
        pass
    
    def delta_hedger(self):
        tot_deltas = self.group_risk.pdelta.sum()
        cum_vol = 0
        if (self.spot_model == False) and (self.proxy_flag['delta']== False):
            for idx, inst in enumerate(self.underliers):
                if idx == self.main_cont: 
                    continue
                multiple = self.option_map[inst, 'multiple']
                cont_mth = self.option_map[inst, 'cont_mth']
                pdelta = self.group_risk[cont_mth, 'delta'] 
                volume = int( - pdelta/multiple + 0.5)
                cum_vol += volume
                if volume!=0:
                    curr_price = self.agent.instruments[inst].price
                    buysell = 1 if volume > 0 else -1
                    valid_time = self.agent.tick_id + 600
                    etrade = trade.XTrade( [inst], [volume], [self.hedge_config['order_type']], curr_price*buysell, [self.hedge_config['num_tick']], \
                                               valid_time, self.name, self.agent.name)
                    self.submitted_pos[inst].append(etrade)
                    self.agent.submit_trade(etrade)
        inst = self.underliers[self.main_cont]
        multiple = self.option_map[inst, 'multiple']
        tot_deltas += cum_vol
        volume = int( tot_deltas/multiple + 0.5)
        if volume!=0:
            curr_price = self.agent.instruments[inst].price
            buysell = 1 if volume > 0 else -1
            etrade = trade.XTrade( [inst], [volume], [self.hedge_config['order_type']], curr_price*buysell, [self.hedge_config['num_tick']], \
                                valid_time, self.name, self.agent.name)
            self.submitted_pos[inst].append(etrade)
            self.agent.submit_trade(etrade)
        
class EquityOptStrat(OptionStrategy):
    def __init__(self, name, underliers, expiries, strikes, agent = None):
        OptionStrategy.__init__(self, name, underliers, expiries, strikes, agent)        
        self.proxy_flag = {'delta': True, 'gamma': True, 'vega': True, 'theta': True}
        self.dividends = [(datetime.date(2015,4,20), 0.0), (datetime.date(2015,11,20), 0.10)]
        
    def get_option_map(self, underliers, expiries, strikes):
        cont_mths = [expiry.year*100 + expiry.month for expiry in expiries]
        all_map = {}
        for under in underliers:
            map = mysqlaccess.get_stockopt_map(under, cont_mths, strikes)
            all_map.update(map)
        return all_map
    
    def get_fwd(self, idx):
        spot = self.agent.instruments[self.underliers[0]].price
        return spot*self.DFs[idx]
    
class IndexFutOptStrat(OptionStrategy):
    def __init__(self, name, underliers, expiries, strikes, agent = None):
        OptionStrategy.__init__(self, name, underliers, expiries, strikes, agent)
        self.proxy_flag = {'delta': True, 'gamma': True, 'vega': True, 'theta': True} 

class CommodOptStrat(OptionStrategy):
    def __init__(self, name, underliers, expiries, strikes, agent = None):
        OptionStrategy.__init__(self, name, underliers, expiries, strikes, agent)
        self.proxy_flag = {'delta': False, 'gamma': False, 'vega': True, 'theta': True} 
        
class OptArbStrat(CommodOptStrat):
    def __init__(self, name, underliers, expiries, strikes, agent = None):
        CommodOptStrat.__init__(self, name, underliers, expiries, strikes, agent)
        self.callspd = dict([(exp, dict([(s, {'upbnd':0.0, 'lowbnd':0.0, 'pos':0.0}) for s in ss])) for exp, ss in zip(expiries, strikes)])
        self.putspd = dict([(exp, dict([(s, {'upbnd':0.0, 'lowbnd':0.0, 'pos':0.0}) for s in ss])) for exp, ss in zip(expiries, strikes)])
        self.bfly = dict([(exp, dict([(s, {'upbnd':0.0, 'lowbnd':0.0, 'pos':0.0}) for s in ss])) for exp, ss in zip(expiries, strikes)])
        
    def tick_run(self, ctick):         
        inst = ctick.instID

class OptSubStrat(object):
    def __init__(self, strat):
        self.strat = strat
    
    def tick_run(self, ctick):
        pass
