import numpy as np
import pandas as pd
import pycmqlib3.analytics.data_handler as dh
from pycmqlib3.utility import misc
from pycmqlib3.analytics.btmetrics import *
from pycmqlib3.analytics.tstool import *


def get_asset_vols(df, product_list, vol_win, vol_type='atr'):
    if vol_type == 'atr':
        df_list = []
        for asset in product_list:
            asset_df = df.loc[:, (df.columns.get_level_values(0) == asset)
                                  & (df.columns.get_level_values(1) == 'c1')].droplevel([0, 1], axis=1)
            vol_ts = dh.ATR(asset_df, vol_win).fillna(method='bfill')
            df_list.append(vol_ts)
        vol_df = pd.concat(df_list, axis=1, join='outer').fillna(method='ffill')
        vol_df.columns = product_list
    elif vol_type == 'pct_chg':
        df_list = []
        for asset in product_list:
            vol_ts = df[(asset, 'c1', 'close')].pct_change().rolling(vol_win).std()
            df_list.append(vol_ts)
        vol_df = pd.concat(df_list, axis=1, join='outer').fillna(method='ffill')
        vol_df.columns = product_list
    elif vol_type == 'lret':
        df_list = []
        for asset in product_list:
            vol_ts = (np.log(df[(asset, 'c1', 'close')])
                      - np.log(df[(asset, 'c1', 'close')].shift(1))).rolling(vol_win).std()
            #vol_ts = vol_ts * df[(asset, 'c1', 'close')]
            df_list.append(vol_ts)
        vol_df = pd.concat(df_list, axis=1, join='outer').fillna(method='ffill')
        vol_df.columns = product_list
    elif vol_type == 'close':
        vol_df = df.loc[:, df.columns.get_level_values(0).isin(product_list)
                           & (df.columns.get_level_values(1) == 'c1')].droplevel([0, 1], axis=1)
        vol_df = vol_df[product_list]
    return vol_df


def default_signal_gen(df, input_args):
    shift_mode = input_args['shift_mode']
    rev_char = input_args['rev_char']
    product_list = input_args['product_list']
    win = input_args['win']
    ma_win = input_args['ma_win']
    rebal_freq = input_args['rebal_freq']
    signal_name = input_args.get('signal_name', "ryield")
    params = input_args.get('params', [0.0, 0.0])
    xs_signal = input_args.get('xs_signal', '')
    xs_params = input_args.get('xs_params', {})
    exp_mean = input_args.get('exp_mean', False)
    pos_func, pos_args, _ = input_args.get('pos_map', (None, {}, ''))

    xdf = df.loc[:, df.columns.get_level_values(0).isin(product_list)].copy(deep=True)

    for asset in product_list:
        if shift_mode == 1:
            xdf[(asset, 'factor', 'ryield')] = (np.log(xdf[(asset, 'c1', 'close')] - xdf[(asset, 'c1', 'shift')])
                                                - np.log(xdf[(asset, 'c2', 'close')] - xdf[(asset, 'c2', 'shift')])) \
                                               / (xdf[(asset, 'c2', 'mth')] - xdf[(asset, 'c1', 'mth')]) * 12.0
        elif shift_mode == 2:
            xdf[(asset, 'factor', 'ryield')] = \
                (np.log(xdf[(asset, 'c1', 'close')]) - np.log(xdf[(asset, 'c2', 'close')]) \
                 - xdf[(asset, 'c1', 'shift')] + xdf[(asset, 'c2', 'shift')]) \
                / (xdf[(asset, 'c2', 'mth')] - xdf[(asset, 'c1', 'mth')]) * 12.0
        else:
            xdf[(asset, 'factor', 'ryield')] = \
                (np.log(xdf[(asset, 'c1', 'close')]) - np.log(xdf[(asset, 'c2', 'close')])) \
                / (xdf[(asset, 'c2', 'mth')] - xdf[(asset, 'c1', 'mth')]) * 12.0
        for i in [1, 2]:
            if shift_mode == 1:
                xdf[(asset, f'c{i}', 'lr')] = \
                    np.log(xdf[(asset, f'c{i}', 'close')] - xdf[(asset, f'c{i}', 'shift')]) \
                    - np.log(xdf[(asset, f'c{i}', 'close')].shift(1) - xdf[(asset, f'c{i}', 'shift')])
            else:
                xdf[(asset, f'c{i}', 'lr')] = \
                    np.log(xdf[(asset, f'c{i}', 'close')]) - np.log(xdf[(asset, f'c{i}', 'close')].shift(1))
        xdf[(asset, 'factor', 'basmom')] = xdf[(asset, 'c1', 'lr')].rolling(win).sum() - xdf[
            (asset, 'c2', 'lr')].rolling(win).sum()
        xdf[(asset, 'factor', 'mom')] = xdf[(asset, 'c1', 'lr')].rolling(win).sum()
        xdf[(asset, 'factor', 'upratio')] = xdf[(asset, 'c1', 'lr')].rolling(win).agg(
            lambda x: (x > 0).sum() / win) - 0.5
        xdf[(asset, 'factor', 'skew')] = xdf[(asset, 'c1', 'lr')].rolling(win).skew()
        xdf[(asset, 'factor', 'kurt')] = xdf[(asset, 'c1', 'lr')].rolling(win).kurt()
        if 'rsi' in signal_name:
            asset_df = xdf.loc[:, (xdf.columns.get_level_values(0) == asset)
                                  & (xdf.columns.get_level_values(1) == 'c1')].droplevel([0, 1], axis=1)
            rsi_output = dh.RSI_F(asset_df, win)
            xdf[(asset, 'factor', 'rsi')] = rsi_output['RSI' + str(win)].values
        elif 'hlbrk' in signal_name:
            chmax = xdf[(asset, 'c1', 'high')].rolling(win).max()
            chmin = xdf[(asset, 'c1', 'low')].rolling(win).min()
            chavg = (chmax + chmin) / 2.0
            xdf[(asset, 'factor', 'hlbrk')] = (xdf[(asset, 'c1', 'close')] - chavg) / (chmax - chmin)
        elif 'macd' in signal_name:
            ema1 = xdf[(asset, 'c1', 'close')].ewm(span=win).mean()
            ema2 = xdf[(asset, 'c1', 'close')].ewm(span=int(win * params[0])).mean()
            mstd = xdf[(asset, 'c1', 'close')].diff().ewm(span=int(win * params[1]), min_periods=10).std()
            xdf[(asset, 'factor', 'macd')] = (ema1 - ema2) / mstd
        elif signal_name == 'mixmom':
            xdf[(asset, 'factor', 'mixmom')] = (xdf[(asset, 'factor', 'mom')] * xdf[
                (asset, 'factor', 'upratio')]).apply(
                lambda x: x if x > 0 else 0) * xdf[(asset, 'factor', 'mom')].apply(lambda x: misc.sign(x))

        data_field = signal_name.replace(rev_char, '')
        if 'dff' == data_field[-3:]:
            ref_field = data_field[:-3]
            xdf[(asset, 'factor', data_field)] = xdf[(asset, 'factor', ref_field)].diff(periods=ma_win)
        elif 'sma' == signal_name[-3:]:
            ref_field = data_field[:-3]
            xdf[(asset, 'factor', data_field)] = xdf[(asset, 'factor', ref_field)].rolling(ma_win).mean()
        elif 'ema' == data_field[-3:]:
            ref_field = data_field[:-3]
            xdf[(asset, 'factor', data_field)] = xdf[(asset, 'factor', ref_field)].ewm(span=ma_win,
                                                                                       min_periods=ma_win//2,
                                                                                       ignore_na=True).mean()
        elif 'xma' == data_field[-3:]:
            ref_field = data_field[:-3]
            xdf[(asset, 'factor', data_field)] = xdf[(asset, 'factor', ref_field)] \
                                                 - xdf[(asset, 'factor', ref_field)].rolling(ma_win).mean()
        elif 'xea' == data_field[-3:]:
            ref_field = data_field[:-3]
            xdf[(asset, 'factor', data_field)] = xdf[(asset, 'factor', ref_field)] \
                                                 - xdf[(asset, 'factor', ref_field)].ewm(span=ma_win,
                                                                                         min_periods=ma_win//2,
                                                                                         ignore_na=True).mean()
        elif 'nma' == data_field[-3:]:
            ref_field = data_field[:-3]
            xdf[(asset, 'factor', data_field)] = xdf[(asset, 'factor', ref_field)] \
                                                 / xdf[(asset, 'factor', ref_field)].rolling(ma_win).std()
        elif 'nmb' == data_field[-3:]:
            ref_field = data_field[:-3]
            xdf[(asset, 'factor', data_field)] = xdf[(asset, 'factor', ref_field)] \
                                                 / ((xdf[(asset, 'factor', ref_field)]**2).rolling(ma_win).mean()**0.5)
        elif 'elv' == data_field[-3:]:
            ref_field = data_field[:-3]
            xdf[(asset, 'factor', data_field)] = (xdf[(asset, 'factor', ref_field)]
                                                  - xdf[(asset, 'factor', ref_field)].ewm(span=ma_win,
                                                                                          min_periods=ma_win//2,
                                                                                          ignore_na=True).mean()) \
                                                 / (xdf[(asset, 'factor', ref_field)].ewm(span=ma_win,
                                                                                          min_periods=ma_win//2,
                                                                                          ignore_na=True).std())
        elif 'zlv' == data_field[-3:]:
            ref_field = data_field[:-3]
            xdf[(asset, 'factor', data_field)] = (xdf[(asset, 'factor', ref_field)]
                                                  - xdf[(asset, 'factor', ref_field)].rolling(ma_win).mean()) \
                                                 / xdf[(asset, 'factor', ref_field)].rolling(ma_win).std()
        elif 'qtl' == data_field[-3:]:
            ref_field = data_field[:-3]
            xdf[(asset, 'factor', data_field)] = 2.0 * (
                    rolling_percentile(xdf[(asset, 'factor', ref_field)], win=ma_win) - 0.5)

        if pos_func:
            xdf[(asset, 'factor', data_field)] = xdf[(asset, 'factor', data_field)].apply(
                lambda x: pos_func(x, **pos_args))
        if rev_char in signal_name:
            xdf[(asset, 'factor', 'signal')] = - xdf[(asset, 'factor', data_field)]
        else:
            xdf[(asset, 'factor', 'signal')] = xdf[(asset, 'factor', data_field)]

    adf = xdf.loc[:, xdf.columns.get_level_values(1) == 'factor'].droplevel([1], axis=1)
    sig_df = adf.loc[:, adf.columns.get_level_values(1) == 'signal'].droplevel([1], axis=1)
    # print("before averaging", sig_df)
    prod_count = sig_df.apply(lambda x: x.count() if x.count() > 0 else np.nan, axis=1)

    if xs_signal == 'rank_cutoff':
        cutoff = xs_params.get('cutoff', 0.2)
        thres = int(1/cutoff)
        sig_df = sig_df[prod_count >= thres]
        prod_count = sig_df.apply(lambda x: x.count() if x.count() > 0 else np.nan, axis=1)
        rank_df = sig_df.rank(axis=1)
        kcut = (prod_count * cutoff).astype('int')
        upper_rank = prod_count - kcut
        lower_rank = kcut + 1
        sig_df = rank_df.gt(upper_rank, axis=0)*1.0 - rank_df.lt(lower_rank, axis=0)*1.0
    elif xs_signal == 'demedian':
        thres = 2
        sig_df = sig_df[prod_count >= thres]
        median_ts = sig_df.quantile(0.5, axis=1)
        sig_df = sig_df.sub(median_ts, axis=0)
    elif xs_signal == 'demean':
        thres = 2
        sig_df = sig_df[prod_count >= thres]
        mean_ts = sig_df.mean(axis=1)
        sig_df = sig_df.sub(mean_ts, axis=0)
    elif xs_signal == 'rank':
        thres = 3
        sig_df = sig_df[prod_count >= thres]
        prod_count = sig_df.apply(lambda x: x.count() if x.count() > 0 else np.nan, axis=1)
        rank_df = sig_df.rank(axis=1)
        median_ts = rank_df.quantile(0.5, axis=1)
        sig_df = rank_df.sub(median_ts, axis=0).div(prod_count, axis=0) * 2.0
    elif len(xs_signal) > 0:
        print('unsupported xs signal types')
    if exp_mean:
        sig_df = tstool.exp_smooth(sig_df, hl=rebal_freq, fill_backward=True)
    else:
        sig_df = sig_df.rolling(rebal_freq).mean()
    # print("after averaging", sig_df)
    return sig_df


def hc_rb_diff(df, input_args):
    shift_mode = input_args['shift_mode']
    product_list = input_args['product_list']
    win = input_args['win']
    xdf = df.loc[:, df.columns.get_level_values(0).isin(['rb', 'hc'])].copy(deep=True)
    xdf = xdf['2014-07-01':]
    if shift_mode == 2:
        xdf[('rb', 'c1', 'px_chg')] = np.log(xdf[('rb', 'c1', 'close')]).diff()
        xdf[('hc', 'c1', 'px_chg')] = np.log(xdf[('hc', 'c1', 'close')]).diff()
    else:
        xdf[('rb', 'c1', 'px_chg')] = xdf[('rb', 'c1', 'close')].diff()
        xdf[('hc', 'c1', 'px_chg')] = xdf[('hc', 'c1', 'close')].diff()
    hc_rb_diff = xdf[('hc', 'c1', 'px_chg')] - xdf[('rb', 'c1', 'px_chg')]
    signal_ts = hc_rb_diff.ewm(span=win).mean() / hc_rb_diff.ewm(span=win).std()
    signal_df = pd.concat([signal_ts] * len(product_list), axis=1)
    signal_df.columns = product_list
    return signal_df


def leader_lagger(df, input_args):
    leadlag_port = {
        'ferrous': {'lead': ['hc', 'rb', ],
                    'lag': ['rb', 'hc', 'i', 'j', 'jm', 'FG', 'SA', 'UR', 'SM',],
                    'param_rng': [40, 60, 2],
                    },
        'base': {'lead': ['al'],
                 'lag': ['al', 'ni', 'sn', 'ss', ],  # 'zn', 'cu'
                 'param_rng': [40, 60, 2],
                 },
        'petchem': {'lead': ['v'],
                    'lag': ['TA', 'MA', 'pp', 'eg', 'eb', 'PF', ],
                    'param_rng': [40, 60, 2],
                    },
        'oil': {'lead': ['sc'],
                'lag': ['sc', 'pg', 'bu', ],
                'param_rng': [20, 30, 2],
                },
        'bean': {'lead': ['b'],
                 'lag': ['p', 'y', 'OI', ],
                 'param_rng': [60, 80, 2],
                 },
    }
    product_list = input_args['product_list']
    signal_cap = input_args.get('signal_cap', None)
    conv_func = input_args.get('conv_func', 'qtl')
    signal_df = pd.DataFrame(index=df.index, columns=product_list)
    for asset in product_list:
        for sector in leadlag_port:
            if asset in leadlag_port[sector]['lag']:
                signal_list = []
                for lead_prod in leadlag_port[sector]['lead']:
                    feature_ts = df[(lead_prod, 'c1', 'close')]
                    signal_ts = calc_conv_signal(feature_ts.dropna(), conv_func,
                                                 leadlag_port[sector]['param_rng'], signal_cap=signal_cap)
                    signal_list.append(signal_ts)
                signal_df[asset] = pd.concat(signal_list, axis=1).mean(axis=1)
                break
            else:
                signal_df[asset] = 0
    return signal_df


def generate_holding_from_signal(signal_df, vol_df, risk_scaling=1.0, asset_scaling=True):
    vol_df = vol_df.reindex(index=signal_df.index).fillna(method='ffill')
    sig_df = signal_df.div(vol_df)
    nperiod, nasset = sig_df.shape
    prod_count = sig_df.apply(lambda x: x.count() if x.count() > 0 else np.nan, axis=1)
    if asset_scaling:
        scaling = risk_scaling / prod_count
    else:
        scaling = pd.Series(risk_scaling/nasset, index=prod_count.index)
    pos_df = sig_df.mul(scaling, axis='rows').shift(1).fillna(0.0)
    return pos_df


def get_px_chg(df, exec_mode='open', chg_type='px', contract='c1'):
    xdf = df.loc[:, df.columns.get_level_values(1) == contract].droplevel([1], axis=1)
    for asset in df.columns.get_level_values(0).unique():
        if exec_mode == 'close':
            xdf[(asset, 'traded_price')] = xdf[(asset, exec_mode)]
        else:
            xdf[(asset, 'traded_price')] = xdf[(asset, exec_mode)].shift(-1)
            xdf.loc[xdf.index[-1], (asset, 'traded_price')] = xdf.loc[xdf.index[-1], (asset, 'close')]
        if chg_type == 'px':
            xdf[(asset, 'px_chg')] = xdf[(asset, 'traded_price')].diff()
        elif chg_type == 'pct':
            xdf[(asset, 'px_chg')] = xdf[(asset, 'traded_price')].pct_change()
    xdf = xdf.loc[:, xdf.columns.get_level_values(1) == 'px_chg'].droplevel([1], axis=1)
    return xdf


def run_backtest(df, input_args):
    product_list = input_args['product_list']
    vol_win = input_args['std_win']
    total_risk = input_args.get('total_risk', 5000000.0)
    shift_mode = input_args.get('shift_mode', 2)
    asset_scaling = input_args.get('asset_scaling', False)
    exec_mode = input_args.get('exec_mode', 'open')
    signal_func = input_args.get('signal_func', default_signal_gen)
    signal_df = signal_func(df, input_args)

    start_date = input_args.get('start_date', None)
    end_date = input_args.get('end_date', None)

    if start_date:
        signal_df = signal_df[signal_df.index >= pd.to_datetime(start_date)]
    if end_date:
        signal_df = signal_df[signal_df.index <= pd.to_datetime(end_date)]

    if shift_mode == 1:
        vol_df = get_asset_vols(df, product_list, vol_win=vol_win, vol_type='atr')
    elif shift_mode == 2:
        vol_df = get_asset_vols(df, product_list, vol_win=vol_win, vol_type='pct_chg')
    else:
        vol_df = get_asset_vols(df, product_list, vol_win=vol_win, vol_type='close')

    holding = generate_holding_from_signal(signal_df, vol_df,
                                           risk_scaling=total_risk,
                                           asset_scaling=asset_scaling)
    if shift_mode == 2:
        df_pxchg = get_px_chg(df, exec_mode=exec_mode, chg_type='pct', contract='c1')
    else:
        df_pxchg = get_px_chg(df, exec_mode=exec_mode, chg_type='px', contract='c1')
    df_pxchg = df_pxchg.reindex(index=holding.index)

    bt_metrics = MetricsBase(holdings=holding[product_list],
                             returns=df_pxchg[product_list])
    return bt_metrics


def get_beta_neutral_returns(df, asset_pairs):
    beta_ret_dict = {}
    betas_dict = {}
    for trade_asset, index_asset in asset_pairs:
        asset_df = df[[(index_asset, 'c1', 'close'), (trade_asset, 'c1', 'close')]].copy(deep=True)
        asset_df = asset_df.droplevel([1, 2], axis=1)
        asset_df = asset_df.dropna(subset=[trade_asset]).ffill()
        for asset in asset_df:
            asset_df[f'{asset}_pct'] = asset_df[asset].pct_change().rolling(5).mean()
        asset_df['beta'] = asset_df[f'{index_asset}_pct'].rolling(244).cov(asset_df[f'{trade_asset}_pct'])\
                           / asset_df[f'{index_asset}_pct'].rolling(244).var()
        key = '_'.join([trade_asset, index_asset])
        asset_df[key] = asset_df[trade_asset].pct_change() \
                        - asset_df['beta'] * asset_df[index_asset].pct_change().fillna(0)
        beta_ret_dict[key] = asset_df[key].dropna()
        betas_dict[key] = asset_df['beta']
    return beta_ret_dict, betas_dict

