import sys
import misc
import data_handler as dh
import pandas as pd
import numpy as np
import datetime
import backtest
import strategy as strat
import json

def rbreaker_sim( mdf, config):
    if 'ddf' in config:
        ddf = config['ddf']
    else:
        freq = config['freq']
        ddf = dh.conv_ohlc_freq(mdf, freq)
    start_equity = config['capital']
    tcost = config['trans_cost']
    unit = config['unit']
    pos_class = config['pos_class']
    pos_args  = config['pos_args']
    close_daily = config['close_daily']
    marginrate = config['marginrate']
    offset = config['offset']
    min_rng = config['min_rng']
    k = config['params']
    a = k[0]
    b = k[1]
    c = k[2]
    ddf['range'] = ddf.high - ddf.low
    ddf['ssetup'] = ddf.high + a*(ddf.close - ddf.low)
    ddf['bsetup'] = ddf.low  - a*(ddf.high - ddf.close)
    ddf['senter'] = (1+b)*(ddf.high+ddf.close)/2.0 - b * ddf.low
    ddf['benter'] = (1+b)*(ddf.low+ddf.close)/2.0 - b * ddf.high
    ddf['bbreak'] = ddf.ssetup + c * (ddf.ssetup - ddf.bsetup)
    ddf['sbreak'] = ddf.bsetup - c * (ddf.ssetup - ddf.bsetup)
    ddf = ddf.shift(1)
    ll = mdf.shape[0]
    mdf['pos'] = pd.Series([0]*ll, index = mdf.index)
    mdf['cost'] = pd.Series([0]*ll, index = mdf.index)
    curr_pos = []
    closed_trades = []
    start_d = mdf.index[0].date()
    end_d = mdf.index[-1].date()
    prev_d = start_d - datetime.timedelta(days=1)
    tradeid = 0
    cur_high = 0
    cur_low = 0
    rev_flag = True
    dslice = None
    num_trades = 0
    for dd in mdf.index:
        mslice = mdf.ix[dd]
        min_id = mslice.min_id
        d = mslice.date
        if (prev_d < d):
            num_trades = 0
            cur_high = mslice.high
            cur_low = mslice.low
            if d not in ddf.index:
                print d, dd
            else:
                dslice = ddf.ix[d]
            if np.isnan(dslice.bbreak):
                continue
            if dslice.range < min_rng * dslice.close:
                rev_flag = False
            else:
                rev_flag = True
            prev_d = d
        else:
            cur_high = max(cur_high, mslice.high)
            cur_low = min(cur_low, mslice.low)
        if len(curr_pos) == 0:
            pos = 0
        else:
            pos = curr_pos[0].pos
        mdf.ix[dd, 'pos'] = pos
        if (min_id <= config['start_min']):
            continue
        if (min_id >= config['exit_min']):
            if (pos != 0) and (close_daily or (d == end_d)):
                curr_pos[0].close(mslice.close - misc.sign(pos) * offset , dd)
                tradeid += 1
                curr_pos[0].exit_tradeid = tradeid
                closed_trades.append(curr_pos[0])
                curr_pos = []
                mdf.ix[dd, 'cost'] -=  abs(pos) * (offset + mslice.close*tcost) 
                pos = 0
        else:
            if num_trades >=3:
                continue
            if ((mslice.high >= dslice.bbreak) and (pos <= 0)) or ((mslice.low <= dslice.sbreak) and (pos >= 0)):
                rev_flag = False
                if (mslice.close >= dslice.bbreak):
                    direction = 1
                else:
                    direction = -1
                if pos != 0:
                    curr_pos[0].close(mslice.close + direction*offset, dd)
                    tradeid += 1
                    curr_pos[0].exit_tradeid = tradeid
                    closed_trades.append(curr_pos[0])
                    curr_pos = []
                    mdf.ix[dd, 'cost'] -=  abs(pos) * (offset + mslice.close*tcost)
                new_pos = pos_class([mslice.contract], [1], unit*direction, mslice.close, 0, **pos_args)
                tradeid += 1
                new_pos.entry_tradeid = tradeid
                new_pos.open(mslice.close + offset*direction, dd)
                curr_pos.append(new_pos)
                pos = unit*direction
                mdf.ix[dd, 'cost'] -=  abs(direction) * (offset + mslice.close*tcost)
                num_trades += 1
            elif rev_flag and (((cur_high < dslice.bbreak) and (cur_high >= dslice.ssetup) and (mslice.close <= dslice.senter) and (pos >=0)) or \
                            ((cur_low > dslice.sbreak)  and (cur_low  <= dslice.bsetup) and (mslice.close >= dslice.benter) and (pos <=0))):
                if len(curr_pos) > 0:
                    curr_pos[0].close(mslice.close-misc.sign(pos)*offset, dd)
                    tradeid += 1
                    curr_pos[0].exit_tradeid = tradeid
                    closed_trades.append(curr_pos[0])
                    curr_pos = []
                    mdf.ix[dd, 'cost'] -=  abs(pos) * (offset + mslice.close*tcost)
                new_pos = pos_class([mslice.contract], [1], -unit*misc.sign(pos), mslice.close, 0, **pos_args)
                tradeid += 1
                new_pos.entry_tradeid = tradeid
                new_pos.open(mslice.close + offset*misc.sign(pos), dd)
                curr_pos.append(new_pos)
                pos = -unit*misc.sign(pos)
                mdf.ix[dd, 'cost'] -=  abs(pos) * (offset + mslice.close*tcost)
                num_trades += 1
        mdf.ix[dd, 'pos'] = pos
    (res_pnl, ts) = backtest.get_pnl_stats( mdf, start_equity, marginrate, 'm')
    res_trade = backtest.get_trade_stats( closed_trades )
    res = dict( res_pnl.items() + res_trade.items())
    return (res, closed_trades, ts)

def gen_config_file(filename):
    sim_config = {}
    sim_config['sim_func']  = 'bktest_rbreaker.rbreaker_sim'
    sim_config['scen_keys'] = ['min_rng', 'params']
    sim_config['sim_name']   = 'RBreaker_'
    sim_config['products']   = ['y', 'p', 'l', 'pp', 'cs', 'a', 'rb', 'SR', 'TA', 'MA', 'i', 'j', 'jd', 'jm', 'ag', 'cu', 'm', 'RM', 'ru']
    sim_config['start_date'] = '20150102'
    sim_config['end_date']   = '20160331'
    sim_config['need_daily'] = True
    sim_config['min_rng']  =  [ 0.015, 0.02, 0.025 ]
    sim_config['params'] = [(0.25, 0.05, 0.15), (0.30, 0.06, 0.20), (0.35, 0.08, 0.25), (0.4, 0.1, 0.3)]    
    sim_config['pos_class'] = 'strat.TradePos'
    sim_config['offset']    = 1
    #chan_func = { 'high': {'func': 'dh.PCT_CHANNEL', 'args':{'pct': 90, 'field': 'high'}},
    #              'low':  {'func': 'dh.PCT_CHANNEL', 'args':{'pct': 10, 'field': 'low'}}}
    config = {'capital': 10000,
              'use_chan': False,
              'trans_cost': 0.0,
              'close_daily': True,
              'unit': 1,
              'stoploss': 0.0,
              'pos_args': {},
              'pos_update': False,
              'start_min': 303,
              'exit_min': 2055,
              #'chan_func': chan_func,
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
