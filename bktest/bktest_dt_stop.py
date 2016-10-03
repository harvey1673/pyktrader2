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
import base

def conv_xslice(mslice):
    xslice = base.BaseObject(open = mslice.xopen, high = mslice.xhigh, low = mslice.xlow, close = mslice.xclose)
    return xslice

def dual_thrust_sim( mdf, config):
    (pos_class, pos_args) = config['pos_param']
    update_freq = config.get('update_freq', 0)
    ddf = config['ddf']
    close_daily = config['close_daily']
    offset = config['offset']
    k = config['param'][0]
    win = config['param'][1]
    multiplier = config['param'][2]
    f = config['param'][3]
    chan = config['chan']
    chan_func = config['chan_func']
    use_chan = config['use_chan']
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
    ddf['ATR'] = dh.ATR(ddf, win)
    if use_chan:
        ddf['CH_H'] = eval(chan_func['high']['func'])(ddf, chan, **chan_func['high']['args']).shift(1)
        ddf['CH_L'] = eval(chan_func['low']['func'])(ddf, chan, **chan_func['low']['args']).shift(1)
    if update_freq > 1:
        xdf = dh.conv_ohlc_freq(mdf, str(update_freq)+'Min')
    else:
        xdf = mdf
    xdata = pd.concat([xdf['open'], xdf['high'], xdf['low'], xdf['close']], axis=1, keys=['xopen','xhigh', 'xlow', 'xclose'])
    mdf = mdf.join(xdata, how = 'left').fillna(method='ffill')
    ll = mdf.shape[0]
    mdf['pos'] = 0
    mdf['cost'] = 0
    start_d = ddf.index[0]
    end_d = mdf.index[-1].date()
    prev_d = start_d - datetime.timedelta(days=1)
    curr_pos = []
    closed_trades = []
    tradeid = 0
    for idx, dd in enumerate(mdf.index):
        mslice = mdf.ix[dd]
        min_id = mslice.min_id
        d = mslice.date
        dslice = ddf.ix[d]
        if np.isnan(dslice.TR) or (mslice.close == 0):
            continue
        if use_chan and np.isnan(dslice.CH_H):
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
        else:
            d_open = dslice.open
        prev_d = d
        buytrig  = d_open + rng
        selltrig = d_open - rng
        stoploss = SL * dslice.ATR
        tmp_args = pos_args.copy()
        if 'reset_margin' in pos_args:
            tmp_args['reset_margin'] = dslice.ATR * pos_args['reset_margin']
            stoploss =  tmp_args['reset_margin'] * stoploss
        close_pos = False
        if pos != 0:
            if ((pos > 0) and (mslice.high < buytrig)) or ((pos < 0) and (mslice.low > selltrig)):
                close_pos = curr_pos[0].check_exit(mslice.close, stoploss)
            if (close_pos == False) and (update_freq > 0) and ((mslice.min_id + 1) % update_freq == 0):
                xslice = conv_xslice(mslice)
                curr_pos[0].update_bar(xslice)
            if close_pos or ((mslice.min_id >= config['exit_min']) and (close_daily or (d == end_d))):
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
                if (use_chan == False) or (use_chan and (mslice.high >= dslice.CH_H)):
                    new_pos = eval(pos_class)([mslice.contract], [1], unit, mslice.close + offset, mslice.close + offset, **tmp_args)
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
                if (use_chan == False) or (use_chan and (mslice.low <= dslice.CH_L)):
                    new_pos = eval(pos_class)([mslice.contract], [1], -unit, mslice.close - offset, mslice.close - offset, **tmp_args)
                    tradeid += 1
                    new_pos.entry_tradeid = tradeid
                    new_pos.open(mslice.close - offset, dd)
                    curr_pos.append(new_pos)
                    pos = -unit
                    mdf.ix[dd, 'cost'] -= abs(pos) * (offset + mslice.close*tcost)
        mdf.ix[dd, 'pos'] = pos
    return (mdf, closed_trades)

def gen_config_file(filename):
    sim_config = {}
    sim_config['sim_func']  = 'bktest_dt_stop.dual_thrust_sim'
    sim_config['scen_keys'] = ['pos_param', 'update_freq']
    sim_config['sim_name']   = 'DT_PSARStop_'
    sim_config['products']   = ['y', 'p', 'l', 'pp', 'cs', 'a', 'rb', 'SR', 'TA', 'MA', 'i', 'j', 'jd', 'jm', 'ag', 'cu', 'm', 'RM', 'ru']
    sim_config['start_date'] = '20150105'
    sim_config['end_date']   = '20160603'
    sim_config['need_daily'] = True
    sim_config['pos_param'] = [('strat.TradePos', {}), \
                               ('strat.ParSARProfitTrig', {'af': 0.02, 'incr': 0.02, 'cap': 0.2, 'reset_margin': 1}), \
                               ('strat.ParSARProfitTrig', {'af': 0.02, 'incr': 0.02, 'cap': 0.2, 'reset_margin': 1.5}), \
                               ('strat.ParSARProfitTrig', {'af': 0.02, 'incr': 0.02, 'cap': 0.2, 'reset_margin': 2}), \
                               ('strat.ParSARProfitTrig', {'af': 0.01, 'incr': 0.01, 'cap': 0.2, 'reset_margin': 1}), \
                               ('strat.ParSARProfitTrig', {'af': 0.02, 'incr': 0.02, 'cap': 0.2, 'reset_margin': 1}), \
                               ('strat.ParSARProfitTrig', {'af': 0.01, 'incr': 0.005, 'cap': 0.2, 'reset_margin': 1}) ]
    sim_config['update_freq'] = [15, 30, 60]
    sim_config['proc_func'] = 'dh.day_split'
    sim_config['offset']    = 1
    chan_func = { 'high': {'func': 'dh.PCT_CHANNEL', 'args':{'pct': 90, 'field': 'high'}},
                  'low':  {'func': 'dh.PCT_CHANNEL', 'args':{'pct': 10, 'field': 'low'}}}
    config = {'capital': 10000,
              'use_chan': False,
              'trans_cost': 0.0,
              'unit': 1,
              'chan': 20,
              'min_range': 0.0035,
              'proc_args': {'minlist':[]},
              'pos_args': {},
              'param': (0.3, 2, 0.5, 0),
              'chan_func': chan_func,
              'close_daily': False,
              'stoploss': 0.0,
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
