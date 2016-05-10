import misc
import json
import data_handler as dh
import pandas as pd
import numpy as np
import strategy as strat
import datetime
import backtest
import sys

def aberration_sim( mdf, config):
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
    #freq_min = int(freq[:-3])
    mode = config.get('mode', 'close')
    xdf = dh.conv_ohlc_freq(mdf, freq)
    boll_ma = dh.MA(xdf, win).shift(1)
    boll_std = dh.STDDEV(xdf, win).shift(1)
    upbnd = np.ceil((boll_ma + boll_std * k)/tick_base) * tick_base
    lowbnd = np.floor((boll_ma - boll_std * k)/tick_base) * tick_base
    boll_ma = np.floor(boll_ma/tick_base + 0.5) * tick_base
    xdata = [boll_ma, boll_std, upbnd, lowbnd, xdf['min_id']]
    xkeys = ['ma', 'stdev', 'upbnd', 'lowbnd', 'xmin_id']
    if chan > 0:
        chan_h = eval(chan_func['high']['func'])(xdf, chan, **chan_func['high']['args'])
        chan_l = eval(chan_func['low']['func'])(xdf, chan, **chan_func['low']['args'])
        xdata = xdata + [ chan_h, chan_l ]
        xkeys = xkeys + ['chan_h', 'chan_l']
    xdf = pd.concat( xdata, axis=1, keys=xkeys).fillna(0)
    mdf = mdf.join(xdf, how = 'left').fillna(method='ffill')
    mdf['is_new'] = (mdf['xmin_id'].shift(1) != mdf['xmin_id'])
    ll = mdf.shape[0]
    mdf['pos'] = pd.Series([0]*ll, index = mdf.index)
    mdf['cost'] = pd.Series([0]*ll, index = mdf.index)
    curr_pos = []
    closed_trades = []
    start_d = mdf.date[0]
    end_d = mdf.date[-1]
    tradeid = 0
    for idx, dd in enumerate(mdf.index):
        mslice = mdf.ix[dd]
        min_id = mslice.min_id
        d = mslice.date
        if len(curr_pos) == 0:
            pos = 0
            start_pos = 0
        else:
            pos = curr_pos[0].pos
            start_pos = pos
        mdf.ix[dd, 'pos'] = pos
        if mslice.ma == 0:
            continue
        upbnd = mslice.upbnd
        lowbnd = mslice.lowbnd
        if chan > 0:
            if mslice.chan_h == 0:
                continue
            else:
                upbnd  = max(mslice.chan_h, upbnd)
                lowbnd = min(mslice.chan_l, lowbnd)
        if min_id >=config['exit_min']:
            if (pos!=0) and ((d == end_d) or close_daily):
                curr_pos[0].close(mslice.close - misc.sign(pos) * offset , dd)
                tradeid += 1
                curr_pos[0].exit_tradeid = tradeid
                closed_trades.append(curr_pos[0])
                curr_pos = []
                mdf.ix[dd, 'cost'] -=  abs(pos) * (offset + mslice.close*tcost)
                pos = 0
        else:
            if mode == 'close':
                high_trig = mslice.close
                low_trig  = mslice.close
                trade_price = mslice.close
            else:
                high_trig = mslice.high
                low_trig = mslice.low
                trade_price = mslice.open
            if ((high_trig >= mslice.ma) and (pos<0)) or ((low_trig <= mslice.ma) and (pos>0)):
                if pos < 0: 
                    exec_price = max(trade_price, mslice.ma)
                else:
                    exec_price = min(trade_price, mslice.ma)
                curr_pos[0].close(exec_price - misc.sign(pos) * offset, dd)
                tradeid += 1
                curr_pos[0].exit_tradeid = tradeid
                closed_trades.append(curr_pos[0])
                curr_pos = []
                mdf.ix[dd, 'cost'] -= abs(pos) * (offset + exec_price*tcost)
                pos = 0
            if ((high_trig > upbnd) and (pos<=0)) or ((low_trig < lowbnd) and (pos>=0)):
                target_pos = ( high_trig > upbnd) * unit - (low_trig < lowbnd) * unit
                if target_pos == 0:
                    print "the min bar hit both up and low bounds, need to think about how to handle it", start_pos, mslice
                    if mslice.close > mslice.ma:
                        target_pos = (high_trig > upbnd) * unit
                        target = max(trade_price, upbnd)
                    else:
                        trade_pos = - (low_trig < lowbnd) * unit
                        target =  min(trade_price, lowbnd)
                else:
                    target = (high_trig > upbnd) * max(trade_price, upbnd) + (low_trig < lowbnd) * min(trade_price, lowbnd)
                new_pos = pos_class([mslice.contract], [1], target_pos, target, target, **pos_args)
                tradeid += 1
                new_pos.entry_tradeid = tradeid
                new_pos.open(target + misc.sign(target_pos)*offset, dd)
                curr_pos.append(new_pos)
                pos = target_pos
                mdf.ix[dd, 'cost'] -=  abs(target_pos) * (offset + target*tcost)
        mdf.ix[dd, 'pos'] = pos
    (res_pnl, ts) = backtest.get_pnl_stats( mdf, start_equity, marginrate, 'm')
    res_trade = backtest.get_trade_stats( closed_trades )
    res = dict( res_pnl.items() + res_trade.items())
    return (res, closed_trades, ts)

def gen_config_file(filename):
    sim_config = {}
    sim_config['sim_func']  = 'bktest_aberration.aberration_sim'
    sim_config['scen_keys'] = ['freq', 'param']
    sim_config['sim_name']   = 'Abberation_'
    sim_config['products']   = ['y', 'p', 'l', 'pp', 'cs', 'a', 'rb', 'SR', 'TA', 'MA', 'i', 'j', 'jd', 'jm', 'ag', 'cu', 'm', 'RM', 'ru']
    sim_config['start_date'] = '20150102'
    sim_config['end_date']   = '20160429'
    sim_config['need_daily'] = True
    sim_config['freq']  =  [ '15min', '30min', '60min']
    sim_config['param'] = [(20, 1, 0), (20, 1, 5), (20, 1, 10), (30, 1, 0), (30, 1, 5), (30, 1, 10), (30, 1, 15), (40, 1, 0), (40, 1, 10), (40, 1, 20), \
                           (20, 1.5, 0), (20, 1.5, 5), (20, 1.5, 10), (30, 1.5, 0), (30, 1.5, 5), (30, 1.5, 10), (30, 1.5, 15), (40, 1.5, 0), (40, 1.5, 10), (40, 1.5, 20)]
    sim_config['pos_class'] = 'strat.TradePos'
    sim_config['offset']    = 1
    chan_func = { 'high': {'func': 'dh.PCT_CHANNEL', 'args':{'pct': 90, 'field': 'close'}},
                  'low':  {'func': 'dh.PCT_CHANNEL', 'args':{'pct': 10, 'field': 'close'}}}
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
