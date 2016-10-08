import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)
import json
import misc
import copy
import data_handler as dh
import pandas as pd
import numpy as np
import strategy as strat
import datetime
import backtest

def dual_thrust_sim( mdf, config):
    close_daily = config['close_daily']
    offset = config['offset']
    k = config['param'][0]
    win = config['param'][1]
    proc_func = config['proc_func']
    proc_args = config['proc_args']
    chan_func = config['chan_func']
    chan_high = eval(chan_func['high']['func'])
    chan_low  = eval(chan_func['low']['func'])
    tcost = config['trans_cost']
    min_rng = config['min_range']
    chan = config['chan']
    xdf = proc_func(mdf, **proc_args)
    tr= pd.concat([pd.rolling_max(xdf.high, win) - pd.rolling_min(xdf.close, win), 
                   pd.rolling_max(xdf.close, win) - pd.rolling_min(xdf.low, win)], 
                   join='outer', axis=1).max(axis=1)
    xdf['tr'] = tr
    xdf['chan_h'] = chan_high(xdf, chan, **chan_func['high']['args'])
    xdf['chan_l'] = chan_low(xdf, chan, **chan_func['low']['args'])
    #sar_param = config['sar_param']
    #sar = dh.SAR(xdf, **sar_param)
    #sar_signal = pd.Series(0, index = sar.index)
    #sar_signal[(sar < xdf['close'])] = 1
    #sar_signal[(sar > xdf['close'])] = -1
    #xdf['atr'] = dh.ATR(xdf, chan)
    xdata = pd.concat([xdf['tr'].shift(1), xdf['chan_h'].shift(1), xdf['chan_l'].shift(1),
                       xdf['open']], axis=1, keys=['tr','chan_h', 'chan_l', 'xopen'])
    mdf = mdf.join(xdata, how = 'left').fillna(method='ffill')
    rng = pd.DataFrame([min_rng * mdf['xopen'], k * mdf['tr']]).max()
    long_signal = pd.Series(np.nan, index = mdf.index)
    long_signal[(mdf['high'] >= mdf['xopen'] + rng) & (mdf['high'] >= mdf['chan_h']) ] = 1
    long_signal[(mdf['low'] <= mdf['xopen'] - rng) | (mdf['low'] <= mdf['chan_l'])] = 0
    if close_daily:
        long_signal[(mdf['min_id']>=config['exit_min'])] = 0
    long_signal = long_signal.shift(1)
    long_signal = long_signal.fillna(method='ffill').fillna(0)
    short_signal = pd.Series(np.nan, index = mdf.index)
    short_signal[(mdf['low'] <= mdf['xopen'] - rng) & (mdf['low'] <= mdf['chan_l']) ] = -1
    short_signal[(mdf['high'] >= mdf['xopen'] + rng) | (mdf['high'] >= mdf['chan_h'])] = 0
    if close_daily:
        short_signal[(mdf['min_id']>=config['exit_min'])] = 0
    short_signal = short_signal.shift(1)
    short_signal = short_signal.fillna(method='ffill').fillna(0)
    if len(mdf[(long_signal>0)&(short_signal<0)]) > 0:
        print "Warning: long and short signal happen at the same time"
    mdf['pos'] = long_signal + short_signal
    mdf.ix[-3:, 'pos'] = 0
    mdf['cost'] = abs(mdf['pos'] - mdf['pos'].shift(1)) * (offset + mdf['open'] * tcost)
    mdf['cost'] = mdf['cost'].fillna(0.0)
    mdf['traded_price'] = mdf.open + (mdf['pos'] - mdf['pos'].shift(1)) * offset
    closed_trades = backtest.simdf_to_trades1(mdf, slippage = offset )
    return (mdf, closed_trades)

def gen_config_file(filename):
    sim_config = {}
    sim_config['sim_func']  = 'bktest.bkvec_dt_min.dual_thrust_sim'
    sim_config['scen_keys'] = ['param', 'chan']
    sim_config['sim_name']   = 'DTsplit3chan_1y'
    sim_config['products']   = ['rb', 'hc', 'i', 'j', 'jm', 'ZC', 'ni', 'ru', 'm', 'RM', 'FG', \
                                'y', 'p', 'OI', 'a', 'cs', 'c', 'jd', 'SR', 'pp', 'l', 'v',\
                                'TA', 'MA', 'ag', 'au', 'cu', 'al', 'zn', 'IF', 'IH', 'IC', 'TF', 'T']
    sim_config['start_date'] = '20151001'
    sim_config['end_date']   = '20160930'
    sim_config['param']  =  [
        (0.5, 1), (0.6, 1), (0.7, 1), (0.8, 1), (0.9, 1), (1.0, 1), (1.1, 1), \
        (0.2, 2), (0.25, 2), (0.3, 2), (0.35, 2),(0.4, 2), (0.45, 2),(0.5, 2), \
        (0.2, 4), (0.25, 4),(0.3, 4), (0.35, 4),(0.4, 4), (0.45, 4),(0.5, 4),\
        ]
    sim_config['pos_class'] = 'strat.TradePos'
    sim_config['proc_func'] = 'dh.day_split'
    sim_config['offset']    = 1
    sim_config['chan'] = [20, 40]
    #sim_config['sar_param'] = [{'incr': 0.005, 'maxaf': 0.02}, {'incr': 0.01, 'maxaf': 0.02}, \
    #                           {'incr': 0.01, 'maxaf': 0.1}, {'incr': 0.02, 'maxaf': 0.1}]
    #chan_func = {'high': {'func': 'dh.PCT_CHANNEL', 'args':{'pct': 75, 'field': 'high'}},
    #             'low':  {'func': 'dh.PCT_CHANNEL', 'args':{'pct': 25, 'field': 'low'}},
    #             }
    chan_func = {'high': {'func': 'dh.DONCH_H', 'args':{}},
                 'low':  {'func': 'dh.DONCH_L', 'args':{}},
                 }
    config = {'capital': 10000,
              'trans_cost': 0.0,
              'close_daily': False,           
              'stoploss': 0.0,
              'min_range': 0.002,
              'pos_args': {},
              'proc_args': {'minlist':[1500]},
              'pos_update': False,
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
