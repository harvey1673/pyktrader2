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
    multiplier = config['param'][2]
    f = config['param'][3]
    combo_signal = config['combo_signal']
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
    xdf['tr'] = tr
    xdf['chan_h'] = chan_high(xdf, chan, **chan_func['high']['args'])
    xdf['chan_l'] = chan_low(xdf, chan, **chan_func['low']['args'])
    xdf['atr'] = dh.ATR(xdf, chan)
    xdf['ma'] = pd.rolling_mean(xdf.close, chan)
    xdata = pd.concat([xdf['tr'].shift(1), xdf['ma'].shift(1),
                       xdf['chan_h'].shift(1), xdf['chan_l'].shift(1),
                       xdf['open'], xdf['atr'].shift(1)], axis=1, keys=['tr','ma', 'chan_h', 'chan_l', 'xopen', 'atr']).fillna(0)
    mdf = mdf.join(xdata, how = 'left').fillna(method='ffill')
    rng = pd.DataFrame([min_rng * mdf['xopen'], k * mdf['tr']]).max()
    mdf['dt_signal'] = np.nan
    mdf.ix[mdf['high'] >= mdf['xopen'] + rng, 'dt_signal'] = 1
    mdf.ix[mdf['low'] <= mdf['xopen'] - rng, 'dt_signal'] = -1
    if close_daily:
        mdf.ix[ mdf['min_id'] >= config['exit_min'], 'dt_signal'] = 0
    addon_signal = copy.deepcopy(mdf['dt_signal'])
    mdf['dt_signal'] = mdf['dt_signal'].fillna(method='ffill').fillna(0)
    mdf['chan_sig'] = np.nan
    if combo_signal:
        mdf.ix[(mdf['high'] >= mdf['chan_h']) & (addon_signal > 0), 'chan_sig'] = 1
        mdf.ix[(mdf['low'] <= mdf['chan_l']) & (addon_signal < 0), 'chan_sig'] = -1
    else:
        mdf.ix[(mdf['high'] >= mdf['chan_h']), 'chan_sig'] = 1
        mdf.ix[(mdf['low'] <= mdf['chan_l']), 'chan_sig'] = -1
    mdf['chan_sig'] = mdf['chan_sig'].fillna(method='ffill').fillna(0)
    pos =  mdf['dt_signal'] * (unit[0] + (mdf['chan_sig'] * mdf['dt_signal'] > 0) * unit[1])
    mdf['pos'] = pos.shift(1).fillna(0)
    mdf.ix[-3:, 'pos'] = 0
    mdf['cost'] = abs(mdf['pos'] - mdf['pos'].shift(1)) * (offset + mdf['open'] * tcost)
    mdf['cost'] = mdf['cost'].fillna(0.0)
    mdf['traded_price'] = mdf['open']
    closed_trades = backtest.simdf_to_trades1(mdf, slippage = offset )
    return (mdf, closed_trades)

def gen_config_file(filename):
    sim_config = {}
    sim_config['sim_func']  = 'bktest.bkvec_dt_min.dual_thrust_sim'
    sim_config['scen_keys'] = ['param']
    sim_config['sim_name']   = 'DTdaily_1y'
    sim_config['products']   = ['rb', 'hc', 'i', 'j', 'jm', 'ZC', 'ni', 'ru', 'm', 'RM', 'FG', \
                                'y', 'p', 'OI', 'a', 'cs', 'c', 'jd', 'SR', 'pp', 'l', 'v',\
                                'TA', 'MA', 'ag', 'au', 'cu', 'al', 'zn', 'IF', 'IH', 'IC', 'TF', 'T']
    sim_config['start_date'] = '20151001'
    sim_config['end_date']   = '20160930'
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
    sim_config['pos_class'] = 'strat.TradePos'
    sim_config['proc_func'] = 'dh.day_split'
    sim_config['offset']    = 1
    #chan_func = {'high': {'func': 'dh.PCT_CHANNEL', 'args':{'pct': 90, 'field': 'high'}},
    #             'low':  {'func': 'dh.PCT_CHANNEL', 'args':{'pct': 10, 'field': 'low'}},
    #             }
    chan_func = {'high': {'func': 'dh.DONCH_H', 'args':{}},
                 'low':  {'func': 'dh.DONCH_L', 'args':{}},
                 }
    config = {'capital': 10000,
              'trans_cost': 0.0,
              'close_daily': False,
              'combo_signal': False,
              'chan': 5,
              'unit': [1, 0],
              'stoploss': 0.0,
              'min_range': 0.0035,
              'pos_args': {},
              'proc_args': {'minlist':[]},
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
