import sys
import misc
import data_handler as dh
import pandas as pd
import numpy as np
import json
import strategy as strat

def asctrend_sim( mdf, config):
    offset = config['offset']
    tcost = config['trans_cost']
    unit = config['unit']
    stoploss = config['stoploss']
    bar_func = config.get('bar_conv_func', 'dh.bar_conv_func2')
    param = config['param']    
    freq = config['freq']
    pos_update = config.get('pos_update', False)
    pos_class = config['pos_class']
    pos_args  = config['pos_args']    
    close_daily = config['close_daily']    
    xdf = dh.conv_ohlc_freq(mdf, freq, extra_cols = ['contract'], bar_func = eval(bar_func))
    asc_period = param[0]
    asc_risk = param[1]
    asctrend = dh.ASCTREND(xdf, asc_period, risk = asc_risk)
    xdf['asc_signal'] = asctrend["ASCSIG_%s" % str(asc_period)].shift(1)
    xdf['asc_stop'] = asctrend["ASCSTOP_%s" % str(asc_period)].shift(1)
    rsi_period = param[2]
    rsi_offset = param[3]
    rsi_buy = 50 + rsi_offset 
    rsi_sell = 50 - rsi_offset
    rsi  = dh.RSI(xdf, n = rsi_period)
    rsi_signal = pd.Series(0, index = rsi.index)
    #rsi_signal[(rsi > rsi_buy)] = 1
    rsi_signal[(rsi > rsi_buy) & (rsi.shift(1) <= rsi_buy)] = 1
    #rsi_signal[(rsi < rsi_sell)] = -1
    rsi_signal[(rsi < rsi_sell) & (rsi.shift(1) >= rsi_sell)] = -1
    xdf['rsi_signal'] = rsi_signal
    if len(param) > 4:
        sar_step = param[4]
        sar_max = param[5]
    else:
        sar_step = 0.005
        sar_max = 0.02
    sar = dh.SAR(xdf, incr = sar_step, maxaf = sar_max)
    sar_signal = pd.Series(0, index = sar.index)
    sar_signal[(sar >= sar.shift(1))] = 1
    sar_signal[(sar <= sar.shift(1))] = -1
    xdf['sar_signal'] = sar_signal
    xdf['sar_stop'] = sar
    xdf['prev_close'] = xdf['close'].shift(1)
    xdf['close_ind'] = np.isnan(xdf['close'].shift(-1))
    if close_daily:
        daily_end = (xdf['date']!=xdf['date'].shift(-1))
        xdf['close_ind'] = xdf['close_ind'] | daily_end
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
        if np.isnan(mslice.sar_stop) or np.isnan(mslice.asc_stop):
            continue
        buy_trig  = (mslice.asc_signal > 0) and (mslice.rsi_signal > 0) and (mslice.sar_signal > 0)
        sell_trig = (mslice.asc_signal < 0) and (mslice.rsi_signal < 0) and (mslice.sar_signal < 0)
        buy_close  = (mslice.asc_signal < 0) or (mslice.rsi_signal < 0)
        sell_close = (mslice.asc_signal > 0) or (mslice.rsi_signal > 0)
        if mslice.close_ind:
            if (pos != 0):
                curr_pos[0].close(mslice.open - misc.sign(pos) * offset , dd)
                tradeid += 1
                curr_pos[0].exit_tradeid = tradeid
                closed_trades.append(curr_pos[0])
                curr_pos = []
                xdf.set_value(dd, 'cost', xdf.at[dd, 'cost'] - abs(pos) * ( mslice.open * tcost))
                xdf.set_value(dd, 'traded_price', mslice.open - misc.sign(pos) * offset)
                pos = 0
        else:
            if (buy_close and (pos > 0)) or (sell_close and (pos < 0)):
                curr_pos[0].close(mslice.open - misc.sign(pos) * offset, dd)
                tradeid += 1
                curr_pos[0].exit_tradeid = tradeid
                closed_trades.append(curr_pos[0])
                curr_pos = []
                xdf.set_value(dd, 'cost', xdf.at[dd, 'cost'] - abs(pos) * (mslice.open * tcost))
                xdf.set_value(dd, 'traded_price', mslice.open - misc.sign(pos) * offset)
                pos = 0       
            if (buy_trig or sell_trig) and (pos==0):
                target_pos = buy_trig * unit - sell_trig * unit
                new_pos = pos_class([mslice.contract], [1], target_pos, mslice.open, mslice.open, **pos_args)
                tradeid += 1
                new_pos.entry_tradeid = tradeid
                new_pos.open(mslice.open + misc.sign(target_pos)*offset, dd)
                curr_pos.append(new_pos)
                pos = target_pos
                xdf.set_value(dd, 'cost', xdf.at[dd, 'cost'] -  abs(target_pos) * (mslice.open * tcost))
                xdf.set_value(dd, 'traded_price', mslice.open + misc.sign(target_pos)*offset)
        # if pos_update and pos != 0:
        #     if curr_pos[0].check_exit(mslice.open, stoploss * mslice.boll_std):
        #         curr_pos[0].close(mslice.open - misc.sign(pos) * offset, dd)
        #         tradeid += 1
        #         curr_pos[0].exit_tradeid = tradeid
        #         closed_trades.append(curr_pos[0])
        #         curr_pos = []
        #         xdf.set_value(dd, 'cost', xdf.at[dd, 'cost'] - abs(pos) * (mslice.open * tcost))
        #         xdf.set_value(dd, 'traded_price', mslice.open - misc.sign(pos) * offset)
        #         pos = 0
        #     else:
        #         curr_pos[0].update_bar(mslice)
        xdf.set_value(dd, 'pos', pos)
    return (xdf, closed_trades)
    
def gen_config_file(filename):
    sim_config = {}
    sim_config['sim_func']  = 'bktest_asctrend.asctrend_sim'
    sim_config['scen_keys'] = ['freq', 'param']
    sim_config['sim_name']   = 'asctrend_sim'
    sim_config['products']   = [ 'm', 'RM', 'y', 'p', 'a', 'rb', 'SR', 'TA', 'MA', 'i', 'ru', 'j', 'jm', 'ag', 'cu', 'au', 'al', 'zn' ]
    sim_config['start_date'] = '20150102'
    sim_config['end_date']   = '20160819'
    sim_config['freq']  =  ['5Min', '15Min', '30Min', '60Min']
    sim_config['param'] = [[9, 3, 14, 10, 0.005, 0.02], [9, 3, 21, 10, 0.005, 0.02], \
                           [19, 3, 14, 10, 0.005, 0.02], [19, 3, 21, 10, 0.005, 0.02], \
                           [19, 13, 14, 10, 0.005, 0.1], [19, 13, 21, 10, 0.005, 0.1], \
                           [19, 13, 14, 20, 0.005, 0.1], [19, 13, 21, 20, 0.005, 0.1], ]
    sim_config['pos_class'] = 'strat.TradePos'
    config = {'capital': 10000,
              'offset': 0,
              'trans_cost': 0.0,
              'close_daily': False,
              'unit': 1,
              'stoploss': 0.0,
              'pos_update': False,
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
