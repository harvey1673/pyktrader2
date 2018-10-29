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

class MARibbonSim(StratSim):
    def __init__(self, config):
        super(MARibbonSim, self).__init__(config)

    def process_config(self, config):
        self.close_daily = config['close_daily']
        self.offset = config['offset']
        self.tick_base = config['tick_base']
        self.freq = config['freq']
        self.corr_entry = config['param'][0]
        self.corr_exit = config['param'][1]
        self.pval_entry = config['param'][2]
        self.pval_exit = config['param'][3]
        self.ma_list = config['ma_list']
        self.pos_update = config['pos_update']
        self.pos_class = config['pos_class']
        self.pos_args  = config['pos_args']
        self.tcost = config['trans_cost']
        self.unit = config['unit']
        self.weights = config.get('weights', [1])
        self.SL = config['stoploss']
        self.no_trade_set = config['no_trade_set']
        self.exit_min = config.get('exit_min', 2060 - self.freq * 2)

    def process_data(self, mdf):
        if self.freq == 1:
            xdf = mdf
        else:
            freq_str = str(self.freq) + "min"
            xdf = dh.conv_ohlc_freq(mdf, freq_str, extra_cols=['contract'])
        ma_ribbon = dh.MA_RIBBON(xdf, self.ma_list)
        self.df = xdf
        for malen in self.ma_list:
            self.df['EMA' + str(malen)] = ma_ribbon['EMA_CLOSE_' + str(malen)]
        self.df['RIBBON_CORR'] = ma_ribbon['MARIBBON_CORR']
        self.df['RIBBON_PVAL'] = ma_ribbon['MARIBBON_PVAL']
        self.df['closeout'] = 0.0
        self.df['cost'] = 0.0
        self.df['pos'] = 0.0
        self.df['traded_price'] = self.df['open']

    def run_vec_sim(self):
        close_ind = pd.Series(False, index = self.df.index)
        close_ind.iloc[-1] = True
        if self.close_daily:
            daily_end = (self.df['date'] != self.df['date'].shift(-1))
            close_ind = close_ind | daily_end
        long_signal = pd.Series(np.nan, index=self.df.index)
        long_flag = (self.df['RIBBON_CORR'] >= self.corr_entry) & (self.df['RIBBON_PVAL'] < self.pval_entry)
        long_signal[long_flag] = 1
        long_signal[(self.df['RIBBON_CORR'] < self.corr_exit) | (self.df['RIBBON_PVAL'] > self.pval_exit)] = 0
        long_signal[close_ind] = 0
        long_signal = long_signal.fillna(method='ffill').fillna(0)
        short_signal = pd.Series(np.nan, index=self.df.index)
        short_flag = (self.df['RIBBON_CORR'] <= -self.corr_entry) & (self.df['RIBBON_PVAL'] < self.pval_entry)
        short_signal[short_flag] = -1
        short_signal[(self.df['RIBBON_CORR'] > -self.corr_exit) | (self.df['RIBBON_PVAL'] > self.pval_exit)] = 0
        short_signal[close_ind] = 0
        short_signal = short_signal.fillna(method='ffill').fillna(0)
        pos =  (long_signal + short_signal)
        self.df['pos'] = pos.shift(1).fillna(0)
        self.df.ix[-1:, 'pos'] = 0
        self.df['cost'] = abs(self.df['pos'] - self.df['pos'].shift(1)) * (self.offset + self.df['open'] * self.tcost)
        self.df['cost'] = self.df['cost'].fillna(0.0)
        self.df['traded_price'] = self.df.open + (self.df['pos'] - self.df['pos'].shift(1)) * self.offset
        self.closed_trades = simdf_to_trades1(self.df)
        return (self.df, self.closed_trades)

def gen_config_file(filename):
    sim_config = {}
    sim_config['sim_class']  = 'bktest.bktest_ma_ribbon.MARibbonSim'
    sim_config['sim_func'] = 'run_vec_sim'
    sim_config['scen_keys'] = ['freq', 'param']
    sim_config['sim_name']   = 'ma_ribbon'
    sim_config['products']   = ['rb', 'hc']
    sim_config['start_date'] = '20150901'
    sim_config['end_date']   = '20180928'
    sim_config['freq'] = [1, 3, 5, 15]
    sim_config['param'] =[[0, 0, 0.5, 0.5], [0, 0, 0.05, 0.2], [0, 0, 0.08, 0.2], [0, 0, 0.1, 0.2],\
                          [0, 0, 0.5, 0.5], [0, 0, 0.05, 0.3], [0, 0, 0.08, 0.3], [0, 0, 0.1, 0.3],\
                          [0, 0, 0.5, 0.5], [0, 0, 0.05, 0.4], [0, 0, 0.08, 0.4], [0, 0, 0.1, 0.4],]
    sim_config['pos_class'] = 'strat.TradePos'
    sim_config['offset']    = 1
    config = {'capital': 10000,              
              'trans_cost': 0.0,
              'unit': 1,
              'ma_list': [5, 10, 20, 30, 40, 60, 80, 120, 160],
              'stoploss': 0.0,
              'close_daily': False,
              'pos_update': False,
              'pos_args': {},
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