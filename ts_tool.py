# -*- coding: utf-8 -*-
import backtest
import misc
import math
import bsopt
import mysqlaccess
import data_handler as dh
import datetime
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import pprint
from statsmodels.tsa.stattools import adfuller
from johansen_test import coint_johansen

def plot_price_series(df, ts_lab1, ts_lab2):
    #months = mdates.MonthLocator()  # every month
    fig, ax = plt.subplots()
    ax.plot(df.index, df[ts_lab1], label=ts_lab1)
    ax.plot(df.index, df[ts_lab2], label=ts_lab2)
    #ax.xaxis.set_major_locator(months)
    #ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax.grid(True)
    fig.autofmt_xdate()
    plt.xlabel('Month/Year')
    plt.ylabel('Price ($)')
    plt.title('%s and %s Daily Prices' % (ts_lab1, ts_lab2))
    plt.legend()
    plt.show()

def plot_scatter_series(df, ts_lab1, ts_lab2):
    plt.xlabel('%s Price ($)' % ts_lab1)
    plt.ylabel('%s Price ($)' % ts_lab2)
    plt.title('%s and %s Price Scatterplot' % (ts_lab1, ts_lab2))
    plt.scatter(df[ts_lab1], df[ts_lab2])
    plt.show()

def plot_series(ts):
    #months = mdates.MonthLocator()  # every month
    fig, ax = plt.subplots()
    ax.plot(ts.index, ts, label=ts.name)
    #ax.xaxis.set_major_locator(months)
    #ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    #ax.set_xlim(datetime.datetime(2012, 1, 1), datetime.datetime(2013, 1, 1))
    ax.grid(True)
    fig.autofmt_xdate()
    plt.xlabel('Month/Year')
    plt.ylabel('Price ($)')
    plt.title('Residual Plot')
    plt.legend()
    plt.plot(ts)
    plt.show()
    
def get_cont_data(asset, start_date, end_date, freq = '1m', nearby = 1, rollrule = '-10b'):
    if nearby == 0:
        mdf = mysqlaccess.load_min_data_to_df('fut_min', asset, start_date, end_date, minid_start = 300, minid_end = 2114, database = 'hist_data')
        mdf['contract'] = asset
    else:
        mdf = misc.nearby(asset, nearby, start_date, end_date, rollrule, 'm', need_shift=True, database = 'hist_data')
    mdf = backtest.cleanup_mindata(mdf, asset)
    xdf = dh.conv_ohlc_freq(mdf, freq, extra_cols = ['contract'], bar_func = dh.bar_conv_func2)
    return xdf

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

def vratio(ts, lag = 2, cor = 'hom'):  
    """ the implementation found in the blog Leinenbock  
    http://www.leinenbock.com/variance-ratio-test/  
    """  
    #t = (std((a[lag:]) - (a[1:-lag+1])))**2;  
    #b = (std((a[2:]) - (a[1:-1]) ))**2;  
    n = len(ts)  
    mu  = sum(ts[1:]-ts[:-1])/n
    m= (n-lag+1)*(1-lag/n)
    #print( mu, m, lag)  
    b=sum(np.square(ts[1:]-ts[:-1]-mu))/(n-1)  
    t=sum(np.square(ts[lag:]-ts[:-lag]-lag*mu))/m  
    vratio = t/(lag*b)
    la = float(lag)  
    if cor == 'hom':  
        varvrt=2*(2*la-1)*(la-1)/(3*la*n)  
    elif cor == 'het':  
        varvrt=0;  
        sum2=sum(np.square(ts[1:]-ts[:-1]-mu))
        for j in range(lag-1):  
            sum1a=np.square(ts[j+1:]-ts[j:-1]-mu)
            sum1b=np.square(ts[1:n-j]-ts[0:n-j-1]-mu)  
            sum1=np.dot(sum1a,sum1b)
            delta=sum1/(sum2**2)
            varvrt=varvrt+((2*(la-j)/la)**2)*delta  
    zscore = (vratio - 1) / np.sqrt(float(varvrt))
    pval = bsopt.cnorm(zscore)
    return  vratio, zscore, pval
        
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
    return adfuller(tseries, order)

def cadf_test(df1, df2, sdat, edate, idx = 'close', order = 1):
    df = pd.concat([df1[idx], df2[idx]], axis = 1, keys = ['asset1', 'asset2'])
    plot_price_series(df, 'asset1', 'asset2')
    plot_scatter_series(df, 'asset1', 'asset2')
    res = pd.stats.api.ols(y = df['asset1'], x = df['asset2'])
    beta_hr = res.beta.x
    res = df['asset1'] - beta_hr*df['asset2']
    plot_series(res)
    cadf = adf_test(res, order)
    pprint.pprint(cadf)

    res = pd.stats.api.ols(y = df['asset2'], x = df['asset1'])
    beta_hr = res.beta.x
    res = df['asset2'] - beta_hr*df['asset1']
    plot_series(res)
    cadf = adf_test(res, order)
    pprint.pprint(cadf)
    
def half_time(ts):
    ndata = ts.values
    dts = ndata[1:] - ndata[:-1]
    xlag = ndata[:-1]
    res = np.polyfit(xlag, dts, 1)
    return -np.log(2)/res[0]
    
def get_johansen(y, p):
    """
    Get the cointegration vectors at 95% level of significance
    given by the trace statistic test.
    """
    N, l = y.shape
    jres = coint_johansen(y, 0, p)
    trstat = jres.lr1                       # trace statistic
    tsignf = jres.cvt                       # critical values
    for i in range(l):
        if trstat[i] > tsignf[i, 1]:     # 0: 90%  1:95% 2: 99%
            r = i + 1
    jres.r = r
    jres.evecr = jres.evec[:, :r]
    return jres
        
def signal_stats(df, signal, time_limit = None):
    long_signal = pd.Series(np.nan, index = df.index)
    long_signal[(signal > 0) & (signal.shift(1) <= 0)] = 1
    long_signal[(signal <= 0)] = 0
    long_signal = long_signal.fillna(method = 'ffill', limit = time_limit)

    short_signal = pd.Series(np.nan, index = df.index)
    short_signal[(signal < 0) & (signal.shift(1) >= 0)] = 1
    short_signal[(signal >= 0)] = 0
    short_signal = short_signal.fillna(method = 'ffill', limit = time_limit)
    
