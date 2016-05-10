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
    param = config['param']
    tick_base = config['tick_base']
    close_daily = config['close_daily']
    win = param[0]
    k = param[1]
    chan = param[2]
    if chan > 0:
        chan_func = config['chan_func']
    tcost = config['trans_cost']
    unit = config['unit']
    freq = config['freq']
    xdf = dh.conv_ohlc_freq(mdf, freq)
    xdf['boll_ma'] = dh.MA(xdf, win)
    boll_std = dh.STDDEV(xdf, win)
    xdf['upbnd'] = np.ceil((xdf['boll_ma'] + boll_std * k)/tick_base) * tick_base
    xdf['lowbnd'] = np.floor((xdf['boll_ma'] - boll_std * k)/tick_base) * tick_base
    if chan > 0:
        xdf['chan_h'] = eval(chan_func['high']['func'])(xdf, chan, **chan_func['high']['args'])
        xdf['chan_l'] = eval(chan_func['low']['func'])(xdf, chan, **chan_func['low']['args'])
    else:
        xdf['chan_h'] = 0
        xdf['chan_l'] = 10000000
    xdf['high_band'] = xdf[['chan_h', 'upbnd']].max(axis=1)
    xdf['low_band'] = xdf[['chan_l', 'lowbnd']].min(axis=1)
    xdf['next_open'] = xdf['open'].shift(-1)
    xdf['next_time'] = xdf.index
    xdf['next_time'] = xdf['next_time'].shift(-1)
    xdf['close_ind'] = np.isnan(xdf['next_open'])
    daily_end = (xdf['date']!=xdf['date'].shift(-1))
    xdf['close_ind'] = xdf['close_ind'] & daily_end
    ll = xdf.shape[0]
    xdf['pos'] = pd.Series([0]*ll, index = xdf.index)
    xdf['cost'] = pd.Series([0]*ll, index = xdf.index)
    xdf['traded_price'] = xdf.close
    curr_pos = []
    closed_trades = []
    tradeid = 0
    for idx, dd in enumerate(xdf.index):
        mslice = xdf.ix[dd]
        min_id = mslice.min_id
        if len(curr_pos) == 0:
            pos = 0
        else:
            pos = curr_pos[0].pos
        xdf.ix[dd, 'pos'] = pos
        if np.isnan(mslice.boll_ma) or np.isnan(mslice.chan_h):
            continue
        if mslice.close_ind:
            if pos!=0:
                curr_pos[0].close(mslice.close - misc.sign(pos) * offset , dd)
                tradeid += 1
                curr_pos[0].exit_tradeid = tradeid
                closed_trades.append(curr_pos[0])
                curr_pos = []
                xdf.ix[dd, 'cost'] -=  abs(pos) * (offset + mslice.close*tcost)
                xdf.ix[dd, 'traded_price'] = mslice.close - abs(pos) * (offset + mslice.close*tcost)
                pos = 0
        else:
            if ((mslice.close > mslice.boll_ma) and (pos<0)) or ((mslice.close < mslice.boll_ma) and (pos>0)):
                curr_pos[0].close(mslice.next_open - misc.sign(pos) * offset, mslice.next_time)
                tradeid += 1
                curr_pos[0].exit_tradeid = tradeid
                closed_trades.append(curr_pos[0])
                curr_pos = []
                xdf.ix[mslice.next_time, 'cost'] -= abs(pos) * (offset + mslice.next_open * tcost)
                xdf.ix[mslice.next_time, 'traded_price'] = mslice.next_open - abs(pos) * (offset + mslice.next_open * tcost)
                pos = 0
            if ((mslice.close > mslice.high_band) and (pos<=0)) or ((mslice.close < mslice.low_band) and (pos>=0)):
                target_pos = ( mslice.close > mslice.high_band) * unit - (mslice.close < mslice.low_band) * unit
                new_pos = pos_class([mslice.contract], [1], target_pos, mslice.next_open, mslice.next_open, **pos_args)
                tradeid += 1
                new_pos.entry_tradeid = tradeid
                new_pos.open(mslice.next_open + misc.sign(target_pos)*offset, mslice.next_time)
                curr_pos.append(new_pos)
                pos = target_pos
                xdf.ix[mslice.next_time, 'cost'] -=  abs(target_pos) * (offset + mslice.next_open * tcost)
                xdf.ix[mslice.next_time, 'traded_price'] = mslice.next_open - abs(pos) * (offset + mslice.next_open * tcost)
        mdf.ix[dd, 'pos'] = pos
    (res_pnl, ts) = backtest.get_pnl_stats( xdf, start_equity, marginrate, 'm')
    res_trade = backtest.get_trade_stats( closed_trades )
    res = dict( res_pnl.items() + res_trade.items())
    return (res, closed_trades, ts)

def gen_config_file(filename):
    sim_config = {}
    sim_config['sim_func']  = 'bktest_bband_chan.bband_chan_sim'
    sim_config['scen_keys'] = ['freq', 'param']
    sim_config['sim_name']   = 'bbands_chan_'
    sim_config['products']   = ['rb', 'ru', 'TA', 'MA', 'i', 'j']
    sim_config['start_date'] = '20150102'
    sim_config['end_date']   = '20160429'
    sim_config['need_daily'] = False
    sim_config['freq']  =  [ '15min']
    sim_config['param'] = [(20, 1, 0), (20, 1, 10), (20, 1, 20), (20, 1.5, 0), (20, 1, 5, 10), (20, 1.5, 20), (40, 1, 0), (40, 1, 20), (40, 1, 40), \
                           (40, 1.5, 0), (40, 1.5, 20), (40, 1.5, 40), (80, 1, 0), (80, 1, 40), (80, 1, 80), (80, 1.5, 0), (80, 1.5, 40), (80, 1.5, 80)]
    sim_config['pos_class'] = 'strat.TradePos'
    sim_config['offset']    = 1
    chan_func = { 'high': {'func': 'dh.DONCH_H', 'args':{'field': 'close'}},
                  'low':  {'func': 'dh.DONCH_L', 'args':{'field': 'close'}}}
    config = {'capital': 10000,
              'chan': 0,
              'trans_cost': 0.0,
              'close_daily': False,
              'mode': 'close',
              'unit': 1,
              'stoploss': 0.0,
              'pos_args': {},
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
