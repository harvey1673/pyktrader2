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
        self.band_ratio = config['band_rato']
        self.ma_func = eval(config.get('ma_func', 'dh.MA'))
        self.band_func = eval(config.get('band_func', 'dh.ATR'))
        self.boll_len = config['boll_len']
        self.chan_len = config['chan_len']
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
            xdf['chan_h'] = dh.DONCH_H(xdf, n = self.chan_len, field = 'high').shift(1)
            xdf['chan_l'] = dh.DONCH_L(xdf, n = self.chan_len, field = 'low').shift(1)
        else:
            xdf['chan_h'] = -10000000
            xdf['chan_l'] = 10000000
        xdata = pd.concat([xdf['band_up'], xdf['band_dn'], xdf['band_mid'], xdf['band_wth'], \
                           xdf['chan_h'], xdf['chan_l']], xdf['high'], xdf['low'], axis=1, \
                           keys=['band_up','band_dn', 'band_mid', 'band_wth', \
                                 'chan_h', 'chan_l', 'xhigh', 'xlow'])
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
        next_pos = (sim_data['close'][n] > sim_data['band_up']) * 1 - (sim_data['RSI'][n] < 50.0 - self.rsi_trigger) * 1
        if len(self.positions)>0:
            curr_pos = self.positions[0].pos
            need_close = (self.close_daily or (self.scur_day == sim_data['date'][-1])) and (sim_data['min_id'][n] >= self.exit_min)
            if need_close or (self.reverse_flag and (curr_pos * next_pos < 0)):
                for tradepos in self.positions:
                    self.close_tradepos(tradepos, sim_data['open'][n+1])
                self.positions = []
                curr_pos = 0
                if need_close:
                    return
            else:
                curr_pos = self.positions[0].pos
        target_pos = next_pos * (sim_data['ATR'][n] > sim_data['ATRMA'][n])
        if (curr_pos == 0) and target_pos != 0:
            self.open_tradepos([sim_data['contract'][n]], sim_data['open'][n+1], target_pos)

def gen_config_file(filename):
    sim_config = {}
    sim_config['sim_class']  = 'bktest_rsiatr2.RSIATRSim'
    sim_config['sim_func'] = 'run_loop_sim'
    sim_config['scen_keys'] = ['freq', 'stoploss']
    sim_config['sim_name']   = 'RSI_ATR'
    sim_config['products']   = ['m', 'RM', 'y', 'p', 'a', 'rb', 'SR', 'TA', 'MA', 'i', 'ru', 'j' ]
    sim_config['start_date'] = '20160102'
    sim_config['end_date']   = '20170607'
    sim_config['stoploss'] = [3.0, 6.0, 9.0]
    sim_config['freq'] = [3, 5, 15]
    sim_config['pos_class'] = 'strat.TargetTrailTradePos'
    sim_config['offset']    = 1

    config = {'capital': 10000,
              'trans_cost': 0.0,
              'close_daily': False,
              'unit': 1,                           
              'pos_args': {},
              'pos_update': True,
              'atr_period': 22,
              'atrma_period': 10, 
              'rsi_len': 5,
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
