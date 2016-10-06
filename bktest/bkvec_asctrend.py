import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)
import misc
import backtest
import data_handler as dh
import pandas as pd
import numpy as np
import json
import strategy as strat

def asctrend_sim( mdf, config):
    offset = config['offset']
    tcost = config['trans_cost']
    unit = config['unit']
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
    rsi_sig = config['rsi_sig']
    wpr_sig = config.get('wpr_sig', True)
    wpr = dh.WPR(xdf, asc_period)
    wpr_buy = 67 + asc_risk
    wpr_sell = 33 - asc_risk    
    wpr_signal = pd.Series(0, index = wpr.index)
    if wpr_sig:
        wpr_signal[(wpr >= wpr_buy) & (wpr.shift(1) < wpr_buy)] = 1
        wpr_signal[(wpr <= wpr_sell) & (wpr.shift(1) > wpr_sell)] = -1
    else:
        wpr_signal[(wpr >= wpr_buy)] = 1
        wpr_signal[(wpr <= wpr_sell)] = -1
    xdf['wpr_signal'] = wpr_signal.shift(1).fillna(0)
    rsi_period = param[2]
    rsi_offset = param[3]
    rsi_buy = 50 + rsi_offset 
    rsi_sell = 50 - rsi_offset
    rsi  = dh.RSI(xdf, n = rsi_period)
    rsi_signal = pd.Series(0, index = rsi.index)
    if rsi_sig:
        rsi_signal[(rsi >= rsi_buy) & (rsi.shift(1) < rsi_buy)] = 1
        rsi_signal[(rsi <= rsi_sell) & (rsi.shift(1) > rsi_sell)] = -1
    else:
        rsi_signal[(rsi >= rsi_buy)] = 1
        rsi_signal[(rsi <= rsi_sell)] = -1
    xdf['rsi_signal'] = rsi_signal.shift(1).fillna(0)
    if len(param) > 4:
        sar_step = param[4]
        sar_max = param[5]
    else:
        sar_step = 0.005
        sar_max = 0.02
    sar = dh.SAR(xdf, incr = sar_step, maxaf = sar_max)
    sar_signal = pd.Series(0, index = sar.index)
    sar_signal[(sar < xdf['close'])] = 1
    sar_signal[(sar > xdf['close'])] = -1
    xdf['sar_signal'] = sar_signal.shift(1)
    xdf['sar_stop'] = sar.shift(1)
    xdf['close_ind'] = np.isnan(xdf['close'].shift(-1))
    if close_daily:
        daily_end = (xdf['date']!=xdf['date'].shift(-1))
        xdf['close_ind'] = xdf['close_ind'] | daily_end
    long_signal = pd.Series(np.nan, index = xdf.index)
    short_signal = pd.Series(np.nan, index = xdf.index)
    long_signal[(xdf['wpr_signal']>0) & (xdf['rsi_signal']>0) & (xdf['sar_signal']>0)] = 1
    long_signal[(xdf['wpr_signal']<0) | (xdf['rsi_signal']<0)] = 0
    long_signal[xdf['close_ind']] = 0
    long_signal = long_signal.fillna(method='ffill').fillna(0)
    short_signal[(xdf['wpr_signal']<0) & (xdf['rsi_signal']<0) & (xdf['sar_signal']<0)] = 1
    short_signal[(xdf['wpr_signal']>0) | (xdf['rsi_signal']>0)] = 0
    short_signal[xdf['close_ind']] = 0
    short_signal = short_signal.fillna(method='ffill').fillna(0)
    if len(xdf[(long_signal>0) & (short_signal<0)])>0:
        print xdf[(long_signal > 0) & (short_signal < 0)]
        print "something wrong with the position as long signal and short signal happen the same time"    
    xdf['pos'] = long_signal + short_signal
    xdf['cost'] = abs(xdf['pos'] - xdf['pos'].shift(1)) * (offset + xdf['open'] * tcost)
    xdf['cost'] = xdf['cost'].fillna(0.0)
    xdf['traded_price'] = xdf.open + (xdf['pos'] - xdf['pos'].shift(1)) * offset
    closed_trades = backtest.simdf_to_trades1(xdf, slippage = offset )
    return (xdf, closed_trades)
    
def gen_config_file(filename):
    sim_config = {}
    sim_config['sim_func']  = 'bktest.bkvec_asctrend.asctrend_sim'
    sim_config['scen_keys'] = ['freq', 'param']
    sim_config['sim_name']   = 'asctrend_sim'
    sim_config['products']   = [ 'rb', 'hc', 'i', 'j', 'jm', 'ZC', 'ni', 'ru', \
                                 'm', 'RM', 'y', 'p', 'a', 'jd', 'cs', 'SR', 'c', 'OI', 'CF', \
                                 'pp', 'l', 'TA', 'v', 'MA', 'bu', 'ag', 'cu', 'au', 'al', 'zn',\
                                 'IF', 'IH', 'IC', 'TF', 'T']
    sim_config['start_date'] = '20150102'
    sim_config['end_date']   = '20160930'
    sim_config['freq']  =  ['15Min', '30Min', '60Min']
    sim_config['param'] =[[ 9, 3, 14, 20, 0.005, 0.1],[9, 3, 14, 20, 0.01, 0.1], \
                        [ 9, 3, 14, 20, 0.02, 0.1], [ 9, 3, 14, 20, 0.02, 0.2], \
                        [14, 3, 14, 20, 0.005, 0.1],[14, 3, 14, 20, 0.01, 0.1], \
                        [14, 3, 14, 20, 0.02, 0.1], [14, 3, 14, 20, 0.02, 0.2], \
                        [14, 3, 21, 20, 0.005, 0.1], [14, 3, 21, 20, 0.01, 0.1], \
                        [14, 3, 21, 20, 0.02, 0.1], [14, 3, 21, 20, 0.02, 0.2], \
                        [14, 3, 9, 20, 0.005, 0.1], [14, 3, 9, 20, 0.01, 0.1], \
                        [14, 3, 9, 20, 0.02, 0.1], [14, 3, 9, 20, 0.02, 0.2],]
    sim_config['pos_class'] = 'strat.TradePos'
    config = {'capital': 10000,
              'offset': 0,
              'rsi_sig': False,
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
