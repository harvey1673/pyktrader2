import misc
import json
import data_handler as dh
import pandas as pd
import numpy as np
import strategy as strat
import datetime
import backtest
import sys

def bband_chan_sim( mdf, config):
    start_equity = config['capital']
    marginrate = config['marginrate']
    offset = config['offset']
    pos_class = config['pos_class']
    pos_args  = config['pos_args']
    pos_update = config.get('pos_update', False)
    stoploss = config.get('stoploss', 0.0)
    param = config['param']
    std_func = eval(config['std_func'])
    #tick_base = config['tick_base']
    close_daily = config['close_daily']
    win = param[0]
    k = param[1]
    chan = param[2]
    stop_ratio = config.get('exit_stop', 0.0)
    k_e = k * stop_ratio
    if chan > 0:
        chan_func = config['chan_func']
    tcost = config['trans_cost']
    unit = config['unit']
    freq = config['freq']
    xdf = dh.conv_ohlc_freq(mdf, freq)
    xdf['boll_ma'] = dh.MA(xdf, win).shift(1)
    xdf['boll_std'] = std_func(xdf, win).shift(1)
    xdf['upbnd'] = xdf['boll_ma'] + xdf['boll_std'] * k
    xdf['lowbnd'] = xdf['boll_ma'] - xdf['boll_std'] * k
    xdf['up_exit'] = xdf['boll_ma'] + xdf['boll_std'] * k_e
    xdf['dn_exit'] = xdf['boll_ma'] - xdf['boll_std'] * k_e
    if chan > 0:
        xdf['chan_h'] = eval(chan_func['high']['func'])(xdf, chan, **chan_func['high']['args']).shift(1)
        xdf['chan_l'] = eval(chan_func['low']['func'])(xdf, chan, **chan_func['low']['args']).shift(1)
    else:
        xdf['chan_h'] = 0
        xdf['chan_l'] = 10000000
    xdf['high_band'] = xdf[['chan_h', 'upbnd']].max(axis=1)
    xdf['low_band'] = xdf[['chan_l', 'lowbnd']].min(axis=1)
    xdf['prev_close'] = xdf['close'].shift(1)
    xdf['close_ind'] = np.isnan(xdf['close'].shift(-1))
    if close_daily:
        daily_end = (xdf['date']!=xdf['date'].shift(-1))
        xdf['close_ind'] = xdf['close_ind'] | daily_end
    ll = xdf.shape[0]
    xdf['pos'] = 0
    xdf['cost'] = 0
    xdf['traded_price'] = xdf.open
    curr_pos = []
    closed_trades = []
    tradeid = 0
    for idx, dd in enumerate(xdf.index):
        mslice = xdf.loc[dd]
        if len(curr_pos) == 0:
            pos = 0
        else:
            pos = curr_pos[0].pos
        xdf.set_value(dd, 'pos', pos)
        if np.isnan(mslice.boll_ma) or np.isnan(mslice.chan_h):
            continue
        if mslice.close_ind:
            if pos!=0:
                curr_pos[0].close(mslice.open - misc.sign(pos) * offset, dd)
                tradeid += 1
                curr_pos[0].exit_tradeid = tradeid
                closed_trades.append(curr_pos[0])
                curr_pos = []
                xdf.set_value(dd, 'cost', xdf.at[dd, 'cost'] - abs(pos) * ( mslice.open * tcost))
                xdf.set_value(dd, 'traded_price', mslice.open - misc.sign(pos) * offset)
                pos = 0
        else:
            if ((mslice.open > mslice.up_exit) and (pos<0)) or ((mslice.open < mslice.dn_exit) and (pos>0)):
                curr_pos[0].close(mslice.open - misc.sign(pos) * offset, dd)
                tradeid += 1
                curr_pos[0].exit_tradeid = tradeid
                closed_trades.append(curr_pos[0])
                curr_pos = []
                xdf.set_value(dd, 'cost', xdf.at[dd, 'cost'] - abs(pos) * (mslice.open * tcost))
                xdf.set_value(dd, 'traded_price', mslice.open - misc.sign(pos) * offset)
                pos = 0
            if ((mslice.open >= mslice.high_band) or (mslice.open <= mslice.low_band)) and (pos==0):
                target_pos = ( mslice.open >= mslice.high_band) * unit - (mslice.open <= mslice.low_band) * unit
                new_pos = pos_class([mslice.contract], [1], target_pos, mslice.open, mslice.open, **pos_args)
                tradeid += 1
                new_pos.entry_tradeid = tradeid
                new_pos.open(mslice.open + misc.sign(target_pos)*offset, dd)
                curr_pos.append(new_pos)
                pos = target_pos
                xdf.set_value(dd, 'cost', xdf.at[dd, 'cost'] -  abs(target_pos) * (mslice.open * tcost))
                xdf.set_value(dd, 'traded_price', mslice.open + misc.sign(target_pos)*offset)
        if pos_update and pos != 0:
            if curr_pos[0].check_exit(mslice.open, stoploss * mslice.boll_std):
                curr_pos[0].close(mslice.open - misc.sign(pos) * offset, dd)
                tradeid += 1
                curr_pos[0].exit_tradeid = tradeid
                closed_trades.append(curr_pos[0])
                curr_pos = []
                xdf.set_value(dd, 'cost', xdf.at[dd, 'cost'] - abs(pos) * (mslice.open * tcost))
                xdf.set_value(dd, 'traded_price', mslice.open - misc.sign(pos) * offset)
                pos = 0
            else:
                curr_pos[0].update_bar(mslice)
        xdf.set_value(dd, 'pos', pos)
    return (xdf, closed_trades)

def gen_config_file(filename):
    sim_config = {}
    sim_config['sim_func']  = 'bktest_bband_chan.bband_chan_sim'
    sim_config['scen_keys'] = ['param', 'pos_args']
    sim_config['sim_name']   = 'BandChan_sar_30min_HL'
    sim_config['products']   = ['rb', 'i', 'j', 'jm', 'ZC', 'ru', 'ni', 'y', 'p', 'm', 'RM', 'cs', 'jd', 'a', 'l', 'pp', 'TA', 'MA', 'bu', 'cu', 'al', 'ag', 'au']
    sim_config['start_date'] = '20150102'
    sim_config['end_date']   = '20160608'
    sim_config['need_daily'] = False

    sim_config['param'] = [(20, 1, 5), (20, 1, 10), (20, 1, 20), (20, 1, 40), (20, 1.25, 5), (20, 1.25, 10), (20, 1.25, 20), (20, 1.25, 40), \
                           (20, 1.5, 5), (20, 1.5, 10), (20, 1.5, 20), (20, 1.5, 40), (20, 2, 5), (20, 2, 10), (20, 2, 20), (20, 2, 40),\
                           (40, 1, 10), (40, 1, 20), (40, 1, 40), (40, 1, 80), (40, 1.25, 10), (40, 1.25, 20), (40, 1.25, 40), (40, 1.25, 80), \
                           (40, 1.5, 10), (40, 1.5, 20), (40, 1.5, 40), (40, 1.5, 80), (40, 2, 10), (40, 2, 20), (40, 2, 40), (40, 2, 80), \
                           (80, 1, 10), (80, 1, 20), (80, 1, 40), (80, 1, 80), (80, 1.25, 10), (80, 1.25, 20), (80, 1.25, 40), (80, 1.25, 80), \
                           (80, 1.5, 10), (80, 1.5, 20), (80, 1.5, 40), (80, 1.5, 80), (80, 2, 10), (80, 2, 20), (80, 2, 40), (80, 2, 80) ]
    sim_config['pos_class'] = 'strat.ParSARTradePos'
    sim_config['pos_args'] = [{'reset_margin': 1, 'af': 0.02, 'incr': 0.02, 'cap': 0.2},\
                                {'reset_margin': 2, 'af': 0.02, 'incr': 0.02, 'cap': 0.2},\
                                {'reset_margin': 3, 'af': 0.02, 'incr': 0.02, 'cap': 0.2},\
                                {'reset_margin': 1, 'af': 0.01, 'incr': 0.01, 'cap': 0.2},\
                                {'reset_margin': 2, 'af': 0.01, 'incr': 0.01, 'cap': 0.2},\
                                {'reset_margin': 3, 'af': 0.01, 'incr': 0.01, 'cap': 0.2}]
    sim_config['offset']    = 1
    chan_func = { 'high': {'func': 'dh.DONCH_H', 'args':{'field': 'high'}},
                  'low':  {'func': 'dh.DONCH_L', 'args':{'field': 'low'}}}
    config = {'capital': 10000,
              'freq': '30min',
              'trans_cost': 0.0,
              'unit': 1,
              'stoploss': 0.0,
              'exit_stop': 0.0,
              'close_daily': False,
              'pos_update': True,
              'std_func': 'dh.STDEV',
              'exit_min': 2055,
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
