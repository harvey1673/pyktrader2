import sys
import misc
import data_handler as dh
import pandas as pd
import numpy as np
import json
import strategy as strat

def psar_chan_sim( mdf, config):
    marginrate = config['marginrate']
    offset = config['offset']
    tcost = config['trans_cost']
    unit = config['unit']
    stoploss = config['stoploss']
    bar_func = config.get('bar_conv_func', 'dh.bar_conv_func2')
    param = config['param']
    freq = config['freq']
    use_HL = config.get('use_HL',False)
    use_chan = config['use_chan']    
    chan_func = config['chan_func']
    chan_args = config['chan_args']
    chan = param[0]
    sar_param = param[1]
    pos_update = config.get('pos_update', False)
    pos_class = config['pos_class']
    pos_args  = config['pos_args']    
    close_daily = config['close_daily']
    
    xdf = dh.conv_ohlc_freq(mdf, freq, extra_cols = ['contract'], bar_func = eval(bar_func))
    if use_chan:
        xdf['chanH'] = eval(chan_func[0])(xdf, chan, **chan_args[0]).shift(1)
        xdf['chanL'] = eval(chan_func[1])(xdf, chan, **chan_args[1]).shift(1)
    else:
        xdf['chanH'] = 0
        xdf['chanL'] = 10000000
    psar_data = dh.PSAR(xdf, **sar_param)
    xdf['psar_dir'] = psar_data['PSAR_DIR'].shift(1)
    xdf['psar_val'] = psar_data['PSAR_VAL'].shift(1)
    xdf['prev_high'] = xdf['high'].shift(1)
    xdf['prev_low'] = xdf['low'].shift(1)
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
        if np.isnan(mslice.chanH) or np.isnan(mslice.chanL):
            continue
        if use_HL:
            buy_trig  = (mslice.prev_high >= mslice.chanH) and (mslice.psar_dir > 0)
            sell_trig = (mslice.prev_low <= mslice.chanL) and (mslice.psar_dir < 0)
            long_close  = (mslice.prev_low <= mslice.chanL) or (mslice.psar_dir < 0)
            short_close = (mslice.prev_high >= mslice.chanH) or (mslice.psar_dir > 0)
        else:
            buy_trig  = (mslice.open >= mslice.chanH) and (mslice.psar_dir > 0)
            sell_trig = (mslice.open <= mslice.chanL) and (mslice.psar_dir < 0)
            long_close  = (mslice.open <= mslice.chanL) or (mslice.psar_dir < 0)
            short_close = (mslice.open >= mslice.chanH) or (mslice.psar_dir > 0)
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
            if (short_close and (pos > 0)) or (long_close and (pos < 0)):
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
        #if pos_update and pos != 0:
        #    if curr_pos[0].check_exit(mslice.open, stoploss * mslice.boll_std):
        #        curr_pos[0].close(mslice.open - misc.sign(pos) * offset, dd)
        #        tradeid += 1
        #        curr_pos[0].exit_tradeid = tradeid
        #        closed_trades.append(curr_pos[0])
        #        curr_pos = []
        #        xdf.set_value(dd, 'cost', xdf.at[dd, 'cost'] - abs(pos) * (mslice.open * tcost))
        #        xdf.set_value(dd, 'traded_price', mslice.open - misc.sign(pos) * offset)
        #        pos = 0
        #    else:
        #        curr_pos[0].update_bar(mslice)                
        xdf.set_value(dd, 'pos', pos)
    return (xdf, closed_trades)
    
def gen_config_file(filename):
    sim_config = {}
    sim_config['sim_func']  = 'bktest_psar_chan.psar_chan_sim'
    sim_config['scen_keys'] = ['freq', 'param']
    sim_config['sim_name']   = 'psar_chan'
    sim_config['products']   = [ 'm', 'RM', 'y', 'p', 'a', 'rb', 'SR', 'TA', 'MA', 'i', 'ru', 'j', 'jm', 'ag', 'cu', 'au', 'al', 'zn' ]
    sim_config['start_date'] = '20150102'
    sim_config['end_date']   = '20160722'
    sim_config['freq']  =  ['5Min', '15Min', '30Min', '60Min']
    sim_config['param']= [[3, {'iaf': 0.02, 'maxaf': 0.2, 'incr': 0.02}], \
                           [5, {'iaf': 0.02, 'maxaf': 0.2, 'incr': 0.02}], \
                           [10, {'iaf': 0.02, 'maxaf': 0.2, 'incr': 0.02}], \
                           [20, {'iaf': 0.02, 'maxaf': 0.2, 'incr': 0.02}], \
                           [3, {'iaf': 0.01, 'maxaf': 0.2, 'incr': 0.01}], \
                           [5, {'iaf': 0.01, 'maxaf': 0.2, 'incr': 0.01}], \
                           [10, {'iaf': 0.01, 'maxaf': 0.2, 'incr': 0.01}], \
                           [20, {'iaf': 0.01, 'maxaf': 0.2, 'incr': 0.01}], \
                           ]
    sim_config['pos_class'] = 'strat.TradePos'
    chan_func = ['dh.DONCH_H', 'dh.DONCH_L']
    config = {'capital': 10000,
              'offset': 0,
              'use_chan': True,
              'use_HL': False,
              'trans_cost': 0.0,
              'close_daily': False,
              'unit': 1,
              'stoploss': 0.0,
              'pos_update': False,
              'pos_args': {},
              'chan_func': chan_func,
              'chan_args': [{}, {}]
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
