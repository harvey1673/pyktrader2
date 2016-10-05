import backtest
import misc
import pandas as pd
import numpy as np
import math
import mysqlaccess
import data_handler as dh
from scipy.stats import norm
import statsmodels.tsa.stattools as ts

def get_cont_data(asset, start_date, end_date, freq = '1m', nearby = 1, rollrule = '-10b'):
    if nearby == 0:
        mdf = mysqlaccess.load_min_data_to_df('fut_min', asset, start_date, end_date, minid_start = 300, minid_end = 2114, database = 'hist_data')
        mdf['contract'] = asset
    else:
        mdf = misc.nearby(asset, nearby, start_date, end_date, rollrule, 'm', need_shift=True, database = 'hist_data')
    mdf = backtest.cleanup_mindata(mdf, asset)
    xdf = dh.conv_ohlc_freq(mdf, freq, extra_cols = ['contract'], bar_func = dh.bar_conv_func2)
    return xdf

def variance_ratio(ts, freqs):
    data = ts.values
    nlen = len(data)
    res = {'n': [], 'ln':[]}
    var1 = np.var(data[1:] - data[:-1])
    lnvar1 = np.var(np.log(data[1:]/data[:-1]))
    for freq in freqs:
        nrow = nlen/freq
        nsize = freq * nrow
        shaped_arr = np.reshape(data[:nsize], (nrow, freq))
        diff = shaped_arr[1:,freq-1] - shaped_arr[:-1,freq-1]
        res['n'].append(np.var(diff)/freq/var1)
        ln_diff = np.log(shaped_arr[1:,freq-1]/shaped_arr[:-1,freq-1])
        res['ln'].append(np.var(ln_diff)/freq/lnvar1)
    return res

def validate_db_data(tday, filter = False):
    all_insts = misc.filter_main_cont(tday, filter)
    data_count = {}
    inst_list = {'min': [], 'daily': [] }
    for instID in all_insts:
        df = mysqlaccess.load_daily_data_to_df('fut_daily', instID, tday, tday)
        if len(df) <= 0:
            inst_list['daily'].append(instID)
        elif (df.close[-1] == 0) or (df.high[-1] == 0) or (df.low[-1] == 0) or df.open[-1] == 0:
            inst_list['daily'].append(instID)
        df = mysqlaccess.load_min_data_to_df('fut_min', instID, tday, tday, minid_start=300, minid_end=2115, database='blueshale')
        if len(df) <= 100:
            output = instID + ':' + str(len(df))
            inst_list['min'].append(output)
        elif df.min_id < 2055:
            output = instID + ': end earlier'
            inst_list['min'].append(output)        
    print inst_list

def hurst(ts, max_shift = 100):
    """Returns the Hurst Exponent of the time series vector ts"""
    # Create the range of lag values
    lags = range(2, max_shift)
    # Calculate the array of the variances of the lagged differences
    tau = [np.sqrt(np.std(np.subtract(ts[lag:], ts[:-lag]))) for lag in lags]
    # Use a linear fit to estimate the Hurst Exponent
    poly = np.polyfit(np.log(lags), np.log(tau), 1)
    # Return the Hurst exponent from the polyfit output
    return poly[0]*2.0

def adf_test(tseries, order = 1):
    return ts.adfuller(tseries, order)