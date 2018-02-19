import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

import misc
import json
import data_handler as dh
import pandas as pd
import numpy as np
import trade_position
import datetime
from backtest import *
import sys

class MASystemSim(StratSim):
    def __init__(self, config):
        super(MASystemSim, self).__init__(config)

    def process_data(self, mdf):
        self.df = mdf

    def process_config(self, config):
        self.offset = config['offset']
        self.pos_class = config['pos_class']
        self.pos_args  = config['pos_args']
        self.pos_update = config.get('pos_update', False)
        self.stoploss = config.get('stoploss', 0.0)
        self.win_list = config['win_list']
        self.ma_func = eval(config['ma_func'])
        self.use_chan = config.get('use_chan', False)
        self.close_daily = config['close_daily']
        self.tcost = config['trans_cost']
        self.unit = config['unit']
        self.freq = config['freq']
        self.chan_ratio = config['channel_ratio']
        if self.chan_ratio > 0:
            self.use_chan = True
            self.channel = int(self.chan_ratio * self.win_list[-1])
        else:
            self.use_chan = False
            self.channel = 0
        self.chan_func = config['channel_func']
        self.chan_high = eval(self.chan_func[0])
        self.chan_low  = eval(self.chan_func[1])
        self.high_args = config['channel_args'][0]
        self.low_args = config['channel_args'][1]

    def run_vec_sim(self):
        if int(self.freq[:-3]) == 1:
            xdf = self.df
        else:
            xdf = dh.conv_ohlc_freq(self.df, self.freq, extra_cols=['contract'])
        for idx, win in enumerate(self.win_list):
            xdf['MA'+str(idx+1)] = self.ma_func(xdf, win).shift(1)
        if self.use_chan:
            xdf['chan_high'] = self.chan_high(xdf, self.channel, **self.high_args).shift(2)
            xdf['chan_low'] = self.chan_low(xdf, self.channel, **self.low_args).shift(2)
        else:
            xdf['chan_high'] = pd.Series(index = xdf.index)
            xdf['chan_low'] = pd.Series(index = xdf.index)
        xdf['prev_close'] = xdf['close'].shift(1)
        xdf['close_ind'] = np.isnan(xdf['close'].shift(-1))
        if self.close_daily:
            daily_end = (xdf['date']!=xdf['date'].shift(-1))
            xdf['close_ind'] = xdf['close_ind'] | daily_end
        long_signal = pd.Series(np.nan, index = xdf.index)
        last = len(self.win_list)
        long_flag = (xdf['MA1'] >= xdf['MA2']) & (xdf['MA1'] >= xdf['MA'+str(last)])
        if self.use_chan:
            long_flag = long_flag & (xdf['open'] >= xdf['chan_high'])
        long_signal[long_flag] = 1
        cover_flag = (xdf['MA1'] < xdf['MA'+str(last)])
        if self.use_chan:
            cover_flag = cover_flag | (xdf['open'] < xdf['chan_low'])
        long_signal[cover_flag] = 0
        long_signal[xdf['close_ind']] = 0
        long_signal = long_signal.fillna(method='ffill').fillna(0)
        short_signal = pd.Series(np.nan, index = xdf.index)
        short_flag = (xdf['MA1'] <= xdf['MA2']) & (xdf['MA1'] <= xdf['MA'+str(last)])
        if self.use_chan:
            short_flag = short_flag & (xdf['open'] <= xdf['chan_low'])
        cover_flag = (xdf['MA1'] > xdf['MA'+str(last)])
        if self.use_chan:
            cover_flag = cover_flag | (xdf['open'] > xdf['chan_low'])
        short_signal[cover_flag] = 0
        short_signal[xdf['close_ind']] = 0
        short_signal = short_signal.fillna(method='ffill').fillna(0)
        if len(xdf[(long_signal>0) & (short_signal<0)])>0:
            print xdf[(long_signal > 0) & (short_signal < 0)]
            print "something wrong with the position as long signal and short signal happen the same time"
        xdf['pos'] = long_signal + short_signal
        xdf['cost'] = abs(xdf['pos'] - xdf['pos'].shift(1)) * (self.offset + xdf['open'] * self.tcost)
        xdf['cost'] = xdf['cost'].fillna(0.0)
        xdf['traded_price'] = xdf.open + (xdf['pos'] - xdf['pos'].shift(1)) * self.offset
        closed_trades = simdf_to_trades1(xdf, slippage = self.offset )
        return (xdf, closed_trades)

def gen_config_file(filename):
    sim_config = {}
    sim_config['sim_func']  = 'bktest_MA_system.MA_sim'
    sim_config['scen_keys'] = ['freq', 'win_list']
    sim_config['sim_name']   = 'EMA3_025'
    sim_config['products']   = ['rb', 'i', 'j']
    sim_config['start_date'] = '20150102'
    sim_config['end_date']   = '20160708'
    sim_config['need_daily'] = False
    sim_config['freq'] = ['30min', '60min']
    sim_config['win_list'] = [ [5,  10, 20], [5, 10, 40], [5, 20, 40], [5, 20, 80], \
                             [10, 20, 40], [10, 20, 80],[10, 30, 60],[10, 30, 120],\
                             [10, 40, 80], [10, 40, 120],\
                             [5, 10], [5, 20], [5, 40], \
                             [10, 20], [10, 30], [10, 40] ]
    sim_config['pos_class'] = 'trade_position.TradePos'
    sim_config['offset']    = 1
    config = {'capital': 10000,
              'trans_cost': 0.0,
              'unit': 1,
              'stoploss': 0.0,
              'close_daily': False,
              'pos_update': False,
              'MA_func': 'dh.EMA',
              'channel_func': ['dh.DONCH_H', 'dh.DONCH_L'],
              'channel_args': [{}, {}],
              'channel_ratio': 0.25,
              'exit_min': 2055,
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
