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
    win_list = config['param']
    MA_func = eval(config['MA_func'])
    close_daily = config['close_daily']
    tcost = config['trans_cost']
    unit = config['unit']
    freq = config['freq']
    xdf = dh.conv_ohlc_freq(mdf, freq)
    for idx, win in enumerate(win_list):
        xdf['MA'+str(idx)] = MA_func(xdf, win).shift(1)
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
            if ((mslice.open > mslice.boll_ma) and (pos<0)) or ((mslice.open < mslice.boll_ma) and (pos>0)):
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
    sim_config['sim_func']  = 'bktest_MA_system.MA_sim'
    sim_config['scen_keys'] = ['param']
    sim_config['sim_name']   = 'MAsim_30min'
    sim_config['products']   = ['rb', 'i', 'j', 'jm', 'ZC', 'ru', 'ni', 'y', 'p', 'm', 'RM', 'cs', 'jd', 'a', 'l', 'pp', 'TA', 'MA', 'bu', 'cu', 'al', 'ag', 'au']
    sim_config['start_date'] = '20150102'
    sim_config['end_date']   = '20160608'
    sim_config['need_daily'] = False
    sim_config['param'] = [ [5, 20, 80], [10, 20, 40], ]
    sim_config['pos_class'] = 'strat.TradePos'
    sim_config['pos_args'] = {}
    #sim_config['pos_class'] = 'strat.ParSARTradePos'
    #sim_config['pos_args'] = [{'reset_margin': 1, 'af': 0.02, 'incr': 0.02, 'cap': 0.2},\
    #                            {'reset_margin': 2, 'af': 0.02, 'incr': 0.02, 'cap': 0.2},\
    #                            {'reset_margin': 3, 'af': 0.02, 'incr': 0.02, 'cap': 0.2},\
    #                            {'reset_margin': 1, 'af': 0.01, 'incr': 0.01, 'cap': 0.2},\
    #                            {'reset_margin': 2, 'af': 0.01, 'incr': 0.01, 'cap': 0.2},\
    #                            {'reset_margin': 3, 'af': 0.01, 'incr': 0.01, 'cap': 0.2}]
    sim_config['offset']    = 1
    config = {'capital': 10000,
              'freq': '30min',
              'trans_cost': 0.0,
              'unit': 1,
              'stoploss': 0.0,
              'close_daily': False,
              'pos_update': False,
              'MA_func': 'dh.MA',
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
