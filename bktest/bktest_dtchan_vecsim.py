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

class DTChanSim(StratSim):
    def __init__(self, config):
        super(DTChanSim, self).__init__(config)

    def process_config(self, config): 
        self.close_daily = config['close_daily']
        self.offset = config['offset']
        self.tick_base = config['tick_base']
        self.k = config['param'][0]
        self.win = config['param'][1]
        self.multiplier = config['param'][2]
        self.f = config['param'][3]
        self.price_mode = config.get('mode','TP')
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
        self.machan = config['machan']
        self.use_chan = (self.machan > 0)
        self.no_trade_set = config['no_trade_set']
        self.pos_freq = config.get('pos_freq', 1)
        self.exit_min = config.get('exit_min', 2058)
        self.buy_trig = 0.0
        self.sell_trig = 0.0
        self.combo_signal = config.get('combo', True)
     
    def process_data(self, mdf):
        self.df = mdf
    
    def run_vec_sim(self):
        xdf = self.proc_func(self.df, **self.proc_args)
        if self.win == -1:
            tr= pd.concat([xdf.high - xdf.low, abs(xdf.close - xdf.close.shift(1))], 
                          join='outer', axis=1).max(axis=1)
        elif self.win == 0:
            tr = pd.concat([(xdf.high.rolling(2).max() - xdf.close.rolling(2).min()) * self.multiplier,
                            (xdf.close.rolling(2).max() - xdf.low.rolling(2).min()) * self.multiplier,
                            xdf.high - xdf.close, 
                            xdf.close - xdf.low], 
                            join='outer', axis=1).max(axis=1)
        else:
            tr= pd.concat([xdf.high.rolling(self.win).max() - xdf.close.rolling(self.win).min(),
                            xdf.close.rolling(self.win).max() - xdf.low.rolling(self.win).min()],
                            join='outer', axis=1).max(axis=1)
        xdf['tr'] = tr
        xdf['chan_h'] = self.chan_high(xdf, self.chan, **self.chan_func['high']['args'])
        xdf['chan_l'] = self.chan_low(xdf, self.chan, **self.chan_func['low']['args'])
        #xdf['atr'] = dh.ATR(xdf, self.machan)
        xdf['ma'] = xdf.close.rolling(max(self.machan, 1)).mean()
        xdf['rng'] = pd.DataFrame([self.min_rng * xdf['open'], self.k * xdf['tr'].shift(1)]).max()
        xdf['upper'] = xdf['open'] + xdf['rng'] * (1 + ((xdf['open'] < xdf['ma'].shift(1)) & self.use_chan) *self.f)
        xdf['lower'] = xdf['open'] - xdf['rng'] * (1 + ((xdf['open'] > xdf['ma'].shift(1)) & self.use_chan) *self.f)
        xdata = pd.concat([xdf['upper'], xdf['lower'],
                           xdf['chan_h'].shift(1), xdf['chan_l'].shift(1),
                           xdf['open']], axis=1, keys=['upper','lower', 'chan_h', 'chan_l', 'xopen']).fillna(0)
        mdf = self.df.join(xdata, how = 'left').fillna(method='ffill')
        mdf['dt_signal'] = np.nan
        if self.price_mode == "HL":
            up_price = mdf['high']
            dn_price = mdf['low']
        elif self.price_mode == "TP":
            up_price = (mdf['high'] + mdf['low'] + mdf['close'])/3.0
            dn_price = up_price
        elif self.price_mode == "CL":
            up_price = mdf['close']
            dn_price = mdf['close']
        else:
            print "unsupported price mode"
        mdf.ix[up_price >= mdf['upper'], 'dt_signal'] = 1
        mdf.ix[dn_price <= mdf['lower'], 'dt_signal'] = -1
        if self.close_daily:
            mdf.ix[ mdf['min_id'] >= self.exit_min, 'dt_signal'] = 0
        addon_signal = copy.deepcopy(mdf['dt_signal'])
        mdf['dt_signal'] = mdf['dt_signal'].fillna(method='ffill').fillna(0)
        mdf['chan_sig'] = np.nan
        if self.combo_signal:
            mdf.ix[(up_price >= mdf['chan_h']) & (addon_signal > 0), 'chan_sig'] = 1
            mdf.ix[(dn_price <= mdf['chan_l']) & (addon_signal < 0), 'chan_sig'] = -1
        else:
            mdf.ix[(mdf['high'] >= mdf['chan_h']), 'chan_sig'] = 1
            mdf.ix[(mdf['low'] <= mdf['chan_l']), 'chan_sig'] = -1
        mdf['chan_sig'] = mdf['chan_sig'].fillna(method='ffill').fillna(0)
        pos =  mdf['dt_signal'] * (self.unit[0] + (mdf['chan_sig'] * mdf['dt_signal'] > 0) * self.unit[1])
        mdf['pos'] = pos.shift(1).fillna(0)
        mdf.ix[-3:, 'pos'] = 0
        mdf['cost'] = abs(mdf['pos'] - mdf['pos'].shift(1)) * (self.offset + mdf['open'] * self.tcost)
        mdf['cost'] = mdf['cost'].fillna(0.0)
        mdf['traded_price'] = mdf['open']
        self.closed_trades = simdf_to_trades1(mdf, slippage = self.offset )
        return ([mdf], self.closed_trades)

def gen_config_file(filename):
    sim_config = {}
    sim_config['sim_class']  = 'bktest_dtchan_vecsim.DTChanSim'
    sim_config['sim_func'] = 'run_vec_sim'
    sim_config['scen_keys'] = ['param', 'chan']
    sim_config['sim_name']   = 'DTChan_VecSim'
    sim_config['products']   = ['m', 'RM', 'y', 'p', 'a', 'rb', 'SR', 'TA', 'MA', 'i', 'ru', 'j' ]
    sim_config['start_date'] = '20150102'
    sim_config['end_date']   = '20170428'
    sim_config['param']  =  [
            (0.5, 0, 0.5, 0.0), (0.6, 0, 0.5, 0.0), (0.7, 0, 0.5, 0.0), (0.8, 0, 0.5, 0.0), \
            (0.9, 0, 0.5, 0.0), (1.0, 0, 0.5, 0.0), (1.1, 0, 0.5, 0.0), \
            (0.5, 1, 0.5, 0.0), (0.6, 1, 0.5, 0.0), (0.7, 1, 0.5, 0.0), (0.8, 1, 0.5, 0.0), \
            (0.9, 1, 0.5, 0.0), (1.0, 1, 0.5, 0.0), (1.1, 1, 0.5, 0.0), \
            (0.2, 2, 0.5, 0.0), (0.25,2, 0.5, 0.0), (0.3, 2, 0.5, 0.0), (0.35, 2, 0.5, 0.0),\
            (0.4, 2, 0.5, 0.0), (0.45, 2, 0.5, 0.0),(0.5, 2, 0.5, 0.0), \
            (0.2, 4, 0.5, 0.0), (0.25, 4, 0.5, 0.0),(0.3, 4, 0.5, 0.0), (0.35, 4, 0.5, 0.0),\
            (0.4, 4, 0.5, 0.0), (0.45, 4, 0.5, 0.0),(0.5, 4, 0.5, 0.0),\
            ]
    sim_config['chan'] = [3, 5, 10, 15, 20]
    sim_config['pos_class'] = 'trade_position.TradePos'
    sim_config['proc_func'] = 'dh.day_split'
    sim_config['offset']    = 1
    chan_func = {'high': {'func': 'dh.DONCH_H', 'args':{}},
                 'low':  {'func': 'dh.DONCH_L', 'args':{}},
                 }
    config = {'capital': 10000,              
              'use_chan': True,
              'trans_cost': 0.0,
              'close_daily': False,
              'unit': 1,              
              'min_range': 0.0035,
              'proc_args': {'minlist':[1500]},                           
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
