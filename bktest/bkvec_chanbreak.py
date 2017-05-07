import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)
import data_handler as dh
import pandas as pd
import numpy as np
import backtest
import sys
import json

def chanbreak_sim( mdf, config):
    freq = config['freq']
    str_freq = str(freq) + 'Min'
    xdf = dh.conv_ohlc_freq(mdf, str_freq)
    tcost = config['trans_cost']
    offset = config['offset']
    win = config['win']
    chan_func = config['channel_func']
    upper_chan_func = eval(chan_func[0])
    lower_chan_func = eval(chan_func[1])
    entry_chan = win[0]    
    exit_chan =  win[1]
    exit_min = config.get('exit_min', 2057)
    close_daily = config.get('close_daily', False)
    stoploss = config.get('stoploss', 2.0)
    xdf['H1'] = upper_chan_func(xdf, entry_chan)
    xdf['L1'] = lower_chan_func(xdf, entry_chan)
    xdf['H2'] = upper_chan_func(xdf, exit_chan)
    xdf['L2'] = lower_chan_func(xdf, exit_chan)
    xdf['ATR'] = dh.ATR(xdf, entry_chan)
    xdata = pd.concat([xdf['H1'], xdf['L1'], xdf['H2'], xdf['L2'], xdf['ATR']], \
                      axis=1, keys=['H1', 'L1', 'H2', 'L2', 'ATR']).shift(1)
    mdf = mdf.join(xdata, how = 'left').fillna(method='ffill')
    mdf['close_ind'] = np.isnan(mdf['close'].shift(-3))
    if close_daily:
        mdf['close_ind'] = (mdf['min_id'] >= exit_min) | mdf['close_ind']
    long_signal = pd.Series(np.nan, index = mdf.index)
    long_signal[(mdf['open']>=mdf['H1'])] = 1
    long_signal[(mdf['open'] <= mdf['L2'])] = 0
    if stoploss > 0:
        long_signal[(mdf['open'] <= mdf['H1']-mdf['ATR'] * stoploss)] = 0
    long_signal[mdf['close_ind']] = 0
    long_signal = long_signal.fillna(method='ffill').fillna(0)
    short_signal = pd.Series(np.nan, index = mdf.index)
    short_signal[(mdf['open']<=mdf['L1'])] = -1
    short_signal[(mdf['open']>=mdf['H2'])] = 0
    if stoploss > 0:
        short_signal[(mdf['open'] >= mdf['L1'] + mdf['ATR'] * stoploss)] = 0
    short_signal[mdf['close_ind']] = 0
    short_signal = short_signal.fillna(method='ffill').fillna(0)
    mdf['pos'] = long_signal + short_signal
    mdf['cost'] = abs(mdf['pos'] - mdf['pos'].shift(1)) * (offset + mdf['open'] * tcost)
    mdf['cost'] = mdf['cost'].fillna(0.0)
    mdf['traded_price'] = mdf.open + (mdf['pos'] - mdf['pos'].shift(1)) * offset
    closed_trades = backtest.simdf_to_trades1(mdf, slippage = offset )
    return (mdf, closed_trades)

def gen_config_file(filename):
    sim_config = {}
    sim_config['sim_func']  = 'bktest.bkvec_chanbreak.chanbreak_sim'
    sim_config['scen_keys'] = ['freq', 'win']
    sim_config['sim_name']   = 'chanbreak_'
    sim_config['products']   = ['rb', 'hc', 'i', 'j', 'jm', 'ZC', 'ru', 'ni', 'y', 'p', 'OI', 'm', 'RM', \
                                'cs', 'jd', 'a', 'l', 'pp', 'v', 'TA', 'MA', 'bu', 'cu', 'al', 'zn', 'ag', 'au',\
                                'IF', 'IH', 'IC', 'TF', 'T']
    sim_config['start_date'] = '20150102'
    sim_config['end_date']   = '20161230'
    sim_config['need_daily'] = False
    sim_config['freq'] = [150, 60, 30, 15]
    sim_config['win'] =[[20, 10], [30, 10], [40, 10], [40, 20], [60, 20], [80, 20]]
    sim_config['offset']    = 1
    config = {'capital': 10000,
              'trans_cost': 0.0,
              'unit': 1,
              'stoploss': 0.0,
              'close_daily': False,
              'pos_update': False,
              'channel_func': ['dh.DONCH_H', 'dh.DONCH_L'],
              'MA_func': ['dh.MA'],
              'exit_min': 2055,
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
