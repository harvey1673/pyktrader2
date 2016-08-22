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
    use_chan = config['use_chan']
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
    chan_ratio = config['channel_ratio']
    channel = int(chan_ratio * win_list[-1])
    xdf = dh.conv_ohlc_freq(mdf, freq, extra_cols=['contract'])
    for idx, win in enumerate(win_list):
        xdf['MA'+str(idx)] = MA_func(xdf, win).shift(1)
    if use_chan:
        xdf['chan_high'] = eval(config['channel_func'][0])(xdf, channel, **config['channel_args'][0]).shift(2)
        xdf['chan_low'] = eval(config['channel_func'][1])(xdf, channel, **config['channel_args'][1]).shift(2)
    else:
        xdf['chan_high'] = pd.Series(index = xdf.index)
        xdf['chan_low'] = pd.Series(index = xdf.index)
    tot_MA = len(win_list)
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
        ma_list = [getattr(mslice, 'MA'+str(i)) for i in range(len(win_list))]
        ma_short = ma_list[0]
        ma_last = ma_list[-1]
        if len(curr_pos) == 0:
            pos = 0
        else:
            pos = curr_pos[0].pos
        xdf.set_value(dd, 'pos', pos)
        if np.isnan(getattr(mslice, "MA"+str(tot_MA-1))):
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
            if (((ma_short >= ma_last) or (mslice.open >= mslice.chan_high)) and (pos<0)) or (((ma_short <= ma_last) or (mslice.open <=mslice.chan_low)) and (pos>0)):
                curr_pos[0].close(mslice.open - misc.sign(pos) * offset, dd)
                tradeid += 1
                curr_pos[0].exit_tradeid = tradeid
                closed_trades.append(curr_pos[0])
                curr_pos = []
                xdf.set_value(dd, 'cost', xdf.at[dd, 'cost'] - abs(pos) * (mslice.open * tcost))
                xdf.set_value(dd, 'traded_price', mslice.open - misc.sign(pos) * offset)
                pos = 0
            if (((ma_short >= ma_list[1]) and (ma_short >= ma_last) and ((use_chan == False) or (mslice.open>=mslice.chan_high))) or \
                        ((ma_short <= ma_list[1]) and (ma_short <= ma_last) and ((use_chan == False) or (mslice.open<=mslice.chan_low)))) and (pos==0):
                target_pos = ((ma_short >= ma_list[1]) and (ma_short >= ma_last) and ((use_chan == False) or (mslice.open>=mslice.chan_high))) * unit \
                             - ((ma_short <= ma_list[1]) and (ma_short <= ma_last) and ((use_chan == False) or (mslice.open<=mslice.chan_low))) * unit
                new_pos = pos_class([mslice.contract], [1], target_pos, mslice.open, mslice.open, **pos_args)
                tradeid += 1
                new_pos.entry_tradeid = tradeid
                new_pos.open(mslice.open + misc.sign(target_pos)*offset, dd)
                curr_pos.append(new_pos)
                pos = target_pos
                xdf.set_value(dd, 'cost', xdf.at[dd, 'cost'] -  abs(target_pos) * (mslice.open * tcost))
                xdf.set_value(dd, 'traded_price', mslice.open + misc.sign(target_pos)*offset)
        xdf.set_value(dd, 'pos', pos)
    return (xdf, closed_trades)

def gen_config_file(filename):
    sim_config = {}
    sim_config['sim_func']  = 'bktest_MA_system.MA_sim'
    sim_config['scen_keys'] = ['freq', 'param']
    sim_config['sim_name']   = 'EMAsim_mixed'
    sim_config['products']   = ['rb', 'i', 'j', 'jm', 'ZC', 'ru', 'ni', 'y', 'p', 'm', 'RM', 'cs', 'jd', 'a', 'l', 'pp', 'TA', 'MA', 'bu', 'cu', 'al', 'ag', 'au']
    sim_config['start_date'] = '20150102'
    sim_config['end_date']   = '20160708'
    sim_config['need_daily'] = False
    sim_config['freq'] = ['3min', '5min', '15min', '30min', '60min']
    sim_config['param'] = [ [5,  10, 20], [5, 10, 40], [5, 20, 40], [5, 20, 80], \
                             [10, 20, 40], [10, 20, 80],[10, 30, 60],[10, 30, 120],\
                             [10, 40, 80], [10, 40, 120],\
                             [5, 10], [5, 20], [5, 40], \
                             [10, 20], [10, 30], [10, 40] ]
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
              'use_chan': True, 
              'stoploss': 0.0,
              'close_daily': False,
              'pos_update': False,
              'MA_func': 'dh.EMA',
              'channel_func': ['dh.DONCH_H', 'dh.DONCH_L'],
              'channel_args': [{}, {}],
              'channel_ratio': 0.5,
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
