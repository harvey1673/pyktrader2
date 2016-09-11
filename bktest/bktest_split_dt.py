import sys
import json
import misc
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
    pos_update = config['pos_update']
    pos_class = config['pos_class']
    pos_args  = config['pos_args']
    proc_func = config['proc_func']
    proc_args = config['proc_args']
    rev_buffer = config.get('rev_buffer', 0)
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
    ll = mdf.shape[0]
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
    xdf['chan_h'] = chan_high(xdf, chan, **chan_func['high']['args'])
    xdf['chan_l'] = chan_low(xdf, chan, **chan_func['low']['args'])
    xdf['ATR'] = dh.ATR(xdf, chan)
    xdf['MA'] = pd.rolling_mean(xdf.close, chan)
    xdata = pd.concat([xdf['TR'].shift(1), xdf['MA'].shift(1),
                       xdf['chan_h'].shift(1), xdf['chan_l'].shift(1),
                       xdf['open'], xdf['ATR'].shift(1)], axis=1, keys=['tr','ma', 'chan_h', 'chan_l', 'xopen', 'atr']).fillna(0)
    mdf = mdf.join(xdata, how = 'left').fillna(method='ffill')
    rng = pd.DataFrame([min_rng * mdf['xopen'], k * mdf['TR']]).max()
    mdf['signal'] = np.nan
    mdf.ix[mdf['high'] >= mdf['xopen'] + rng, 'signal'] = 1
    mdf.ix[mdf['low'] <= mdf['xopen'] - rng, 'signal'] = -1
    if close_daily:
        mdf.ix[ mdf['min_id'] >= config['exit_min'], 'signal'] = 0
    mdf.ix[-3:, 'pos'] = 0
    mdf['signal'].fillna(method='ffill')
    mdf['signal'].fillna(0)
    mdf['pos'] = mdf['signal'].shift(1)
    mdf['cost'] = abs(mdf['pos'] - mdf['pos'].shift(1)) * (offset + mdf['open'] * tcost)
    mdf['traded_price'] = mdf['open']
    trade_df = mdf[mdf['pos']!= mdf['pos'].shift(1)]
    closed_trades = backtest.conv_simdf_to_tradelist(trade_df)
    return (mdf, closed_trades)

def gen_config_file(filename):
    sim_config = {}
    sim_config['sim_func']  = 'bktest_split_dt.dual_thrust_sim'
    sim_config['scen_keys'] = ['param', 'rev_buffer']
    sim_config['sim_name']   = 'DTsplit'
    sim_config['products']   = ['y', 'p', 'a', 'rb', 'SR', 'TA', 'MA', 'i', 'ni', 'j', 'jm', 'ag', 'cu', 'au', 'm', 'RM', 'ru']
    sim_config['start_date'] = '20150105'
    sim_config['end_date']   = '20160603'
    sim_config['rev_buffer'] = [0, 0.5, 1, 1.5, 2]
    sim_config['param']  =  [
            (0.5, 1, 0.5, 0.0), (0.6, 1, 0.5, 0.0), (0.7, 1, 0.5, 0.0), (0.8, 1, 0.5, 0.0), \
            (0.9, 1, 0.5, 0.0), (1.0, 1, 0.5, 0.0), (1.1, 1, 0.5, 0.0), \
            #(0.2, 2, 0.5, 0.0), (0.25,2, 0.5, 0.0), (0.3, 2, 0.5, 0.0), (0.35, 2, 0.5, 0.0),\
            #(0.4, 2, 0.5, 0.0), (0.45, 2, 0.5, 0.0),(0.5, 2, 0.5, 0.0), \
            #(0.2, 4, 0.5, 0.0), (0.25, 4, 0.5, 0.0),(0.3, 4, 0.5, 0.0), (0.35, 4, 0.5, 0.0),\
            #(0.4, 4, 0.5, 0.0), (0.45, 4, 0.5, 0.0),(0.5, 4, 0.5, 0.0),\
            ]
    sim_config['pos_class'] = 'strat.TradePos'
    sim_config['proc_func'] = 'dh.day_split'
    sim_config['offset']    = 1
    chan_func = {'high': {'func': 'dh.DONCH_H', 'args':{}},
                 'low':  {'func': 'dh.DONCH_L', 'args':{}},
                 }
    config = {'capital': 10000,
              'use_chan': False,
              'chan': 10,
              'trans_cost': 0.0,
              'close_daily': False,
              'unit': 1,
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
