# -*- coding: utf-8 -*-
import misc
import dbaccess
import data_handler as dh
import datetime
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import statsmodels.formula.api as smf
from pykalman import KalmanFilter
from scipy import poly1d
from stats_test import test_mean_reverting, half_life
from sklearn.linear_model import LinearRegression
from sklearn import metrics
from statsmodels.tsa.stattools import coint, adfuller
import seaborn as sns

def colored_scatter(ts_a, ts_b, ts_c):
    points = plt.scatter(ts_a, ts_b, c = [float((d-ts_c.min()).days) for d in ts_c], s=20, cmap='jet')
    cb = plt.colorbar(points)
    cb.ax.set_yticklabels([str(x) for x in ts_c[::len(ts_c)//7]])
    plt.show()

def get_data(spotID, start, end, spot_table = 'spot_daily', name = None, index_col = 'date', fx_pair = None, field = 'spotID', args = None):
    cnx = dbaccess.connect(**dbaccess.dbconfig)
    if args:
        args['start_date'] = start
        args['end_date'] = end
        df = misc.nearby(spotID, **args)
    else:
        df = dbaccess.load_daily_data_to_df(cnx, spot_table, spotID, start, end, index_col = None, field = field)
    print df
    if isinstance(df[index_col][0], basestring):
        if len(df[index_col][0])> 12:
            df[index_col] = df[index_col].apply(lambda x: datetime.datetime.strptime(x, "%Y-%m-%d %H:%M:%S").date())
        else:
            df[index_col] = df[index_col].apply(lambda x: datetime.datetime.strptime(x, "%Y-%m-%d").date())
    df = df.set_index(index_col)
    if name:
        col_name = name
    else:
        col_name = spotID
    if field == 'ccy':
        df = df[df.tenor=='0W']
        data_field = 'rate'
    elif field == 'spotID':
        data_field = 'close'
    df = df[[data_field]]
    df.rename(columns = {data_field: col_name}, inplace = True)
    if fx_pair:
        fx = dbaccess.load_daily_data_to_df(cnx, 'fx_daily', fx_pair, start, end, index_col = None, field = 'ccy')
        fx = fx[fx['tenor']=='0W']
        if isinstance(fx[index_col][0], basestring):
            fx[index_col] = fx[index_col].apply(lambda x: datetime.datetime.strptime(x, "%Y-%m-%d %H:%M:%S").date())
        fx = fx.set_index(index_col)
        df[col_name] = df[col_name]/fx['rate']
    return df

def merge_df(df_list):
    if len(df_list) == 0:
        return None
    xdf = df_list[0]
    for i in range(1, len(df_list)):
        xdf = xdf.merge(df_list[i], left_index = True, right_index = True, how = 'outer')
        #xdf.rename(columns={ col_name: "x"+str(i)}, inplace=True )
    return xdf


def split_df(df, date_list, split_col = 'date'):
    output = []
    if len(date_list) == 0:
        output.append(df)
        return  output
    if split_col == 'index':
        ts = df.index
    else:
        ts = df[split_col]
    index_list = [ts[0]] + date_list + [ts[-1]]
    for sdate, edate in zip(index_list[:-1], index_list[1:]):
        output.append(df[(ts <= edate) & (ts >= sdate)])
    return output

def get_cont_data(asset, start_date, end_date, freq = '1m', nearby = 1, rollrule = '-10b'):
    cnx = dbaccess.connect(**dbaccess.hist_dbconfig)
    if nearby == 0:
        mdf = dbaccess.load_min_data_to_df(cnx, 'fut_min', asset, start_date, end_date, minid_start = 300, minid_end = 2114, database = 'hist_data')
        mdf['contract'] = asset
    else:
        mdf = misc.nearby(asset, nearby, start_date, end_date, rollrule, 'm', need_shift=True, database = 'hist_data')
    mdf = misc.cleanup_mindata(mdf, asset)
    xdf = dh.conv_ohlc_freq(mdf, freq, extra_cols = ['contract'], bar_func = dh.bar_conv_func2)
    return xdf

def validate_db_data(tday, filter = False):
    all_insts = misc.filter_main_cont(tday, filter)
    data_count = {}
    inst_list = {'min': [], 'daily': [] }
    cnx = dbaccess.connect(**dbaccess.dbconfig)
    for instID in all_insts:
        df = dbaccess.load_daily_data_to_df(cnx, 'fut_daily', instID, tday, tday)
        if len(df) <= 0:
            inst_list['daily'].append(instID)
        elif (df.close[-1] == 0) or (df.high[-1] == 0) or (df.low[-1] == 0) or df.open[-1] == 0:
            inst_list['daily'].append(instID)
        df = dbaccess.load_min_data_to_df(cnx, 'fut_min', instID, tday, tday, minid_start=300, minid_end=2115)
        if len(df) <= 100:
            output = instID + ':' + str(len(df))
            inst_list['min'].append(output)
        elif df.min_id < 2055:
            output = instID + ': end earlier'
            inst_list['min'].append(output)        
    print inst_list

class Regression(object):
    def __init__(self, df, dependent=None, independent=None):
        """
        Initialize the class object
        Pre-condition:
            dependent - column name
            independent - list of column names
        """
        if not dependent:
            dependent = df.columns[1]
        if not independent:
            independent = [df.columns[2], ]

        formula = '{} ~ '.format(dependent)
        first = True
        for element in independent:
            if first:
                formula += element
                first = False
            else:
                formula += ' + {}'.format(element)

        self.df = df
        self.dependent = dependent
        self.independent = independent
        self.result = smf.ols(formula, df).fit()

    def summary(self):
        """
        Return linear regression summary
        """
        return self.result.summary()

    def plot_all(self):
        """
        Plot all dependent and independent variables against time. To visualize
        there relations
        """
        df = self.df
        independent = self.independent
        dependent = self.dependent

        plt.figure(figsize=(10, 5))
        plt.plot(df.index, df[dependent], label=dependent)
        for indep in independent:
            plt.plot(df.index, df[indep], label=indep)
        plt.xticks(rotation='vertical')
        plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
        plt.show()

    def plot2D(self, rotation=False):
        """
        Print scatter plot and the best fit line
        Pre-condition:
            graph must be of 2D
        """
        if len(self.independent) > 1:
            raise ValueError("Not a single independent variable regression")
        params = self.result.params
        df = self.df
        k = params[1]
        b = params[0]
        independent = self.independent[0]
        dependent = self.dependent
        model = k * df[independent] + b

        plt.figure(figsize=(10, 5))
        plt.plot(df[independent], df[dependent], 'o')
        plt.plot(df[independent], model)
        plt.xlabel(independent)
        plt.ylabel(dependent)
        plt.title(dependent + ' vs. ' + independent)
        if rotation:
            plt.xticks(rotation='vertical')
        plt.show()

    def residual(self):
        """
        Return a pandas Series of residual
        Pre-condition:
            There should be no NAN in data. Hence length of date is equal to length
            of data
        """
        df = self.result.resid
        df.index = self.df.index
        return df

    def residual_plot(self, std_line=2, rotation=True):
        """
        Plot the residual against time
        Pre-condition:
            std_line - plot n std band. Set to zero to disable the feature.
        """
        plt.figure(figsize=(10, 5))
        plt.plot(self.df.index, self.result.resid, label='residual')
        if rotation:
            plt.xticks(rotation='vertical')
        plt.title('residual plot')
        if std_line != 0:
            df = self.df
            std = self.residual().describe()['std']
            mean = self.residual().describe()['mean']
            num = len(df.index)
            plt.plot(df.index, std_line * std * np.ones(num) + mean, 'r--')
            plt.plot(df.index, -std_line * std * np.ones(num) + mean, 'r--')
            plt.title('residual plot ({} STD band)'.format(std_line))
        plt.show()

    def residual_vs_fit(self, colorbar=False):
        if colorbar:
            df = self.df
            y_predict = self.result.predict(df[self.independent])
            colored_scatter(y_predict, self.result.resid, df.index)
        else:
            residual = self.residual()
            df = self.df
            y_predict = self.result.predict(df[self.independent])
            plt.plot(y_predict, residual, 'o')
            plt.plot(y_predict, np.zeros(len(residual)), 'r--')
            plt.xlabel("predict")
            plt.ylabel('residual')
            plt.title('Residual vs fit')
            plt.show()

    def cross_validation(self, split_dates, split_col = 'index'):
        if type(self.df.index[0]).__name__ == 'Timestamp' and type(split_dates[0]).__name__ != 'Timestamp':
            split_dates = [pd.to_datetime(idx) for idx in split_dates]
        data_set = split_df(self.df, split_dates, split_col = split_col)
        for idx, train in enumerate(data_set):
            reg_train = Regression(train, self.dependent, self.independent)
            string = []
            for indep in reg_train.independent:
                string.append("%.4f * %s" % (reg_train.result.params[indep], indep))
            print "Train set %s: %s = %s + %.4f\t\nR-sqr: %.2f\tResid std: %.4f" % (idx,
                reg_train.dependent, ' + '.join(string), reg_train.result.params[0],
                reg_train.result.rsquared, reg_train.result.resid.std())
            for idy in range(len(data_set)):
                if idx != idy:
                    test_sum = 0
                    for indep in self.independent:
                        test_sum += data_set[idy][indep] * reg_train.result.params[indep]
                    test_resid = data_set[idy][self.dependent] - test_sum
                    print ("Test set %s: Resid std: %.4f\tResid mean: %.4f" % (idy, test_resid.std(), test_resid.mean(),))

    def run_all(self):
        """
        Lazy ass's ultimate solution. Run all available analysis
        Pre-condition:
            There should be only one independent variable
        """
        _2D = len(self.independent) == 1
        print
        self.plot_all()
        print
        print self.summary()
        if _2D:
            self.plot2D()
        print
        print 'Error statistics'
        print self.residual().describe()
        print
        self.residual_vs_fit()
        self.residual_plot()
        residual = self.residual()
        test_mean_reverting(residual)
        print
        print  'Halflife = ', half_life(residual)

    def summarize_all(self):
        if len(self.independent) == 1:
            dependent = self.dependent
            independent = self.independent[0]
            params = self.result.params
            result = self.result
            k = params[1]
            b = params[0]
            conf = result.conf_int()
            cadf = adfuller(result.resid)
            if cadf[0] <= cadf[4]['5%']:
                boolean = 'likely'
            else:
                boolean = 'unlikely'
            print
            print ("{:^40}".format("{} vs {}".format(dependent.upper(), independent.upper())))
            print ("%20s %s = %.4f * %s + %.4f" % ("Model:", dependent, k, independent, b))
            print ("%20s %.4f" % ("R square:", result.rsquared))
            print ("%20s [%.4f, %.4f]" % ("Confidence interval:", conf.iloc[1, 0], conf.iloc[1, 1]))
            print ("%20s %.4f" % ("Model error:", result.resid.std()))
            print ("%20s %s" % ("Mean reverting:", boolean))
            print ("%20s %d" % ("Half life:", half_life(result.resid)))
        else:
            dependent = self.dependent
            independent = self.independent  # list
            params = self.result.params
            result = self.result
            b = params[0]
            conf = result.conf_int()  # pandas
            cadf = adfuller(result.resid)
            if cadf[0] <= cadf[4]['5%']:
                boolean = 'likely'
            else:
                boolean = 'unlikely'
            print
            print ("{:^40}".format("{} vs {}".format(dependent.upper(), (', '.join(independent)).upper())))
            string = []
            for i in range(len(independent)):
                string.append("%.4f * %s" % (params[independent[i]], independent[i]))
            print ("%20s %s = %s + %.4f" % ("Model:", dependent, ' + '.join(string), b))
            print ("%20s %.4f" % ("R square:", result.rsquared))
            string = []
            for i in range(len(independent)):
                string.append("[%.4f, %.4f]" % (conf.loc[independent[i], 0], conf.loc[independent[i], 1]))
            print ("%20s %s" % ("Confidence interval:", ' , '.join(string)))
            print ("%20s %.4f" % ("Model error:", result.resid.std()))
            print ("%20s %s" % ("Mean reverting:", boolean))
            print ("%20s %d" % ("Half life:", half_life(result.resid)))


class KalmanRegression(object):
    def __init__(self, df, dependent=None, independent=None, delta=None, trans_cov=None, obs_cov=None):
        if not dependent:
            dependent = df.columns[1]
        if not independent:
            independent = df.columns[2]

        self.x = df[independent]
        self.x.index = df.index
        self.y = df[dependent]
        self.y.index = df.index
        self.dependent = dependent
        self.independent = independent

        self.delta = delta or 1e-5
        self.trans_cov = trans_cov or self.delta / (1 - self.delta) * np.eye(2)
        self.obs_mat = np.expand_dims(
            np.vstack([[self.x.values], [np.ones(len(self.x))]]).T,
            axis=1
        )
        self.obs_cov = obs_cov or 1
        self.kf = KalmanFilter(n_dim_obs=1, n_dim_state=2,
                               initial_state_mean=np.zeros(2),
                               initial_state_covariance=np.ones((2, 2)),
                               transition_matrices=np.eye(2),
                               observation_matrices=self.obs_mat,
                               observation_covariance=self.obs_cov,
                               transition_covariance=self.trans_cov)
        self.state_means, self.state_covs = self.kf.filter(self.y.values)

    def slope(self):
        state_means = self.state_means
        return pd.Series(state_means[:, 0], index=self.x.index)

    def plot_params(self):
        state_means = self.state_means
        x = self.x
        _, axarr = plt.subplots(2, sharex=True)
        axarr[0].plot(x.index, state_means[:, 0], label='slope')
        axarr[0].legend()
        axarr[1].plot(x.index, state_means[:, 1], label='intercept')
        axarr[1].legend()
        plt.tight_layout()
        plt.show()
        return state_means[:, 0]

    def plot2D(self):
        x = self.x
        y = self.y
        state_means = self.state_means

        cm = plt.get_cmap('jet')
        colors = np.linspace(0.1, 1, len(x))
        # Plot data points using colormap
        sc = plt.scatter(x, y, s=30, c=colors, cmap=cm, edgecolor='k', alpha=0.7)
        cb = plt.colorbar(sc)
        cb.ax.set_yticklabels([str(p.date()) for p in x[::len(x) // 9].index])

        # Plot every fifth line
        step = 100
        xi = np.linspace(x.min() - 5, x.max() + 5, 2)
        colors_l = np.linspace(0.1, 1, len(state_means[::step]))
        for i, beta in enumerate(state_means[::step]):
            plt.plot(xi, beta[0] * xi + beta[1], alpha=.2, lw=1, c=cm(colors_l[i]))

        # Plot the OLS regression line
        plt.plot(xi, poly1d(np.polyfit(x, y, 1))(xi), '0.4')

        plt.title(self.dependent + ' vs. ' + self.independent)
        plt.show()

    def run_all(self):
        self.plot_params()
        self.plot2D()