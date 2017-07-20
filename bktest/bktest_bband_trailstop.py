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

class BBTrailStop(StratSim):
    def __init__(self, config):
        super(BBTrailStop, self).__init__(config)

    def process_config(self, config):
        self.close_daily = config['close_daily']
        self.offset = config['offset']
        self.tick_base = config['tick_base']
        self.freq = config['freq']
        self.band_ratio = config['band_ratio']
        self.ma_func = eval(config.get('ma_func', 'dh.MA'))
        self.band_func = eval(config.get('band_func', 'dh.ATR'))
        self.boll_len = config['boll_len']
        self.chan_len = config['chan_ratio'] * self.boll_len
        self.pos_update = config['pos_update']
        self.pos_class = config['pos_class']
        self.pos_args  = config['pos_args']        
        self.tcost = config['trans_cost']
        self.unit = config['unit']
        self.weights = config.get('weights', [1])
        self.SL = config['stoploss']
        self.no_trade_set = config['no_trade_set']
        self.pos_freq = config.get('pos_freq', 1)
        self.exit_min = config.get('exit_min', 2060 - self.freq * 2)
        self.buy_trig = 0.0
        self.sell_trig = 0.0
     
    def process_data(self, mdf):
        if self.freq == 1:
            xdf = mdf
        else:
            freq_str = str(self.freq) + "min"
            xdf = dh.conv_ohlc_freq(mdf, freq_str, extra_cols = ['contract'])
        xdf['band_wth'] = self.band_func(xdf, n = self.boll_len) * self.band_ratio
        xdf['band_mid'] = self.ma_func(xdf, n=self.boll_len)
        xdf['band_up'] = xdf['band_mid'] + xdf['band_wth']
        xdf['band_dn'] = xdf['band_mid'] - xdf['band_wth']
        if (self.chan_len > 0):
            xdf['chan_h'] = dh.DONCH_H(xdf, n = self.chan_len, field = 'high')
            xdf['chan_l'] = dh.DONCH_L(xdf, n = self.chan_len, field = 'low')
        else:
            xdf['chan_h'] = -10000000
            xdf['chan_l'] = 10000000
        xdata = pd.concat([xdf['band_up'].shift(1), xdf['band_dn'].shift(1), \
                           xdf['band_mid'].shift(1), xdf['band_wth'].shift(1), \
                           xdf['chan_h'].shift(1), xdf['chan_l'].shift(1)], axis=1, \
                           keys=['band_up','band_dn', 'band_mid', 'band_wth', \
                                 'chan_h', 'chan_l'])
        self.df = mdf.join(xdata, how = 'left').fillna(method='ffill')
        self.df['datetime'] = self.df.index
        self.df['cost'] = 0.0
        self.df['pos'] = 0.0
        self.df['closeout'] = 0.0
        self.df['traded_price'] = self.df['open']

    def daily_initialize(self, sim_data, n):
        pass

    def check_data_invalid(self, sim_data, n):
        return np.isnan(sim_data['band_up'][n]) or np.isnan(sim_data['chan_h'][n]) or np.isnan(sim_data['chan_l'][n])
        # or (sim_data['date'][n] != sim_data['date'][n + 1])

    def get_tradepos_exit(self, tradepos, sim_data, n):
        gap = (int((self.SL * sim_data['band_wth'][n-1]) / float(self.tick_base)) + 1) * float(self.tick_base)
        return gap

    def on_bar(self, sim_data, n):
        self.pos_args = {'reset_margin': 0}
        curr_pos = 0
        next_pos = (sim_data['high'][n] >= max(sim_data['band_up'][n], sim_data['chan_h'][n])) * 1 - \
                   (sim_data['low'][n] <= min(sim_data['band_dn'][n], sim_data['chan_l'][n])) * 1
        if len(self.positions)>0:
            curr_pos = self.positions[0].pos
            need_close = (self.close_daily or (self.scur_day == sim_data['date'][-1])) and (sim_data['min_id'][n] >= self.exit_min)
            if need_close or (curr_pos * next_pos < 0):
                for tradepos in self.positions:
                    self.close_tradepos(tradepos, sim_data['open'][n+1])
                self.positions = []
                curr_pos = 0
                if need_close:
                    return
            else:
                curr_pos = self.positions[0].pos
        if (curr_pos == 0) and next_pos != 0:
            self.open_tradepos([sim_data['contract'][n]], sim_data['open'][n+1], next_pos)

def gen_config_file(filename):
    sim_config = {}
    sim_config['sim_class']  = 'bktest.bktest_bband_trailstop.BBTrailStop'
    sim_config['sim_func'] = 'run_loop_sim'
    sim_config['scen_keys'] = ['boll_len', 'chan_ratio', 'band_ratio', 'stoploss']
    sim_config['sim_name']   = 'band_trailstop'
    sim_config['products']   = ['m', 'RM', 'y', 'p', 'a', 'rb', 'SR', 'TA', 'MA', 'i', 'ru', 'j' ]
    sim_config['start_date'] = '20160102'
    sim_config['end_date']   = '20170707'
    sim_config['boll_len'] = [80, 120, 160]
    sim_config['chan_ratio'] = [0.125, 0.25, 0.5]
    sim_config['band_ratio'] = [1.0, 1.5, 2.0]
    sim_config['stoploss'] = [0.5, 1.0, 1.5, 2.0]
    sim_config['pos_class'] = 'strat.TargetTrailTradePos'
    sim_config['offset']    = 1

    config = {'capital': 10000,
              'trans_cost': 0.0,
              'close_daily': False,
              'unit': 1,                           
              'pos_args': {},
              'freq': 3,
              'pos_update': True,
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
