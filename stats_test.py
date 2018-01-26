# -*- coding: utf-8 -*-
import math
import bsopt
from statsmodels.tsa.stattools import coint, adfuller
import numpy as np
from numpy import log, polyfit, sqrt, std, subtract
import pandas as pd
import statsmodels.tsa.stattools as ts
import statsmodels.api
import matplotlib.pyplot as plt
from pandas.plotting import autocorrelation_plot
import warnings
import pprint
from johansen_test import coint_johansen

pd.options.mode.chained_assignment = None  # default='warn'
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

def plot_price_series(df, ts_lab1, ts_lab2):
    fig, ax = plt.subplots()
    ax.plot(df.index, df[ts_lab1], label=ts_lab1)
    ax.plot(df.index, df[ts_lab2], label=ts_lab2)
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
    fig, ax = plt.subplots()
    ax.plot(ts.index, ts, label=ts.name)
    ax.grid(True)
    fig.autofmt_xdate()
    plt.xlabel('Month/Year')
    plt.ylabel('Price ($)')
    plt.title('Residual Plot')
    plt.legend()
    plt.plot(ts)
    plt.show()

def variance_ratio(ts, freqs):
    data = ts.values
    nlen = len(data)
    res = {'n': [], 'ln': []}
    var1 = np.var(data[1:] - data[:-1])
    lnvar1 = np.var(np.log(data[1:] / data[:-1]))
    for freq in freqs:
        nrow = nlen / freq
        nsize = freq * nrow
        shaped_arr = np.reshape(data[:nsize], (nrow, freq))
        diff = shaped_arr[1:, freq - 1] - shaped_arr[:-1, freq - 1]
        res['n'].append(np.var(diff) / freq / var1)
        ln_diff = np.log(shaped_arr[1:, freq - 1] / shaped_arr[:-1, freq - 1])
        res['ln'].append(np.var(ln_diff) / freq / lnvar1)
    return res


def vratio(ts, lag=2, cor='hom'):
    """ the implementation found in the blog Leinenbock
    http://www.leinenbock.com/variance-ratio-test/
    """
    # t = (std((a[lag:]) - (a[1:-lag+1])))**2;
    # b = (std((a[2:]) - (a[1:-1]) ))**2;
    n = len(ts)
    mu = sum(ts[1:] - ts[:-1]) / n
    m = (n - lag + 1) * (1 - lag / n)
    # print( mu, m, lag)
    b = sum(np.square(ts[1:] - ts[:-1] - mu)) / (n - 1)
    t = sum(np.square(ts[lag:] - ts[:-lag] - lag * mu)) / m
    vratio = t / (lag * b)
    la = float(lag)
    if cor == 'hom':
        varvrt = 2 * (2 * la - 1) * (la - 1) / (3 * la * n)
    elif cor == 'het':
        varvrt = 0;
        sum2 = sum(np.square(ts[1:] - ts[:-1] - mu))
        for j in range(lag - 1):
            sum1a = np.square(ts[j + 1:] - ts[j:-1] - mu)
            sum1b = np.square(ts[1:n - j] - ts[0:n - j - 1] - mu)
            sum1 = np.dot(sum1a, sum1b)
            delta = sum1 / (sum2 ** 2)
            varvrt = varvrt + ((2 * (la - j) / la) ** 2) * delta
    zscore = (vratio - 1) / np.sqrt(float(varvrt))
    pval = bsopt.cnorm(zscore)
    return vratio, zscore, pval

def adf_test(tseries, order=1):
    return adfuller(tseries, order)

def cadf_test(df1, df2, sdat, edate, idx='close', order=1):
    df = pd.concat([df1[idx], df2[idx]], axis=1, keys=['asset1', 'asset2'])
    plot_price_series(df, 'asset1', 'asset2')
    plot_scatter_series(df, 'asset1', 'asset2')
    res = pd.stats.api.ols(y=df['asset1'], x=df['asset2'])
    beta_hr = res.beta.x
    res = df['asset1'] - beta_hr * df['asset2']
    plot_series(res)
    cadf = adf_test(res, order)
    pprint.pprint(cadf)

    res = pd.stats.api.ols(y=df['asset2'], x=df['asset1'])
    beta_hr = res.beta.x
    res = df['asset2'] - beta_hr * df['asset1']
    plot_series(res)
    cadf = adf_test(res, order)
    pprint.pprint(cadf)

def get_johansen(y, p):
    """
    Get the cointegration vectors at 95% level of significance
    given by the trace statistic test.
    """
    N, l = y.shape
    jres = coint_johansen(y, 0, p)
    trstat = jres.lr1  # trace statistic
    tsignf = jres.cvt  # critical values
    for i in range(l):
        if trstat[i] > tsignf[i, 1]:  # 0: 90%  1:95% 2: 99%
            r = i + 1
    jres.r = r
    jres.evecr = jres.evec[:, :r]
    return jres


def signal_stats(df, signal, time_limit=None):
    long_signal = pd.Series(np.nan, index=df.index)
    long_signal[(signal > 0) & (signal.shift(1) <= 0)] = 1
    long_signal[(signal <= 0)] = 0
    long_signal = long_signal.fillna(method='ffill', limit=time_limit)

    short_signal = pd.Series(np.nan, index=df.index)
    short_signal[(signal < 0) & (signal.shift(1) >= 0)] = 1
    short_signal[(signal >= 0)] = 0
    short_signal = short_signal.fillna(method='ffill', limit=time_limit)

def test_stationary(X, threshold=0.01):
    """
    Test if a time series is stationary
    Pre-condition:
        X - a pandas Series
    """
    pvalue = adfuller(X)[1]
    if pvalue < threshold:
        print 'p-value = ' + str(pvalue) + ' The series is likely stationary.'
        return True
    else:
        print 'p-value = ' + str(pvalue) + ' The series is likely non-stationary.'
        return False


def test_mean_reverting(X):
    """
    Test if a time series is mean reverting
    """
    Y = X.copy(False)
    cadf = adfuller(Y)
    print
    print 'Augmented Dickey Fuller test statistic =', cadf[0]
    print 'Augmented Dickey Fuller p-value =', cadf[1]
    print 'Augmented Dickey Fuller 1%, 5% and 10% test statistics =', cadf[4]


def hurst(X):
    """Returns the Hurst Exponent of the time series vector ts"""
    # Create the range of lag values
    lags = range(2, 100)

    # Calculate the array of the variances of the lagged differences
    tau = [sqrt(std(subtract(X[lag:], X[:-lag]))) for lag in lags]

    # Use a linear fit to estimate the Hurst Exponent
    poly = polyfit(log(lags), log(tau), 1)

    # Return the Hurst exponent from the polyfit output
    return poly[0] * 2.0


def half_life(series):
    """
    Caculate half life of a mean reverting time series
    Pre-condition:
        series - a mean reverting pandas series
    """
    # re-initialize series's index
    X = series.copy(False)
    X.index = range(len(X))
    # Run OLS regression on spread series and lagged version of itself
    spread_lag = X.shift(1)
    spread_lag.ix[0] = spread_lag.ix[1]
    spread_ret = X - spread_lag
    spread_ret.ix[0] = spread_ret.ix[1]
    spread_lag2 = statsmodels.api.add_constant(spread_lag)
    model = statsmodels.api.OLS(spread_ret, spread_lag2)
    res = model.fit()
    halflife = -np.log(2) / res.params[1]
    return halflife


def autocorrelation_graph(X):
    """
    Plot the autocorrelation graph of a pandas series
    Pre-condition:
        X - a pandas Series
    """
    plt.figure(figsize=(10, 5))
    autocorrelation_plot(X)
    plt.show()

def price_seasonality(data):
    data = data.copy()
    px = data.columns[1]
    start_year = data['date'][0].year
    end_year = data['date'].iloc[-1].year
    num_years = end_year - start_year + 1

    for i in range(num_years):
        temp = data[data['date'].dt.year == start_year + i]
        #        temp[px] = pd.ewma(temp[px], span=10)
        temp['trend'] = pd.ewma(temp[px], span=250)
        plt.plot(temp['date'], temp[px] - temp['trend'])
        plt.title("Seasonality plot of year {}".format(start_year + i))
        plt.xticks(rotation="vertical")
        plt.show()

def vol_seasonality(data):
    data = data.copy()
    px = data.columns[1]
    start_year = data['date'][0].year
    end_year = data['date'].iloc[-1].year
    num_years = end_year - start_year + 1

    for i in range(num_years):
        temp = data[data['date'].dt.year == start_year + i]
        temp['log'] = np.log(temp[px])
        temp['log_ret'] = temp['log'] - temp['log'].shift()
        plt.plot(temp['date'], pd.rolling_std(temp['log_ret'], 10))
        plt.title("Volatiliy seasonality plot of year {}".format(start_year + i))
        plt.xticks(rotation="vertical")
        plt.show()

def cross_correlation(ts_pair, lag = 100, mode = ['lndiff', 'lndiff'], supress = True):
    input = []
    for ts, m in zip(ts_pair, mode):
        data = ts
        if m:
            if 'ln' in m:
                data = np.log(data)
            if 'diff' in m:
                data = data - data.shift(1)
        input.append(data)
    corrs = pd.Series([input[0].corr(input[1].shift(x)) for x in np.arange(-lag, lag)], index = np.arange(-lag, lag))
    idx = corrs.idxmax()
    plt.annotate('series 1 shift %d' % idx , xy= (idx, corrs[idx]), xytext=(idx+4, corrs[idx]))
    plt.axvline(x=idx, ls='--', color='r')
    plt.plot(np.arange(-lag, lag), corrs)
    plt.show()
    if not supress:
        return corrs

class InputDataException(Exception):
    pass


if __name__ == '__main__':
    pass
