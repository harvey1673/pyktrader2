import misc
import json
import data_handler as dh
import pandas as pd
import numpy as np
import strategy as strat
import datetime
import backtest
import sys

def MA_sim( mdf, config):
    offset = config['offset']
    pos_class = config['pos_class']
    pos_args  = config['pos_args']
    pos_update = config.get('pos_update', False)
    stoploss = config.get('stoploss', 0.0)
    ma_list = config['ma_list']
    param = config['param']
    corr_entry = param[0]
    corr_exit = param[1]
    pval_entry = param[2]
    pval_exit = param[3]
    if len(param)>=5:
        channel = param[4]
    else:
        channel = 0
    if channel == 0:
        use_chan = False
    else:
        use_chan = True
    close_daily = config['close_daily']
    tcost = config['trans_cost']
    unit = config['unit']
    freq = config['freq']   
    if int(freq[:-3]) == 1:
        xdf = mdf
    else:
        xdf = dh.conv_ohlc_freq(mdf, freq, extra_cols=['contract'])
    if use_chan:
        xdf['chan_high'] = eval(config['channel_func'][0])(xdf, channel, **config['channel_args'][0]).shift(2)
        xdf['chan_low'] = eval(config['channel_func'][1])(xdf, channel, **config['channel_args'][1]).shift(2)
    else:
        xdf['chan_high'] = pd.Series(index = xdf.index)
        xdf['chan_low'] = pd.Series(index = xdf.index)
    ma_ribbon = dh.MA_RIBBON(xdf, ma_list)
    ribbon_corr = ma_ribbon["MARIBBON_CORR"].shift(1)
    ribbon_pval = ma_ribbon["MARIBBON_PVAL"].shift(1)
    ribbon_dist = ma_ribbon["MARIBBON_DIST"].shift(1)
    xdf['prev_close'] = xdf['close'].shift(1)
    xdf['close_ind'] = np.isnan(xdf['close'].shift(-1))
    if close_daily:
        daily_end = (xdf['date']!=xdf['date'].shift(-1))
        xdf['close_ind'] = xdf['close_ind'] | daily_end
    long_signal = pd.Series(np.nan, index = xdf.index) 
    long_flag = (xdf.ribbon_corr >= corr_entry) & (xdf.ribbon_pval < pval_entry)
    if use_chan:
        long_flag = long_flag & (xdf['open'] >= xdf['chan_high'])
    long_signal[long_flag] = 1
    long_signal[(xdf.ribbon_corr < corr_exit) | (xdf.ribbon_pval > pval_exit)] = 0
    long_signal = long_signal.fillna(method='ffill').fillna(0)
    short_signal = pd.Series(np.nan, index = xdf.index)    
    short_flag = (xdf.ribbon_corr <= -corr_entry) & (xdf.ribbon_pval < pval_entry)
    if use_chan:
        short_flag = long_flag & (xdf['open'] <= xdf['chan_low'])    
    short_signal[short_flag] = -1
    short_signal[(xdf.ribbon_corr > -corr_exit) | (xdf.ribbon_pval > pval_exit)] = 0
    short_signal = short_signal.fillna(method='ffill').fillna(0)    
    if len(xdf[(long_signal>0) & (short_signal<0)])>0:
        print xdf[(long_signal > 0) & (short_signal < 0)]
        print "something wrong with the position as long signal and short signal happen the same time"    
    xdf['pos'] = long_signal + short_signal
    xdf['cost'] = abs(xdf['pos'] - xdf['pos'].shift(1)) * (offset + xdf['open'] * tcost)
    xdf['cost'] = xdf['cost'].fillna(0.0)
    xdf['traded_price'] = xdf.open + (xdf['pos'] - xdf['pos'].shift(1)) * offset
    closed_trades = backtest.simdf_to_trades1(xdf, slippage = offset )
    return (xdf, closed_trades)

def gen_config_file(filename):
    sim_config = {}
    sim_config['sim_func']  = 'bktest.bkvec__ma_ribbon.MA_sim'
    sim_config['scen_keys'] = ['freq', 'param']
    sim_config['sim_name']   = 'ribbon_customMA_'
    sim_config['products']   = ['rb', 'hc', 'i', 'j', 'jm', 'ZC', 'ru', 'ni', 'y', 'p', 'm', 'RM', \
                                'SR', 'cs', 'jd', 'a', 'l', 'pp', 'v', 'TA', 'MA', 'bu', 'cu', 'al', \
                                'ag', 'au', 'IF', 'IH', 'TF', 'T']
    sim_config['start_date'] = '20150102'
    sim_config['end_date']   = '20160819'
    sim_config['need_daily'] = False
    sim_config['freq'] = ['15min', '30min', '60min', '90min']
    sim_config['param'] =[[0, 0, 0.02, 0.2], [0, 0, 0.05, 0.2], [0, 0, 0.08, 0.2], [0, 0, 0.1, 0.2],\
                          [0, 0, 0.02, 0.3], [0, 0, 0.05, 0.3], [0, 0, 0.08, 0.3], [0, 0, 0.1, 0.3],\
                          [0, 0, 0.02, 0.4], [0, 0, 0.05, 0.4], [0, 0, 0.08, 0.4], [0, 0, 0.1, 0.4],]
    sim_config['pos_class'] = 'strat.TradePos'
    #sim_config['pos_class'] = 'strat.ParSARTradePos'
    #sim_config['pos_args'] = [{'reset_margin': 1, 'af': 0.02, 'incr': 0.02, 'cap': 0.2},\
    #                            {'reset_margin': 2, 'af': 0.02, 'incr': 0.02, 'cap': 0.2},\
    #                            {'reset_margin': 3, 'af': 0.02, 'incr': 0.02, 'cap': 0.2},\
    #                            {'reset_margin': 1, 'af': 0.01, 'incr': 0.01, 'cap': 0.2},\
    #                            {'reset_margin': 2, 'af': 0.01, 'incr': 0.01, 'cap': 0.2},\
    #                            {'reset_margin': 3, 'af': 0.01, 'incr': 0.01, 'cap': 0.2}]
    sim_config['offset']    = 1
    config = {'capital': 10000,              
              'trans_cost': 0.0,
              'unit': 1,
              'ma_list': range(10, 160, 10),
              'trade_ind': 'MARIBBON_CORR',
              'use_chan': False, 
              'stoploss': 0.0,
              'close_daily': False,
              'pos_update': False,
              'MA_func': 'dh.EMA',
              'channel_func': ['dh.DONCH_H', 'dh.DONCH_L'],
              'channel_args': [{}, {}],              
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
