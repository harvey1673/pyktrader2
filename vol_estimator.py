import math
import numpy as np

def ret_vol_est(df, window=30, trading_periods=252, clean=True):
    log_return = (df['close'] / df['close'].shift(1)).apply(np.log)

    result = log_return.rolling(
        window=window,
        center=False
    ).std() * math.sqrt(trading_periods)

    if clean:
        return result.dropna()
    else:
        return result


def kurt_estimator(df, window=30, clean=True):

    log_return = (df['close'] / df['close'].shift(1)).apply(np.log)
    result = log_return.rolling(
        window=window,
        center=False
    ).kurt()

    if clean:
        return result.dropna()
    else:
        return result


def skew_estimator(df, window=30, clean=True):
    log_return = (df['close'] / df['close'].shift(1)).apply(np.log)

    result = log_return.rolling(
        window=window,
        center=False
    ).skew()

    if clean:
        return result.dropna()
    else:
        return result


def gk_vol_est(df, window = 30, trading_periods=252, clean=True):
    log_hl = (df['high'] / df['low']).apply(np.log)
    log_cc = (df['close'] / df['close'].shift(1)).apply(np.log)
    rs = 0.5 * log_hl ** 2 - (2 * math.log(2) - 1) * log_cc ** 2

    def f(v):
        return (trading_periods * v.mean()) ** 0.5

    result = rs.rolling(window=window, center=False).apply(func=f)
    if clean:
        return result.dropna()
    else:
        return result


def ht_vol_est(df, window=30, trading_periods=252, clean=True):
    log_return = (df['close'] / df['close'].shift(1)).apply(np.log)
    vol = log_return.rolling(
        window=window,
        center=False
    ).std() * math.sqrt(trading_periods)
    h = window
    n = (log_return.count() - h) + 1
    adj_factor = 1.0 / (1.0 - (h / n) + ((h ** 2 - 1) / (3 * n ** 2)))
    result = vol * adj_factor
    if clean:
        return result.dropna()
    else:
        return result


def pk_vol_est(df, window=30, trading_periods=252, clean=True):
    rs = (1.0 / (4.0 * math.log(2.0))) * ((df['high'] / df['low']).apply(np.log)) ** 2.0

    def f(v):
        return trading_periods * v.mean() ** 0.5

    result = rs.rolling(
        window=window,
        center=False
    ).apply(func=f)

    if clean:
        return result.dropna()
    else:
        return result


def rs_vol_est(df, window=30, trading_periods=252, clean=True):
    log_ho = (df['high'] / df['open']).apply(np.log)
    log_lo = (df['low'] / df['open']).apply(np.log)
    log_co = (df['close'] / df['open']).apply(np.log)

    rs = log_ho * (log_ho - log_co) + log_lo * (log_lo - log_co)

    def f(v):
        return trading_periods * v.mean() ** 0.5

    result = rs.rolling(
        window=window,
        center=False
    ).apply(func=f)

    if clean:
        return result.dropna()
    else:
        return result


def yz_vol_est(df, window=30, trading_periods=252, clean=True):
    log_ho = (df['high'] / df['open']).apply(np.log)
    log_lo = (df['low'] / df['open']).apply(np.log)
    log_co = (df['close'] / df['open']).apply(np.log)

    log_oc = (df['open'] / df['close'].shift(1)).apply(np.log)
    log_oc_sq = log_oc ** 2

    log_cc = (df['close'] / df['close'].shift(1)).apply(np.log)
    log_cc_sq = log_cc ** 2

    rs = log_ho * (log_ho - log_co) + log_lo * (log_lo - log_co)

    close_vol = log_cc_sq.rolling(
        window=window,
        center=False
    ).sum() * (1.0 / (window - 1.0))
    open_vol = log_oc_sq.rolling(
        window=window,
        center=False
    ).sum() * (1.0 / (window - 1.0))
    window_rs = rs.rolling(
        window=window,
        center=False
    ).sum() * (1.0 / (window - 1.0))

    k = 0.34 / (1 + (window + 1) / (window - 1))
    result = (open_vol + k * close_vol + (1 - k) * window_rs).apply(np.sqrt) * math.sqrt(trading_periods)

    if clean:
        return result.dropna()
    else:
        return result

