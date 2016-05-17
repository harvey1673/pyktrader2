import sys
import misc
import data_handler as dh
import pandas as pd
import tradeagent as agent
import numpy as np
import strategy as strat
import datetime
import json
import backtest

def dual_thrust_sim( mdf, config):
    (pos_class, pos_args) = config['pos_param']
    update_freq = config.get('update_freq', 1)
    ddf = config['ddf']
    close_daily = config['close_daily']
    marginrate = config['marginrate']
    offset = config['offset']
    k = config['param'][0]
    win = config['param'][1]
    multiplier = config['param'][2]
    f = config['param'][3]
    start_equity = config['capital']
    chan = config['chan']
    chan_func = config['chan_func']
    use_chan = config('use_chan']
    tcost = config['trans_cost']
    unit = config['unit']
    SL = config['stoploss']
    min_rng = config['min_range']

    if win == -1:
        tr= pd.concat([ddf.high - ddf.low, ddf.close - ddf.close.shift(1)], 
                       join='outer', axis=1).max(axis=1).shift(1)
    elif win == 0:
        tr = pd.concat([(pd.rolling_max(ddf.high, 2) - pd.rolling_min(ddf.close, 2))*multiplier, 
                        (pd.rolling_max(ddf.close, 2) - pd.rolling_min(ddf.low, 2))*multiplier,
                        ddf.high - ddf.close, 
                        ddf.close - ddf.low], 
                        join='outer', axis=1).max(axis=1).shift(1)
    else:
        tr= pd.concat([pd.rolling_max(ddf.high, win) - pd.rolling_min(ddf.close, win), 
                       pd.rolling_max(ddf.close, win) - pd.rolling_min(ddf.low, win)], 
                       join='outer', axis=1).max(axis=1).shift(1)
    ddf['TR'] = tr
    ddf['CH_H'] = eval(chan_func['high']['func'])(ddf, chan, **chan_func['high']['args']).shift(1)
    ddf['CH_L'] = eval(chan_func['low']['func'])(ddf, chan, **chan_func['low']['args']).shift(1)
    ll = mdf.shape[0]
    mdf['pos'] = pd.Series([0]*ll, index = mdf.index)
    mdf['cost'] = pd.Series([0]*ll, index = mdf.index)
    start_d = ddf.index[0]
    end_d = mdf.index[-1].date()
    prev_d = start_d - datetime.timedelta(days=1)    
    # if close_daily:
        # mdf['close_ind'] = (mdf.min_id >= config['exit_min'])
    # else:
        # mdf['close_ind'] = (mdf.min_id >= config['exit_min']) & (mdf.date == end_d)
    curr_pos = []
    closed_trades = []
    tradeid = 0
    for dd in mdf.index:
        mslice = mdf.ix[dd]
        min_id = mslice.min_id
        d = mslice.date
        dslice = ddf.ix[d]
        if np.isnan(dslice.TR) or (mslice.close == 0):
            continue
        if use_chan and np.isnan(mslice.CH_H):
            continue
        if len(curr_pos) == 0:
            pos = 0
        else:
            pos = curr_pos[0].pos
        mdf.ix[dd, 'pos'] = pos
        d_open = dslice.open
        if (d_open <= 0):
            continue
        rng = max(min_rng * d_open, k * dslice.TR)
        if (prev_d < d):
            d_open = mslice.open
            d_high = mslice.high
            d_low =  mslice.low
        else:
            d_open = dslice.open
            d_high = max(d_high, mslice.high)
            d_low  = min(d_low, mslice.low)
        prev_d = d
        buytrig  = d_open + rng
        selltrig = d_open - rng
        if pos != 0:
            if (mslice.min_id + 1) % update_freq == 0:
                curr_pos[0].update_bar(mslice)
            if (curr_pos[0].check_exit(mslice.close, SL)) or (mslice.min_id >= config['exit_min'] and (close_daily or (d == end_d))):
                curr_pos[0].close(mslice.close - misc.sign(pos) * offset , dd)
                tradeid += 1
                curr_pos[0].exit_tradeid = tradeid
                closed_trades.append(curr_pos[0])
                curr_pos = []
                mdf.ix[dd, 'cost'] -=  abs(pos) * (offset + mslice.close*tcost)
                pos = 0
        if mslice.min_id < config['exit_min']:
            if (mslice.high >= buytrig) and (pos <=0 ):
                if len(curr_pos) > 0:
                    curr_pos[0].close(mslice.close+offset, dd)
                    tradeid += 1
                    curr_pos[0].exit_tradeid = tradeid
                    closed_trades.append(curr_pos[0])
                    curr_pos = []
                    mdf.ix[dd, 'cost'] -=  abs(pos) * (offset + mslice.close*tcost)
                if mslice.high >= dslice.CH_H:
                    new_pos = eval(pos_class)([mslice.contract], [1], unit, mslice.close + offset, mslice.close + offset, **pos_args)
                    tradeid += 1
                    new_pos.entry_tradeid = tradeid
                    new_pos.open(mslice.close + offset, dd)
                    curr_pos.append(new_pos)
                    pos = unit
                    mdf.ix[dd, 'cost'] -=  abs(pos) * (offset + mslice.close*tcost)
            elif (mslice.low <= selltrig) and (pos >=0 ):
                if len(curr_pos) > 0:
                    curr_pos[0].close(mslice.close-offset, dd)
                    tradeid += 1
                    curr_pos[0].exit_tradeid = tradeid
                    closed_trades.append(curr_pos[0])
                    curr_pos = []
                    mdf.ix[dd, 'cost'] -=  abs(pos) * (offset + mslice.close*tcost)
                if mslice.low <= dslice.CH_L:
                    new_pos = eval(pos_class)([mslice.contract], [1], -unit, mslice.close - offset, mslice.close - offset)
                    tradeid += 1
                    new_pos.entry_tradeid = tradeid
                    new_pos.open(mslice.close - offset, dd)
                    curr_pos.append(new_pos)
                    pos = -unit
                    mdf.ix[dd, 'cost'] -= abs(pos) * (offset + mslice.close*tcost)
        mdf.ix[dd, 'pos'] = pos
            
    (res_pnl, ts) = backtest.get_pnl_stats( mdf, start_equity, marginrate, 'm')
    res_trade = backtest.get_trade_stats( closed_trades )
    res = dict( res_pnl.items() + res_trade.items())
    return (res, closed_trades, ts)

def gen_config_file(filename):
    sim_config = {}
    sim_config['sim_func']  = 'bktest_dt_chanfilter.dual_thrust_sim'
    sim_config['scen_keys'] = ['close_daily', 'pos_param']
    sim_config['sim_name']   = 'DTdchan_'
    sim_config['products']   = ['y', 'p', 'l', 'pp', 'cs', 'a', 'rb', 'SR', 'TA', 'MA', 'i', 'j', 'jd', 'jm', 'ag', 'cu', 'm', 'RM', 'ru']
    sim_config['start_date'] = '20150105'
    sim_config['end_date']   = '20160513'
    sim_config['need_daily'] = True
    sim_config['pos_param'] = [('strat.TradePos', {})]
    sim_config['close_daily'] = [False, True]
    sim_config['proc_func'] = 'dh.day_split'
    sim_config['offset']    = 1
    chan_func = { 'high': {'func': 'dh.PCT_CHANNEL', 'args':{'pct': 90, 'field': 'high'}},
                  'low':  {'func': 'dh.PCT_CHANNEL', 'args':{'pct': 10, 'field': 'low'}}}
    config = {'capital': 10000,
              'use_chan': True,
              'trans_cost': 0.0,
              'unit': 1,
              'chan': 20,
              'stoploss': 0.0,
              'min_range': 0.0035,
              'proc_args': {'minlist':[]},
              'pos_args': {},
              'param': (0.8, 0, 0.5, 0),
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
