import sys
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
        self.k = config['param'][0]
        self.win = config['param'][1]
        self.multiplier = config['param'][2]
        self.f = config['param'][3]
        self.price_mode = config.get('price_mode','TP')
        self.pos_update = config['pos_update']
        self.pos_class = config['pos_class']
        self.pos_args  = config['pos_args']
        self.proc_func = config['proc_func']
        self.proc_args = config['proc_args']
        chan_func = config['chan_func']
        self.chan_high = eval(chan_func['high']['func'])
        self.chan_low  = eval(chan_func['low']['func'])
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
        xdf['chan_h'] = self.chan_high(xdf['high'], self.chan, **self.chan_func['high']['args'])
        xdf['chan_l'] = self.chan_low(xdf['low'], self.chan, **self.chan_func['low']['args'])
        xdata = pd.concat([xdf['TR'].shift(1), xdf['MA'].shift(1),
                           xdf['chan_h'].shift(1), xdf['chan_l'].shift(1),
                           xdf['open']], axis=1, keys=['tr','ma', 'chanh', 'chanl', 'dopen']).fillna(0)
        self.df = mdf.join(xdata, how = 'left').fillna(method='ffill')
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
        return (sim_data['ma'][n] == 0) or (sim_data['chan_h'][n] == 0) or (sim_data['dopen'][n] == 0) \
               or (sim_data['date'][n] != sim_data['date'][n + 1])

    def on_bar(self, sim_data, n):
        if self.price_mode == 'TP':
            ref_long = ref_short = (sim_data['close'][n] + sim_data['high'][n] + sim_data['low'][n])/3.0
        elif self.price_mode == 'HL':
            ref_long  = sim_data['high'][n]
            ref_short = sim_data['low'][n]
        elif self.price_mode == 'CL':
            ref_long = ref_short = sim_data['close'][n]
        else:
            ref_long = ref_short = sim_data['open'][n+1]
        target_pos = (ref_long > self.buy_trig) - (ref_short < self.sell_trig)
        if len(self.positions)>0:
            need_close = (self.close_daily or (self.scur_day == sim_data['date'][-1])) and (sim_data['min_id'][n] >= self.exit_min)
            for tradepos in self.positions:
                if need_close or (tradepos.pos * target_pos < 0):
                    self.close_tradepos(tradepos, sim_data['open'][n+1])
            self.positions = [pos for pos in self.positions if not pos.is_closed]
            if need_close:
                return
        if target_pos != 0:
            if (not self.use_chan) or (((ref_long > sim_data['chanh'][n]) and target_pos > 0) or ((ref_short < sim_data['chanl'][n]) and target_pos < 0)):
                self.open_tradepos([sim_data['contract'][n]], sim_data['open'][n+1], target_pos)
    
def run_sim(config):
    mdf = config['mdf']
    close_daily = config['close_daily']
    offset = config['offset']
    k = config['param'][0]
    win = config['param'][1]
    multiplier = config['param'][2]
    f = config['param'][3]
    price_mode = config.get('price_mode','TP')
    pos_update = config['pos_update']
    pos_class = config['pos_class']
    pos_args  = config['pos_args']
    proc_func = config['proc_func']
    proc_args = config['proc_args']
    chan_func = config['chan_func']
    chan_high = eval(chan_func['high']['func'])
    chan_low  = eval(chan_func['low']['func'])
    tcost = config['trans_cost']
    unit = config['unit']
    SL = config['stoploss']
    min_rng = config['min_range']
    chan = config['chan']
    use_chan = config['use_chan']
    no_trade_set = config['no_trade_set']
    pos_freq = config.get('pos_freq', 1)
    xdf = proc_func(mdf, **proc_args)
    if win == -1:
        tr= pd.concat([xdf.high - xdf.low, abs(xdf.close - xdf.close.shift(1))],
                       join='outer', axis=1).max(axis=1)
    elif win == 0:
        tr = pd.concat([(pd.rolling_max(xdf.high, 2) - pd.rolling_min(xdf.close, 2))*multiplier,
                        (pd.rolling_max(xdf.close, 2) - pd.rolling_min(xdf.low, 2))*multiplier,
                        xdf.high - xdf.close,
                        xdf.close - xdf.low],
                        join='outer', axis=1).max(axis=1)
    else:
        tr= pd.concat([pd.rolling_max(xdf.high, win) - pd.rolling_min(xdf.close, win),
                       pd.rolling_max(xdf.close, win) - pd.rolling_min(xdf.low, win)],
                       join='outer', axis=1).max(axis=1)
    xdf['TR'] = tr
    xdf['chan_h'] = chan_high(xdf['high'], chan, **chan_func['high']['args'])
    xdf['chan_l'] = chan_low(xdf['low'], chan, **chan_func['low']['args'])
    xdata = pd.concat([xdf['TR'].shift(1), xdf['MA'].shift(1),
                       xdf['chan_h'].shift(1), xdf['chan_l'].shift(1),
                       xdf['open']], axis=1, keys=['tr','ma', 'chanh', 'chanl', 'dopen']).fillna(0)
    df = mdf.join(xdata, how = 'left').fillna(method='ffill')
    df['pos'] = 0
    df['cost'] = 0
    df['traded_price'] = df['open']
    sim_data = dh.DynamicRecArray(dataframe=df)
    nlen = len(sim_data)
    positions = []
    closed_trades = []
    tradeid = 0
    curr_date = None
    buytrig = selltrig = 0.0
    for n in range(nlen-3):
        cost = 0
        pos = sim_data['pos'][n]
        if sim_data['ma'][n] == 0 or sim_data['chan_h'][n] == 0 or sim_data['dopen'][n] == 0:
            continue
        if curr_date != sim_data['date'][n]:
            curr_date = sim_data['date'][n]
            dopen = sim_data['dopen'][n]
            rng = max(min_rng * dopen, k * sim_data['tr'][n])
            buytrig = dopen + rng
            selltrig = dopen - rng
            if sim_data['ma'][n] > dopen:
                buytrig += f * rng
            else:
                selltrig -= f * rng
            continue
        if price_mode == 'TP':
            ref_long = ref_short = (sim_data['close'][n] + sim_data['high'][n] + sim_data['low'][n])/3.0
        elif price_mode == 'HL':
            ref_long  = sim_data['high'][n]
            ref_short = sim_data['low'][n]
        elif price_mode == 'CL':
            ref_long = ref_short = sim_data['close'][n]
        else:
            ref_long = ref_short = sim_data['open'][n+1]
        target_pos = (ref_long > buytrig) - (ref_short < selltrig)
        if len(positions)>0:
            need_close = (close_daily or (curr_date == sim_data['date'][-1])) and (sim_data['min_id'][n] >= config['exit_min'])
            for tradepos in positions:
                ep = sim_data['low'][n] if tradepos.pos > 0 else sim_data['high'][n]
                if need_close or tradepos.check_exit(sim_data['open'][n+1], 0) or ( tradepos.pos * target_pos < 0):
                    tradepos.close(sim_data['open'][n+1] - offset * misc.sign(tradepos.pos), sim_data['datetime'][n+1])
                    tradepos.exit_tradeid = tradeid
                    tradeid += 1
                    pos -= tradepos.pos
                    cost += abs(tradepos.pos) * (offset + sim_data['open'][n+1]*tcost)
                    closed_trades.append(tradepos)
                elif pos_update:
                    tradepos.update_price(ep)
            positions = [pos for pos in positions if not pos.is_closed]
            if need_close:
                continue
        if target_pos != 0:
            if (not use_chan) or (((ref_long > sim_data['chanh'][n]) and target_pos > 0) or ((ref_short < sim_data['chanl'][n]) and target_pos < 0)):
                new_pos = pos_class([sim_data['contract'][n]], [1], unit * target_pos, sim_data['open'][n+1] + target_pos * offset, buytrig, **pos_args)
                tradeid += 1
                new_pos.entry_tradeid = tradeid
                new_pos.open(sim_data['open'][n+1] + target_pos * offset, sim_data['datetime'][n+1])
                positions.append(new_pos)
                pos += unit * target_pos
                cost += abs(target_pos) * (offset + sim_data['open'][n+1]*tcost)
        sim_data['cost'][n+1] = cost
        sim_data['pos'][n+1] = pos
    out_df = pd.concat([])
    return out_df, closed_trades

def gen_config_file(filename):
    sim_config = {}
    sim_config['sim_class']  = 'bktest_dtsplit_psar.DTStopSim'
    sim_config['sim_func'] = 'run_loop_sim'
    sim_config['scen_keys'] = ['param']
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
    sim_config['pos_class'] = 'strat.ParSARTradePos'
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
              'pos_args': { 'af': 0.02, 'incr': 0.02, 'cap': 0.2},
              'pos_update': True,
              'chan_func': chan_func,
              'pos_freq':30,
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
