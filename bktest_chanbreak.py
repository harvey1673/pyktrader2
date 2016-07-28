import misc
import data_handler as dh
import pandas as pd
import numpy as np
import strategy as strat
import datetime
import backtest
import sys

def count_min_id(dt):
    return ((dt.hour+6)%24)*60+dt.minute + 1

def chanbreak_sim( mdf, config):
    freq = config['freq']
    str_freq = str(freq) + 'Min'
    xdf = dh.conv_ohlc_freq(mdf, str_freq)
    start_equity = config['capital']
    tcost = config['trans_cost']
    unit = config['unit']
    marginrate = config['marginrate']
    offset = config['offset']
    win = config['win']
    pos_class = config['pos_class']
    pos_args  = config['pos_args']
    chan_func = config['channel_func']
    upper_chan_func = chan_func[0]
    lower_chan_func = chan_func[1]
    entry_chan = win[0]    
    exit_chan =  win[1]
    xdf['H1'] = upper_chan_func(xdf, entry_chan)
    xdf['L1'] = lower_chan_func(xdf, entry_chan)
    xdf['H2'] = upper_chan_func(xdf, exit_chan)
    xdf['L2'] = lower_chan_func(xdf, exit_chan)
    xdf['ATR'] = dh.ATR(xdf, entry_chan)
    xdata = pd.concat([xdf['H1'], xdf['L1'], xdf['H2'], xdf['L2'], xdf['ATR'], xdf['high'], xdf['low']], \
                      axis=1, keys=['H1', 'L1', 'H2', 'L2', 'ATR', 'xhigh', 'xlow']).shift(1)
    ll = mdf.shape[0]
    mdf = mdf.join(xdata, how = 'left').fillna(method='ffill')
    mdf['pos'] = pd.Series([0]*ll, index = mdf.index)
    mdf['cost'] = pd.Series([0]*ll, index = mdf.index)
    curr_pos = []
    closed_trades = []
    end_d = mdf.index[-1].date()
    tradeid = 0
    x_idx = 0
    max_idx = len(xdf.index)
    for idx, dd in enumerate(mdf.index):
        mslice = mdf.ix[dd]
        min_id = mslice.min_id
        cnt_id = count_min_id(dd)
        if len(curr_pos) == 0:
            pos = 0
        else:
            pos = curr_pos[0].pos
        mdf.ix[dd, 'pos'] = pos
        #if np.isnan(mslice.ATR):
        #    continue
        if (min_id >=config['exit_min']):
            if (pos!=0) and (dd.date() == end_d):
                curr_pos[0].close(mslice.close - misc.sign(pos) * offset , dd)
                tradeid += 1
                curr_pos[0].exit_tradeid = tradeid
                closed_trades.append(curr_pos[0])
                curr_pos = []
                pos = 0
                mdf.ix[dd, 'cost'] -=  abs(pos) * (offset + mslice.close*tcost) 
            continue
        else:
            if (pos !=0):
                if (cnt_id % freq) == 0:
                    curr_pos[0].update_bar(mslice)
                check_price = (pos>0) * mslice.low + (pos<0) * mslice.high
                if curr_pos[0].check_exit(check_price, 0):
                    curr_pos[0].close(mslice.close - misc.sign(pos) * offset, dd)
                    tradeid += 1
                    curr_pos[0].exit_tradeid = tradeid
                    closed_trades.append(curr_pos[0])
                    pos = 0
                    curr_pos = []                    
            if ((mslice.high >= mslice.H2) and (pos<0)) or ((mslice.low <= mslice.L2) and (pos>0)):
                curr_pos[0].close(mslice.close - misc.sign(pos) * offset, dd)
                tradeid += 1
                curr_pos[0].exit_tradeid = tradeid
                closed_trades.append(curr_pos[0])
                curr_pos = []
                mdf.ix[dd, 'cost'] -= abs(pos) * (offset + mslice.close*tcost)
                pos = 0
            if ((mslice.high >= mslice.H1) and (pos<=0)) or ((mslice.low <= mslice.L1) and (pos>=0)):
                if (pos ==0 ):
                    pos = (mslice.high >= mslice.H1) * unit -(mslice.low <= mslice.L1) * unit
                    exit_target = (mslice.high >= mslice.H1) * mslice.L2 + (mslice.low <= mslice.L1) * mslice.H2
                    new_pos = pos_class([mslice.contract], [1], pos, mslice.close, exit_target, 1, **pos_args)
                    tradeid += 1
                    new_pos.entry_tradeid = tradeid
                    new_pos.open(mslice.close + misc.sign(pos)*offset, dd)
                    curr_pos.append(new_pos)
                    mdf.ix[dd, 'cost'] -=  abs(pos) * (offset + mslice.close*tcost)
            mdf.ix[dd, 'pos'] = pos
    return (mdf, closed_trades)

def gen_config_file(filename):
    sim_config = {}
    sim_config['sim_func']  = 'bktest_chanbreak.chanbreak_sim'
    sim_config['scen_keys'] = ['freq', 'win']
    sim_config['sim_name']   = 'chanbreak_'
    sim_config['products']   = ['rb', 'i', 'j', 'jm', 'ZC', 'ru', 'ni', 'y', 'p', 'm', 'RM', 'cs', 'jd', 'a', 'l', 'pp', 'TA', 'MA', 'bu', 'cu', 'al', 'ag', 'au']
    sim_config['start_date'] = '20150102'
    sim_config['end_date']   = '20160708'
    sim_config['need_daily'] = False
    sim_config['freq'] = ['5min', '15min', '30min', '60min']
    sim_config['win'] = [ [5,  10, 20], [5, 10, 40], [5, 20, 40], [5, 20, 80], \
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
              'stoploss': 0.0,
              'close_daily': False,
              'pos_update': False,
              'channel_func': [dh.DONCH_H, dh.DONCH_L],
              'MA_func': dh.MA,
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
