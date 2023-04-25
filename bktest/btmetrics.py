from . import tstool
import copy
import math
import pandas as pd
import numpy as np
import workdays
from datetime import date, timedelta
from pycmqlib3.utility.misc import get_first_day_of_month, Holiday_Map, day_shift


def sharpe(ts, cum_pnl=True, business_days_per_year=tstool.PNL_BDAYS):
    if cum_pnl:
        ts = ts.diff(1).dropna()
    return ts.mean() / ts.std() * np.sqrt(business_days_per_year)


def sortino(ts, cum_pnl=True, business_days_per_year=tstool.PNL_BDAYS):
    if cum_pnl:
        ts = ts.diff(1).dropna()
    return ts.mean() / (ts[ts<0].std()) * np.sqrt(business_days_per_year)


def calmar(ts, cum_pnl=True, business_days_per_year=tstool.PNL_BDAYS):
    if cum_pnl:
        max_dd, _ = max_drawdown(ts)
        daily_pnl = ts.diff(1).dropna()
    else:
        daily_pnl = ts
        cum_pnl = daily_pnl.cumsum()
        max_dd = max_drawdown(cum_pnl)
    if max_dd >= 0:
        return np.nan
    else:
        return daily_pnl.mean() * business_days_per_year / (-max_dd)


def max_drawdown(ts, cum_pnl=True):
    if cum_pnl:
        cum_pnl = ts
    else:
        cum_pnl = ts.cumsum()
    dd = cum_pnl - cum_pnl.cummax()
    max_dd = dd.min()
    return max_dd


class MetricsBase(object):
    def __init__(self, holdings, returns, portfolio_obj=None, limits=None,
                 shift_holdings=0, backtest=True, hols='CHN',
                 business_days_per_year=tstool.PNL_BDAYS):
        holdings.index = pd.to_datetime(holdings.index)
        returns.index = pd.to_datetime(returns.index)
        self.raw_holdings, self.raw_returns = holdings, returns
        self.holdings, self.returns = self._align_holding_returns(holdings, returns, limits, backtest)
        self.holdings = self.holdings.shift(shift_holdings)
        self.portfolio_obj = portfolio_obj
        self.date_range = self.holdings.index
        self.universe = self.holdings.columns
        self.holidays = Holiday_Map.get(hols, [])
        self.business_days_per_year = business_days_per_year

    def _align_holding_returns(self, holdings, returns, limits, backtest):
        import warnings

        holdings = copy.deepcopy(holdings).sort_index()
        returns = copy.deepcopy(returns).sort_index().dropna(how='all')

        first_index = holdings.index[0]
        last_index = holdings.index[-1]
        if backtest:
            aligned_return = returns.loc[first_index: last_index]
        else:
            aligned_return = returns.loc[first_index:]

        holdings = holdings.reindex_like(aligned_return, method='ffill', limit=limits)
        date_range = holdings.index.intersection(aligned_return.index)

        if set(returns.columns) < set(holdings.columns):
            warnings.warn("some assets in holdings do not have a corresponding return ts")
        
        universe = returns.columns.intersection(holdings.columns)
        return holdings.loc[date_range, universe], returns.loc[date_range, universe]

    def _perf_metric(self, pnl_df, metric):
        func_dict = {
            'sharpe': sharpe,
            'sortino': sortino,
            'calmar': calmar,
            'maxdd': max_drawdown,
        }
        res_ts = pd.Series(index=pnl_df.columns)
        for col in pnl_df.columns:
            if metric in func_dict:
                args = {'cum_pnl': False}
                if metric in ['sharpe', 'sortino', 'calmar']:
                    args['business_days_per_year'] = self.business_days_per_year
                res_ts.loc[col] = func_dict[metric](pnl_df[col], **args)
            else:
                res_ts.loc[col] = getattr(pnl_df[col], metric)()
        return res_ts

    def _calculate_perf_metric(self, pnl_df, metric='sharpe', tenors=True):
        df = copy.deepcopy(pnl_df)
        if isinstance(df, pd.Series):
            df = df.to_frame(name='total')
        result = {}
        result[metric] = self._perf_metric(df, metric)

        if isinstance(tenors, bool) and tenors:
            mid_point = int(math.floor(len(df.index) / 2.0))
            sample = df.iloc[:mid_point]
            result[f'{metric}_fh'] = self._perf_metric(sample, metric)
            sample = df.iloc[mid_point + 1:]
            result[f'{metric}_sh'] = self._perf_metric(sample, metric)
        elif isinstance(tenors, list):
            edate = df.index[-1]
            for tenor in tenors:
                sdate = pd.to_datetime(day_shift(edate, '-' + tenor))
                sample = df.loc[sdate:]
                result[f'{metric}_{tenor}'] = self._perf_metric(sample, metric)

        result = pd.DataFrame(result).T
        if isinstance(pnl_df, pd.Series):
            result = result['total']
        return result

    def _calculate_sharpe(self, pnl_df, tenors=True):
        df = copy.deepcopy(pnl_df)
        if isinstance(df, pd.Series):
            df = df.to_frame(name='total')
        
        result = {}
        result['sharpe'] = df.mean(skipna=True, axis=0)/df.std(skipna=True, axis=0)

        if isinstance(tenors, bool) and tenors:
            mid_point = int(math.floor(len(df.index)/2.0))
            sample = df.iloc[:mid_point]
            result['sharpe_fh'] = sample.mean(skipna=True, axis=0)/sample.std(skipna=True, axis=0)
            sample = df.iloc[mid_point + 1:]
            result['sharpe_sh'] = sample.mean(skipna=True, axis=0)/sample.std(skipna=True, axis=0)
        elif isinstance(tenors, list):
            edate = df.index[-1]
            for tenor in tenors:
                sdate = pd.to_datetime(day_shift(edate, '-' + tenor))
                sample = df.loc[sdate:]
                result[f'sharpe_{tenor}'] = sample.mean(skipna=True, axis=0)/sample.std(skipna=True, axis=0)

        result = pd.DataFrame(result).T
        if isinstance(pnl_df, pd.Series):
            result = result['total']
        return np.sqrt(self.business_days_per_year) * result

    def _lagged_portfolio_pnl(self, **kwargs):
        return self._lagged_asset_pnl(**kwargs).sum(axis=1, skipna = True)

    def _smoothed_portfolio_pnl(self, **kwargs):
        return self._smoothed_asset_pnl(**kwargs).sum(axis=1, skipna = True)

    def _calc_pnl(self, holdings):
        if holdings is None:
            holdings = self.holdings
        return holdings.multiply(self.returns)

    def _lagged_asset_pnl(self, holdings=None, shift=0):
        if holdings is None:
            holdings = self.holdings
        return self._calc_pnl(tstool.lag(holdings, shift))

    def _smoothed_asset_pnl(self, hl, holdings=None):
        if holdings is None:
            holdings = self.holdings
        return self._calc_pnl(tstool.exp_smooth(holdings, hl))

    def _check_log_safe(self, returns):
        if isinstance(returns, pd.Series):
            bad_counts = (returns < -1) * 1.0
        else:
            bad_counts = (returns < -1).sum(axis=1)
        bad_dates = returns.index[bad_counts.values > 0]
        if len(bad_dates) > 0:
            raise Warning(str(len(bad_dates)) + " instances of returns < -1 identified (eg: " +
                          str(bad_dates[0]) + ") - not safe to convert to log returns.")

    def _cumpnl(self, input_df, use_log_returns=False, limits=None):
        df = copy.deepcopy(input_df).dropna(how='all').fillna(0, limit=limits)
        if use_log_returns:
            self._check_log_safe(df)
            cumpnl = np.log(1+df).cumsum()
        else:
            cumpnl = df.cumsum()
        return cumpnl

    def _calculate_pnl_stats(self, holdings, shift=0, use_log_returns=False, tenors=True, perf_metrics=['sharpe']):
        asset_pnl = self._lagged_asset_pnl(holdings=holdings, shift=shift)
        portfolio_pnl = self._lagged_portfolio_pnl(holdings=holdings, shift=shift)
        pnl_per_trade = 100 * 100 * asset_pnl.mean(axis=0) / self.holdings.diff().abs().mean()
        turnover = 100 * self.holdings.diff().abs().mean() / self.holdings.abs().mean()
        asset_sharpe_stats = asset_pnl.apply(lambda x: self._calculate_sharpe(x, tenors=tenors), axis=0)
        pnl_stats = {
            'asset_pnl': asset_pnl,
            'asset_cumpnl': self._cumpnl(asset_pnl, use_log_returns=use_log_returns),
            'portfolio_pnl': portfolio_pnl.to_frame(name='total'),
            'portfolio_cumpnl': self._cumpnl(portfolio_pnl, use_log_returns=use_log_returns).to_frame(name='total'),
            'asset_sharpe_stats': asset_sharpe_stats,
            'pnl_per_trade': pnl_per_trade,
            'turnover': turnover,
        }

        for metric in perf_metrics:
            pnl_stats[metric] = self._calculate_perf_metric(portfolio_pnl, metric, tenors=tenors)
        return pnl_stats

    def calculate_daily_pnl(self, trade_prices, close_prices, mode='ret'):
        holdings, trade_prices = self._align_holding_returns(self.holdings, trade_prices, limits=None, backtest=True)
        holdings, close_prices = self._align_holding_returns(self.holdings, close_prices, limits=None, backtest=True)
        if mode == 'ret':
            pnl_df = self.holdings.shift(1).multiply(close_prices.pct_change().fillna(0))
            pnl_df += (self.holdings - self.holdings.shift(1).fillna(0)).multiply(close_prices/trade_prices-1)
        else:
            pnl_df = self.holdings.shift(1).multiply(close_prices.diff().fillna(0))
            pnl_df += (self.holdings - self.holdings.shift(1).fillna(0)).multiply(close_prices - trade_prices)
        return pnl_df

    def asset_returns(self):
        cum_log_returns = np.log(1+self.returns).cumsum(axis=0)
        asset_returns_stats = {'asset_cum_log_returns': cum_log_returns}
        return asset_returns_stats

    def calculate_pnl_stats(self, **kwargs):
        return self._calculate_pnl_stats(holdings=self.holdings, **kwargs)

    def annual_pnl(self, use_log_returns=False):
        portfolio_pnl = self._lagged_portfolio_pnl().to_frame(name='total')
        portfolio_pnl['Year'] = portfolio_pnl.index.year
        portfolio_pnl.index = [i.replace(year=2016) for i in portfolio_pnl.index]
        annual_pnl = portfolio_pnl.pivot(columns='Year', values='total').fillna(0.0)
        annual_sharpe_stats = self._calculate_sharpe(annual_pnl)
        group_pnl = {
            'years': annual_pnl.columns,
            'pnl': annual_pnl,
            'cumlog_pnl': self._cumpnl(annual_pnl, use_log_returns=use_log_returns),
            'sharpe_stats': annual_sharpe_stats,
        }
        return group_pnl

    def seasonal_pnl(self, use_log_returns=False):
        portfolio_pnl = self._lagged_portfolio_pnl().to_frame(name='total')
        portfolio_pnl['Month'] = portfolio_pnl.index.month
        portfolio_pnl.index = [i.replace(month=1) for i in portfolio_pnl.index]
        seasonal_pnl = portfolio_pnl.pivot(columns='Month', values='total').fillna(0.0)
        seasonal_stats = self._calculate_sharpe(seasonal_pnl)
        group_pnl = {
            'years': list(set(self.holdings.index.year)),
            'pnl': seasonal_pnl,
            'cumlog_pnl': self._cumpnl(seasonal_pnl, use_log_returns=use_log_returns, limits=4),
            'sharpe_stats': seasonal_stats,
        }
        return group_pnl

    def week_pnl(self, use_log_returns=False):
        portfolio_pnl = self._lagged_portfolio_pnl().to_frame(name='total')
        portfolio_pnl['WeekDay'] = portfolio_pnl.index.weekday
        portfolio_pnl.index = [i-timedelta(days=i.weekday()) for i in portfolio_pnl.index]
        weekday_pnl = portfolio_pnl.pivot(columns='WeekDay', values='total').fillna(0.0)
        weekday_stats = self._calculate_sharpe(weekday_pnl)
        group_pnl = {
            'years': list(set(self.holdings.index.year)),
            'pnl': weekday_pnl,
            'cumlog_pnl': self._cumpnl(weekday_pnl, use_log_returns=use_log_returns, limits=4),
            'sharpe_stats': weekday_stats,
        }

        return group_pnl
    
    def _business_day_in_month(self, date_index):
        new_index = [None] * len(date_index)
        new_col = [None] * len(date_index)
        for t, t_date in enumerate(date_index):            
            bd = workdays.networkdays(get_first_day_of_month(t_date), t_date, self.holidays)
            if bd <= 4:
                new_col[t] = '1-4'
                new_index[t] = t_date
            elif bd <= 9:
                new_col[t] = '5-9'
                new_index[t] = t_date.replace(day = bd-4)
            elif bd <= 14:
                new_col[t] = '10-14'
                new_index[t] = t_date.replace(day = bd-9)                
            elif bd <= 20:
                new_col[t] = '15-20'
                new_index[t] = t_date.replace(day = bd-14)
            else:
                new_col[t] = '>20'
                new_index[t] = t_date.replace(day = bd-19)
        
        return new_index, new_col

    def monthday_pnl(self, use_log_returns=False):
        portfolio_pnl = self._lagged_portfolio_pnl().to_frame(name='total')
        new_index, new_col = self._business_day_in_month(portfolio_pnl.index)
        portfolio_pnl.index = new_index
        portfolio_pnl['MonthDay'] = new_col
        monthday_pnl = portfolio_pnl.pivot(columns = 'MonthDay', values = 'total')
        monthday_stats = self._calculate_sharpe(monthday_pnl)

        group_pnl = {
            'years': list(set(self.holdings.index.year)),
            'pnl': monthday_pnl,
            'cumlog_pnl': self._cumpnl(monthday_pnl, use_log_returns=use_log_returns, limits=2),
            'sharpe_stats': monthday_stats,
        }

        return group_pnl

    def long_short_pnl(self, use_log_returns=False):
        long_holdings = copy.deepcopy(self.holdings)
        long_holdings[long_holdings < 0] = 0
        short_holdings = copy.deepcopy(self.holdings)
        short_holdings[short_holdings > 0] = 0
        long_short_pnl = {
            'total_pnl_stat': self._calculate_pnl_stats(holdings=self.holdings, use_log_returns=use_log_returns),
            'long_pnl_stat': self._calculate_pnl_stats(holdings=long_holdings, use_log_returns=use_log_returns),
            'short_pnl_stat': self._calculate_pnl_stats(holdings=short_holdings, use_log_returns=use_log_returns),
        }
        return long_short_pnl

    def lead_lag(self, ll_limit_left=-20, ll_limit_right=60,
                ll_sub_windows=[
                    (date(1980, 1, 1), date(1989, 12, 31)),
                    (date(1990, 1, 1), date(1999, 12, 31)),
                    (date(2000, 1, 1), date(2009, 12, 31)),
                    (date(2010, 1, 1), date(2019, 12, 31)),
                    (date(2020, 1, 1), date(2029, 12, 31)),
                ]):
        leadlag_result = []
        data = {i: self._calculate_sharpe(self._lagged_portfolio_pnl(shift=i), tenors=False).loc['sharpe']
                for i in range(ll_limit_left, ll_limit_right+1)}
        leadlag_result.append(pd.Series(data, name='fullsample'))

        for (start, end) in ll_sub_windows:
            data = {i: self._calculate_sharpe(self._lagged_portfolio_pnl(shift=i)[start:end], tenors=False).loc['sharpe']
                    for i in range(ll_limit_left, ll_limit_right+1)}
            leadlag_result.append(pd.Series(data, name='{0}:{1}'.format(start.strftime('%Y-%b-%d'), end.strftime('%Y-%b-%d'))))
        leadlag_stats = {
            'leadlag_sharpes': pd.DataFrame(leadlag_result),
        }
        return leadlag_stats

    # lagged/smoothed stats
    def lagged_pnl(self, use_log_returns=False, lags=[1,2,5,10,20], shift_func=None):
        lagged_pnl = pd.DataFrame(index=self.date_range, columns=lags, dtype = float)

        if shift_func is None:
            lagged_pnl = lagged_pnl.apply(lambda x: self._lagged_portfolio_pnl(shift=x.name), axis=0)
            lagged_sharpe = self._calculate_sharpe(lagged_pnl)
        else:
            func = shift_func.get('func', None)
            if func is None:
                raise ValueError('"func" must be present in the shift_func parameter')
            else:
                params = shift_func.get('params', {})
                shifted_holdings = func(self.holdings, **params)
                lagged_pnl = self._calc_pnl(shifted_holdings).sum(axis=1, skipna=True).to_frame(name='total')
                lagged_sharpe = self._calculate_sharpe(lagged_pnl)

        portfolio_pnl_stats = {
            'pnl': lagged_pnl,
            'cumpnl': self._cumpnl(lagged_pnl, use_log_returns=use_log_returns),
            'sharpe': lagged_sharpe,
        }
        return portfolio_pnl_stats

    def smoothed_pnl(self, use_log_returns=False, smooth_hls=[1, 2, 5, 10, 20]):
        smoothed_pnl = pd.DataFrame(index=self.date_range, columns=smooth_hls, dtype=float)
        smoothed_pnl = smoothed_pnl.apply(lambda x: self._smoothed_portfolio_pnl(hl=x.name), axis=0)
        smoothed_sharpes = self._calculate_sharpe(smoothed_pnl)
        portfolio_pnl_stats = {
            'pnl': smoothed_pnl,
            'cumpnl': self._cumpnl(smoothed_pnl, use_log_returns=use_log_returns),
            'sharpe': smoothed_sharpes,
        }
        return portfolio_pnl_stats

    def tilt_timing(self, tilt_rolling_window = 3 * tstool.PNL_BDAYS, use_log_returns = False):
        holdings_tilt = self.holdings.rolling(window=tilt_rolling_window, min_periods = 1).mean()
        holdings_timing = self.holdings.subtract(holdings_tilt)

        avg_holdings = self.holdings.mean(axis=0, skipna=True)
        holdings_tilt_full_sample = pd.DataFrame(data=[avg_holdings.values] * len(self.holdings.index), 
                                                 index=self.holdings.index, columns=avg_holdings.index)
        holdings_timing_full_sample = self.holdings - holdings_tilt_full_sample
        tilt_timing_stats = {
            'holdings_tilt': holdings_tilt,
            'pnl_tilt_stat': self._calculate_pnl_stats(holdings_tilt, use_log_returns=use_log_returns),
            'holdings_timing': holdings_timing,
            'pnl_timing_stat': self._calculate_pnl_stats(holdings_timing, use_log_returns=use_log_returns),
            'holdings_tilt_full_sample': holdings_tilt_full_sample,
            'pnl_tilt_stat_full_sample': self._calculate_pnl_stats(holdings_tilt_full_sample, use_log_returns=use_log_returns),
            'holdings_timing_full_sample': holdings_timing_full_sample,
            'pnl_timing_stat_full_sample': self._calculate_pnl_stats(holdings_timing_full_sample, use_log_returns=use_log_returns),
        }

        return tilt_timing_stats

    def seasonl_tilt_timing(self, trailing_seasonal_window_years = 5, use_log_returns = False):
        import math
        sdate = self.holdings.index[0]
        edate = self.holdings.index[-1]
        all_days = pd.date_range(start=sdate, end=edate)
        mask_leap = (all_days.month == 2) & (all_days.day == 29)
        all_days_no_leap = all_days[~mask_leap]
        index_adjustments = np.asarray([365 * i for i in range(1, int(math.floor(len(all_days_no_leap) / 365.0)))])

        holdings_tilt = self.holdings.rolling(window = trailing_seasonal_window_years * tstool.PNL_BDAYS, min_periods=1).mean()
        holdings_nontilt = self.holdings - holdings_tilt
        holdings_nontilt = holdings_nontilt.reindex(all_days_no_leap, method = 'ffill')
        holdings_nontilt = tstool.filldown(holdings_nontilt, maxfill = 2)

        holdings_seasonal = pd.DataFrame(index=all_days_no_leap, columns = self.universe)
        for t in range(365 * trailing_seasonal_window_years, len(all_days_no_leap)):
            curr_indicies = t - index_adjustments[0:trailing_seasonal_window_years]
            holdings_seasonal.iloc[t] = holdings_nontilt.iloc[curr_indicies].mean(skipna = True)
        
        holdings_timing = holdings_nontilt - holdings_seasonal

        avg_holdings = self.holdings.mean(axis=0, skipna = True)
        holdings_tilt_full_sample = pd.DataFrame(data = [avg_holdings.values] * len(self.holdings.index),
                                                index = self.holdings.index, columns = avg_holdings.index)
        holdings_nontilt_full_sample = self.holdings - holdings_tilt_full_sample
        holdings_nontilt_full_sample = holdings_nontilt_full_sample.reindex(all_days_no_leap, method = 'ffill')
        holdings_nontilt_full_sample = tstool.filldown(holdings_nontilt_full_sample, maxfill=2)

        holdings_seasonal_full_sample = pd.DataFrame(index = all_days_no_leap, columns = self.universe)
        for t in range(0, 365):
            curr_indicies = t + index_adjustments
            curr_indicies = curr_indicies[curr_indicies < len(all_days_no_leap)]
            curr_means = holdings_nontilt_full_sample.iloc[curr_indicies].mean(skipna = True)
            curr_mean_rp = [curr_means.values] * len(curr_indicies)
            holdings_seasonal_full_sample.iloc[curr_indicies] = curr_mean_rp

        holdings_timing_full_sample = holdings_nontilt_full_sample - holdings_seasonal_full_sample

        tilt_timing_seasonal_stats = {
            'holdings_tilt': holdings_tilt,
            'pnl_tilt_stat': self._calculate_pnl_stats(holdings_tilt, use_log_returns=use_log_returns),
            'holdings_seasonal': holdings_seasonal,
            'pnl_seasonal_stat': self._calculate_pnl_stats(holdings_seasonal, use_log_returns=use_log_returns),
            'holdings_timing': holdings_timing,
            'pnl_timing_stat': self._calculate_pnl_stats(holdings_timing, use_log_returns=use_log_returns),

            'holdings_title_full_sample': holdings_tilt_full_sample,
            'pnl_tilt_stat_full_sample': self._calculate_pnl_stats(holdings_tilt_full_sample, use_log_returns=use_log_returns),
            'holdings_seasonal_full_sample': holdings_seasonal_full_sample,
            'pnl_seasonal_stat_full_sample': self._calculate_pnl_stats(holdings_seasonal_full_sample, use_log_returns=use_log_returns),
            'holdings_timing_full_sample': holdings_timing_full_sample,
            'pnl_timing_stat_full_sample': self._calculate_pnl_stats(holdings_timing_full_sample, use_log_returns=use_log_returns),
        }
        return tilt_timing_seasonal_stats

    def turnover(self):
        trades = tstool.diff(self.holdings, skipna = True)

        turnover_perc_y = (
            tstool.calendar_aggregation(trades.abs(), how = 'sum', period = 'annual') /
            tstool.calendar_aggregation(self.holdings.abs(), how = 'mean', period = 'annual'))
        
        turnover_portfolio_perc_y = (
            tstool.calendar_aggregation(trades.abs().sum(axis=1), how = 'sum', period = 'annual') /
            tstool.calendar_aggregation(self.holdings.abs().sum(axis=1), how = 'mean', period = 'annual')
        )

        avg_annual_turnover = turnover_portfolio_perc_y.mean(axis=0)

        holdings_lag1 = tstool.lag(self.holdings, lag = 1)
        sign_change = (self.holdings * holdings_lag1) < 0

        change_counts_monthly = tstool.calendar_aggregation(sign_change, how = 'sum', period = 'monthly')
        change_counts_annual = tstool.calendar_aggregation(sign_change, how = 'sum', period = 'annual')

        turnover_stats = {
            'turnover_perc_y': turnover_perc_y,
            'turnover_portfolio_perc_y': turnover_portfolio_perc_y,
            'avg_annual_turnover': avg_annual_turnover,
            'change_counts_monthly': change_counts_monthly,
            'change_counts_annual': change_counts_annual,
        }

        return turnover_stats

    def directional_xs(self, use_log_returns = False):
        net_position = self.holdings.sum(axis=1, skipna = True)
        mask_valid = ~(np.isnan(self.holdings.values) | (self.holdings.values == 0))
        valid_position_counts = np.sum(mask_valid, axis=1)

        directional_values_rp = np.tile(np.reshape(net_position.values / valid_position_counts, [len(self.date_range), 1]), 
                                        [1, len(self.universe)])
        directional_values_rp[~mask_valid] = np.NaN

        holdings_directional = pd.DataFrame(data = directional_values_rp, index = self.date_range, columns = self.universe)
        pnlstats_directional = self._calculate_pnl_stats(holdings= holdings_directional, use_log_returns=use_log_returns)

        holdings_xs = self.holdings - holdings_directional
        pnlstats_xs = self._calculate_pnl_stats(holdings=holdings_xs, use_log_returns=use_log_returns)

        directional_xs_stats = {
            'holdings_directional': holdings_directional,
            'pnlstats_directional': pnlstats_directional,
            'holdings_xs': holdings_xs,
            'pnlstats_xs': pnlstats_xs,
        }

        return directional_xs_stats

    def scaled_holdings(self, rolling_periods=252):
        rolling_std = self.returns.rolling(min_periods=1, window=rolling_periods).std()
        scaled_holding = self.holdings.div(rolling_std)
        return scaled_holding

    def expected_risk(self):
        if getattr(self.portfolio_obj, 'cov_matrices', None) is None:
            raise TypeError('Must pass in a valid cov matrices in order to compute the risk')

        cov_matrices = self.portfolio_obj.cov_matrices.reindex(method = 'ffill', Time = self.date_range)
        portfolio_risk = pd.DataFrame(index = self.date_range, columns = ['risk'], dtype = float)
        for t, t_date in enumerate(self.date_range):
            portfolio_risk.iloc[t] = self.holdings.iloc[t].T.dot(cov_matrices.sel(Time=t_date)).dot(self.holdings.iloc[t])
        
        portfolio_risk = np.sqrt(portfolio_risk)
        upper_risk_limit = self.portfolio_obj.static_constraints['upper_risk_limit']
        lower_risk_limit = self.portfolio_obj.static_constraints['lower_risk_limit']

        if upper_risk_limit is not None:
            portfolio_risk['upper'] = upper_risk_limit
        if lower_risk_limit is not None:
            portfolio_risk['lower'] = lower_risk_limit

        return portfolio_risk
