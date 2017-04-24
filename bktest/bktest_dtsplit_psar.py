import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)
import json
import misc
import data_handler as dh
import pandas as pd
import numpy as np
import datetime
from backtest import *

class DTStopSim(StratSim):
    def __init__(self, config):
        super(DTStopSim, self).__init__(config)

    def process_config(self, config): 
        self.close_daily = config['close_daily']
        self.offset = config['offset']
        self.tick_base = config['tick_base']
        self.k = config['param'][0]
        self.win = config['param'][1]
        self.multiplier = config['param'][2]
        self.f = config['param'][3]
        self.atr_len = config['atr_period']
        self.price_mode = config.get('price_mode','TP')
        self.pos_update = config['pos_update']
        self.pos_class = config['pos_class']
        self.pos_args  = config['pos_args']
        self.proc_func = config['proc_func']
        self.proc_args = config['proc_args']
        self.chan_func = config['chan_func']
        self.chan_high = eval(self.chan_func['high']['func'])
        self.chan_low  = eval(self.chan_func['low']['func'])
        self.tcost = config['trans_cost']
        self.unit = config['unit']
        self.weights = config.get('weights', [1])
        self.SL = config['stoploss']
        self.min_rng = config['min_range']
        self.chan = config['chan']
        self.use_chan = config['use_chan']
        self.no_trade_set = config['no_trade_set']
        self.pos_freq = config.get('pos_freq', 1)
        self.exit_min = config.get('exit_min', 2058)
        self.buy_trig = 0.0
        self.sell_trig = 0.0
     
    def process_data(self, mdf):
        xdf = self.proc_func(mdf, **self.proc_args)
        if self.win == -1:
            tr= pd.concat([xdf.high - xdf.low, abs(xdf.close - xdf.close.shift(1))],
                           join='outer', axis=1).max(axis=1)
        elif self.win == 0:
            tr = pd.concat([(pd.rolling_max(xdf.high, 2) - pd.rolling_min(xdf.close, 2))*self.multiplier,
                            (pd.rolling_max(xdf.close, 2) - pd.rolling_min(xdf.low, 2))*self.multiplier,
                            xdf.high - xdf.close,
                            xdf.close - xdf.low],
                            join='outer', axis=1).max(axis=1)
        else:
            tr= pd.concat([pd.rolling_max(xdf.high, self.win) - pd.rolling_min(xdf.close, self.win),
                           pd.rolling_max(xdf.close, self.win) - pd.rolling_min(xdf.low, self.win)],
                           join='outer', axis=1).max(axis=1)
        xdf['TR'] = tr
        xdf['chanh'] = self.chan_high(xdf['high'], self.chan, **self.chan_func['high']['args'])
        xdf['chanl'] = self.chan_low(xdf['low'], self.chan, **self.chan_func['low']['args'])
        xdf['ATR'] = dh.ATR(xdf, n = self.atr_len)
        xdf['MA'] = dh.MA(xdf, n=self.atr_len, field = 'close')
        xdata = pd.concat([xdf['TR'].shift(1), xdf['MA'].shift(1), xdf['ATR'].shift(1),
                           xdf['chanh'].shift(1), xdf['chanl'].shift(1),
                           xdf['open']], axis=1, keys=['tr','ma', 'atr', 'chanh', 'chanl', 'dopen']).fillna(0)
        self.df = mdf.join(xdata, how = 'left').fillna(method='ffill')
        self.df['datetime'] = self.df.index
        self.df['cost'] = 0
        self.df['pos'] = 0
        self.df['traded_price'] = self.df['open']

    def daily_initialize(self, sim_data, n):
        self.dopen = sim_data['dopen'][n]
        rng = max(self.min_rng * self.dopen, self.k * sim_data['tr'][n])
        self.buy_trig = self.dopen + rng
        self.sell_trig = self.dopen - rng
        if sim_data['ma'][n] > self.dopen:
            self.buy_trig += self.f * rng
        else:
            self.sell_trig -= self.f * rng

    def check_data_invalid(self, sim_data, n):
        return (sim_data['ma'][n] == 0) or (sim_data['chanh'][n] == 0) or (sim_data['dopen'][n] == 0) \
               or (sim_data['date'][n] != sim_data['date'][n + 1])

    def get_tradepos_exit(self, tradepos, sim_data, n):
        gap = (int(self.SL * sim_data['atr'][n]/self.tick_base) + 1) * self.tick_base
        return gap

    def on_bar(self, sim_data, n):
        self.pos_args = {'reset_margin': sim_data['atr'][n]}
        if self.price_mode == 'TP':
            ref_long = ref_short = (sim_data['close'][n] + sim_data['high'][n] + sim_data['low'][n])/3.0
        elif self.price_mode == 'HL':
            ref_long  = sim_data['high'][n]
            ref_short = sim_data['low'][n]
        elif self.price_mode == 'CL':
            ref_long = ref_short = sim_data['close'][n]
        else:
            ref_long = ref_short = sim_data['open'][n+1]
        target_pos = (ref_long > self.buy_trig) * 1 - (ref_short < self.sell_trig) * 1
        curr_pos = 0
        if len(self.positions)>0:
            curr_pos = self.positions[0].pos
            need_close = (self.close_daily or (self.scur_day == sim_data['date'][-1])) and (sim_data['min_id'][n] >= self.exit_min)
            for tradepos in self.positions:
                if need_close or (tradepos.pos * target_pos < 0):
                    self.close_tradepos(tradepos, sim_data['open'][n+1])
            self.positions = [pos for pos in self.positions if not pos.is_closed]
            if need_close:
                return
            else:
                if len(self.positions) > 0:
                    curr_pos = self.positions[0].pos        
        if target_pos != 0 and (curr_pos * target_pos <= 0):                            
            if (not self.use_chan) or (((ref_long > sim_data['chanh'][n]) and target_pos > 0) or ((ref_short < sim_data['chanl'][n]) and target_pos < 0)):
                self.open_tradepos([sim_data['contract'][n]], sim_data['open'][n+1], target_pos)

def gen_config_file(filename):
    sim_config = {}
    sim_config['sim_class']  = 'bktest_dtsplit_psar.DTStopSim'
    sim_config['sim_func'] = 'run_loop_sim'
    sim_config['scen_keys'] = ['param', 'stoploss']
    sim_config['sim_name']   = 'DT_psar'
    sim_config['products']   = ['m', 'RM', 'y', 'p', 'a', 'rb', 'SR', 'TA', 'MA', 'i', 'ru', 'j' ]
    sim_config['start_date'] = '20150102'
    sim_config['end_date']   = '20160311'
    sim_config['param']  =  [
            (0.5, 0, 0.5, 0.0), (0.6, 0, 0.5, 0.0), (0.7, 0, 0.5, 0.0), (0.8, 0, 0.5, 0.0), \
            (0.9, 0, 0.5, 0.0), (1.0, 0, 0.5, 0.0), (1.1, 0, 0.5, 0.0), \
            (0.5, 1, 0.5, 0.0), (0.6, 1, 0.5, 0.0), (0.7, 1, 0.5, 0.0), (0.8, 1, 0.5, 0.0), \
            (0.9, 1, 0.5, 0.0), (1.0, 1, 0.5, 0.0), (1.1, 1, 0.5, 0.0), \
            (0.2, 2, 0.5, 0.0), (0.25,2, 0.5, 0.0), (0.3, 2, 0.5, 0.0), (0.35, 2, 0.5, 0.0),\
            (0.4, 2, 0.5, 0.0), (0.45, 2, 0.5, 0.0),(0.5, 2, 0.5, 0.0), \
            #(0.2, 4, 0.5, 0.0), (0.25, 4, 0.5, 0.0),(0.3, 4, 0.5, 0.0), (0.35, 4, 0.5, 0.0),\
            #(0.4, 4, 0.5, 0.0), (0.45, 4, 0.5, 0.0),(0.5, 4, 0.5, 0.0),\
            ]
    sim_config['stoploss'] = [1, 2, 3]
    sim_config['pos_class'] = 'strat.TargetTrailTradePos'
    sim_config['proc_func'] = 'dh.day_split'
    sim_config['offset']    = 1
    chan_func = {'high': {'func': 'pd.rolling_max', 'args':{}},
                 'low':  {'func': 'pd.rolling_min', 'args':{}},
                 }
    config = {'capital': 10000,
              'chan': 10,
              'use_chan': False,
              'trans_cost': 0.0,
              'close_daily': False,
              'unit': 1,
              'stoploss': 0.0,
              'min_range': 0.004,
              'proc_args': {'minlist':[1500]},
              'pos_args': {},
              'pos_update': True,
              'atr_period': 10,
              'chan_func': chan_func,
              }
    sim_config['config'] = config
    with open(filename, 'w') as outfile:
        json.dump(sim_config, outfile)
    return sim_config

if __name__=="__main__":
    args = sys.argv[1:]
    if len(args) < 1:
        print "need to input a file name for config file"
    else:
        gen_config_file(args[0])
    pass
