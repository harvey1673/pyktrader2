import datetime
import os
import copy
import sys
import json
import pandas as pd
import numpy as np
import data_handler as dh
import trade_position
import dbaccess
import misc
import platform
#import mysql_helper

sim_margin_dict = { 'au': 0.06, 'ag': 0.08, 'cu': 0.07, 'al':0.05,
                'zn': 0.06, 'rb': 0.06, 'ru': 0.12, 'a': 0.05,
                'm':  0.05, 'RM': 0.05, 'y' : 0.05, 'p': 0.05,
                'c':  0.05, 'CF': 0.05, 'i' : 0.05, 'j': 0.05,
                'jm': 0.05, 'pp': 0.05, 'l' : 0.05, 'SR': 0.06,
                'TA': 0.06, 'TC': 0.05, 'ME': 0.06, 'IF': 0.1,
                'jd': 0.06, 'ni': 0.07, 'IC': 0.1,  'ZC': 0.05,
                'IH': 0.01, 'FG': 0.05, 'TF':0.015, 'TS':0.015, 'OI': 0.05,
                'T': 0.015, 'MA': 0.06, 'cs': 0.05, 'bu': 0.07, 
                'sn': 0.05, 'v': 0.05, 'hc': 0.09, 'SM': 0.1,
                'SF': 0.1, 'CY': 0.05, 'AP': 0.05, }
sim_start_dict = { 'c': datetime.date(2008,10,1), 'm': datetime.date(2010,10,1),
    'y': datetime.date(2010,10,1), 'l': datetime.date(2008,10,1), 'rb':datetime.date(2010,10,1),
    'p': datetime.date(2010,10,1), 'cu':datetime.date(2010,10,1), 'al':datetime.date(2010,10,1),
    'zn':datetime.date(2010,10,1), 'au':datetime.date(2010,10,1), 'v': datetime.date(2010,10,1),
    'a': datetime.date(2010,10,1), 'ru':datetime.date(2010,10,1), 'ag':datetime.date(2012,7,1),
    'i': datetime.date(2013,11,26), 'j': datetime.date(2011,6,1), 'jm':datetime.date(2013,5,1),
    'ME':datetime.date(2012,2,1),  'CF':datetime.date(2012,6,1),  'TA':datetime.date(2007,2,1),
    'PM':datetime.date(2012,10,1), 'RM':datetime.date(2013,2,1),  'SR':datetime.date(2006,1,6),
    'FG':datetime.date(2013,2,1),  'OI':datetime.date(2013,6,1),  'RI':datetime.date(2013,6,1),
    'TC':datetime.date(2013,10,1), 'WH':datetime.date(2014,2,1),  'pp':datetime.date(2014,3,1),
    'IF':datetime.date(2010,5,1),  'MA':datetime.date(2015,7,1),  'TF':datetime.date(2014,4,1),
    'IH':datetime.date(2015,5,1),  'IC':datetime.date(2015,5,1),  'cs':datetime.date(2015,2,1),
    'jd':datetime.date(2014,2,1),  'ni':datetime.date(2015,6,1),  'sn':datetime.date(2015,6,1),
    'ZC':datetime.date(2015,12,1), 'hc':datetime.date(2012, 1, 1), 'SM': datetime.date(2016,10,10),
    'SF': datetime.date(2016,10,10), 'CY': datetime.date(2017, 8, 18), 'AP': datetime.date(2017, 12, 22),
    'TS': datetime.date(2018, 8, 17),}

trade_offset_dict = {
                'au': 0.05, 'ag': 1,    'cu': 10,   'al':5,
                'zn': 5,    'rb': 1,    'ru': 5,    'a': 1,
                'm':  1,    'RM': 1,    'y' : 2,    'p': 2,
                'c':  1,    'CF': 5,    'i' : 0.5,  'j': 0.5,
                'jm': 0.5,  'pp': 1,    'l' : 5,    'SR': 1,
                'TA': 2,    'TC': 0.2,  'ME': 1,    'IF': 0.2,
                'jd': 1,    'ni': 10,   'IC': 0.2,  'TS':0.005,
                'IH': 0.2,  'FG': 1,    'TF':0.005, 'OI': 2,
                'T': 0.005, 'MA': 1,    'cs': 1,    'bu': 1,
                'sn': 10,   'v':  5,    'ZC': 0.2,  'hc': 1,
                'SM': 4,    'SF': 4,    'CY': 5,    'AP': 1,
                }


class StratSim(object):
    def __init__(self, config):
        self.pos_update = False
        self.pos_class = None
        self.pos_args = {}
        self.weights = [1]
        self.offset = 0
        self.config = config
        self.process_config(config)
        self.process_data(config['df'])
        self.positions = []
        self.closed_trades = []
        self.tradeid = 0
        self.timestamp = 0
        self.traded_vol = 0.0
        self.traded_cost = 0.0
        self.traded_price = 0.0
        self.closeout_pnl = 0.0
        self.scur_day = None

    def process_config(self, config):
        pass

    def process_data(self, df):
        pass

    def on_bar(self, sim_data, n):
        pass

    def get_tradepos_exit(self, tradepos, sim_data, n):
        return 0

    def run_loop_sim(self):
        dra = dh.DynamicRecArray(dataframe=self.df)
        sim_data = dra.data
        nlen = len(dra)
        self.scur_day = sim_data['date'][0]
        for n in range(1, nlen-1):
            self.timestamp = datetime.datetime.utcfromtimestamp(sim_data['datetime'][n].astype('O')/1e9)
            self.traded_vol = self.traded_cost = self.closeout_pnl = 0
            self.traded_price = sim_data['open'][n]
            sim_data['pos'][n] = sim_data['pos'][n - 1]
            if not self.check_data_invalid(sim_data, n-1):
                if (n >= nlen - 2) or (sim_data['contract'][n]!=sim_data['contract'][n+1]):
                    for tradepos in self.positions:
                        self.close_tradepos(tradepos, sim_data['open'][n])
                    self.positions = []
                else:
                    self.on_bar(sim_data, n - 1)
                    self.check_curr_pos(sim_data, n)
            sim_data['pos'][n] += self.traded_vol
            sim_data['cost'][n] = self.traded_cost
            sim_data['closeout'][n] = self.closeout_pnl
            sim_data['traded_price'][n] = self.traded_price
            if self.scur_day != sim_data['date'][n+1]:
                self.daily_initialize(sim_data, n)
                self.scur_day = sim_data['date'][n + 1]
        #pos = pd.Series(sim_data['pos'], index = self.df.index, name = 'pos')
        #closeout = pd.Series(sim_data['closeout'], index = self.df.index, name = 'closeout')
        #tp = pd.Series(sim_data['traded_price'], index=self.df.index, name='traded_price')
        #cost = pd.Series(sim_data['cost'], index=self.df.index, name='cost')
        #out_df = pd.concat([self.df.open, self.df.high, self.df.low, self.df.close, self.df.date, self.df.min_id, pos, tp, cost, closeout], \
        #                   join='outer', axis = 1)
        out_df = pd.DataFrame(sim_data)
        return out_df, self.closed_trades

    def run_vec_sim(self):
        pass

    def check_data_invalid(self, sim_data, n):
        return False

    def close_tradepos(self, tradepos, price):
        tp = price - self.offset * tradepos.direction
        tradepos.close(tp, self.timestamp)
        tradepos.exit_tradeid = self.tradeid
        self.tradeid += 1
        self.closed_trades.append(tradepos)
        if self.traded_vol * tradepos.pos > 0:
            self.closeout_pnl += tradepos.pos * (tp - self.traded_price)
        else:
            self.traded_price = (self.traded_price * self.traded_vol - tp * tradepos.pos)/(self.traded_vol - tradepos.pos)
        self.traded_vol -= tradepos.pos
        self.traded_cost += abs(tradepos.pos) * (self.offset + tp * self.tcost)
        # print "close", self.timestamp, tp, self.traded_price, self.traded_vol

    def open_tradepos(self, contracts, price, traded_pos):
        tp = price + misc.sign(traded_pos) * self.offset
        new_pos = self.pos_class(insts = contracts, volumes = self.weights, \
                                 pos = self.unit * traded_pos, \
                                 entry_target = tp, exit_target = tp, \
                                 multiple = 1, **self.pos_args)
        new_pos.entry_tradeid = self.tradeid
        self.tradeid += 1
        new_pos.open(tp, self.unit * traded_pos, self.timestamp)
        self.positions.append(new_pos)
        self.traded_price = (self.traded_price * self.traded_vol + tp * new_pos.pos)/(self.traded_vol + new_pos.pos)
        self.traded_vol += new_pos.pos
        self.traded_cost += abs(new_pos.pos) * (self.offset + tp * self.tcost)
        # print "open", self.timestamp, tp, self.traded_price, self.traded_vol

    def check_curr_pos(self, sim_data, n):
        for tradepos in self.positions:
            exit_gap = self.get_tradepos_exit(tradepos, sim_data, n)
            ep =  sim_data['low'][n] if tradepos.pos > 0 else sim_data['high'][n]
            if tradepos.check_exit(ep, exit_gap):
                if tradepos.check_exit(sim_data['open'][n], exit_gap):
                    order_price = sim_data['open'][n]
                else:
                    order_price = tradepos.exit_target - tradepos.direction * exit_gap
                self.close_tradepos(tradepos, order_price)
            elif self.pos_update:
                up = sim_data['low'][n] if tradepos.pos < 0 else sim_data['high'][n]
                tradepos.update_price(up)
        self.positions = [pos for pos in self.positions if not pos.is_closed]

    def daily_initialize(self):
        pass

def stat_min2daily(df):
    return pd.Series([df['pnl'].sum(), df['cost'].sum(), df['margin'][-1]], index = ['pnl','cost','margin'])

def simdf_to_trades1(df, slippage = 0):
    xdf = df[df['pos'] != df['pos'].shift(1)]
    prev_pos = 0
    tradeid = 0
    pos_list = []
    closed_trades = []
    for pos, tprice, cont, dtime in zip(xdf['pos'], xdf['traded_price'],
                                              xdf['contract'], xdf.index):
        if (prev_pos * pos >= 0) and (abs(prev_pos) < abs(pos)):
            if len(pos_list) > 0 and (pos_list[-1].pos * (pos - prev_pos) < 0):
                print "Error: the new trade should be on the same direction of the existing trade cont=%s, prev_pos=%s, pos=%s, time=%s" % (
                cont, prev_pos, pos, dtime)
            new_pos = trade_position.TradePos(insts=[cont], volumes=[1], pos=pos - prev_pos, entry_target=tprice,
                                     exit_target=tprice)
            tradeid += 1
            new_pos.entry_tradeid = tradeid
            new_pos.open(tprice, pos - prev_pos, dtime)
            pos_list.append(new_pos)
        else:
            for i, tp in enumerate(reversed(pos_list)):
                if (prev_pos - tp.pos - pos) * (prev_pos) < 0:
                    break
                else:
                    tp.close(tprice, dtime)
                    prev_pos -= tp.pos
                    tradeid += 1
                    tp.exit_tradeid = tradeid
                    closed_trades.append(tp)
            pos_list = [tp for tp in pos_list if not tp.is_closed]
            if prev_pos != pos:
                if len(pos_list) == 0:
                    new_pos = trade_position.TradePos(insts=[cont], volumes=[1], pos=pos - prev_pos, entry_target=tprice,
                                             exit_target=tprice)
                    tradeid += 1
                    new_pos.entry_tradeid = tradeid
                    new_pos.open(tprice, pos - prev_pos, dtime)
                    pos_list.append(new_pos)
                else:
                    print "Warning: handling partial position for prev_pos=%s, pos=%s, cont=%s, time=%s, should avoid this situation!" % (
                    prev_pos, pos, cont, dtime)
                    partial_tp = copy.deepcopy(pos_list[-1])
                    partial_tp.pos = prev_pos - pos
                    partial_tp.close(tprice, dtime)
                    tradeid += 1
                    partial_tp.exit_tradeid = tradeid
                    closed_trades.append(partial_tp)
                    pos_list[-1].pos -= prev_pos - pos
        prev_pos = pos
    if (len(pos_list) != 0) or (prev_pos != 0):
        print "ERROR: something wrong with the backtest position management - there are unclosed positions after the test"
    return closed_trades


def simdf_to_trades2(df, slippage=0.0):
    xdf = df[df['pos'] != df['pos'].shift(1)]
    prev_pos = 0
    tradeid = 0
    pos_list = []
    closed_trades = []
    for pos, tprice, cont, dtime in zip(xdf['pos'], xdf['traded_price'],
                                              xdf['contract'], xdf.index):
        if (prev_pos * pos >= 0) and (abs(prev_pos) < abs(pos)):
            if len(pos_list) > 0 and (pos_list[-1].pos * (pos - prev_pos) < 0):
                print "Error: the new trade should be on the same direction of the existing trade cont=%s, prev_pos=%s, pos=%s, time=%s" % (
                cont, prev_pos, pos, dtime)
            npos = int(abs(pos - prev_pos))
            new_pos = [trade_position.TradePos(insts=[cont], volumes=[1], pos=misc.sign(pos - prev_pos), entry_target=tprice,
                                      exit_target=tprice) for i in range(npos)]
            for tpos in new_pos:
                tradeid += 1
                tpos.entry_tradeid = tradeid
                tpos.open(tprice, misc.sign(pos - prev_pos), dtime)
            pos_list = pos_list + new_pos
            new_pos = [trade_position.TradePos(insts=[cont], volumes=[1], pos=misc.sign(pos - prev_pos), entry_target=tprice,
                                      exit_target=tprice) for i in range(npos)]
            for tpos in new_pos:
                tradeid += 1
                tpos.entry_tradeid = tradeid
                tpos.open(tprice, misc.sign(pos - prev_pos), dtime)
            pos_list = pos_list + new_pos
        else:
            for i, tp in enumerate(reversed(pos_list)):
                if (prev_pos - tp.pos - pos) * (prev_pos) < 0:
                    break
                else:
                    tp.close(tprice, dtime)
                    prev_pos -= tp.pos
                    tradeid += 1
                    tp.exit_tradeid = tradeid
                    closed_trades.append(tp)
            pos_list = [tp for tp in pos_list if not tp.is_closed]
            if prev_pos != pos:
                if len(pos_list) == 0:
                    npos = int(abs(pos - prev_pos))
                    new_pos = [
                        trade_position.TradePos(insts=[cont], volumes=[1], pos=misc.sign(pos - prev_pos), entry_target=tprice,
                                       exit_target=tprice) for i in range(npos)]
                    for tpos in new_pos:
                        tradeid += 1
                        tpos.entry_tradeid = tradeid
                        tpos.open(tprice, misc.sign(pos - prev_pos), dtime)
                    pos_list = pos_list + new_pos
                else:
                    print "Warning: This should not happen for unit tradepos for prev_pos=%s, pos=%s, cont=%s, time=%s, should avoid this situation!" % (
                    prev_pos, pos, cont, dtime)
        prev_pos = pos
    if (len(pos_list) != 0) or (prev_pos != 0):
        print "ERROR: something wrong with the backtest position management - there are unclosed positions after the test"
    return closed_trades


def check_bktest_bar_stop(bar, stop_price, direction=1):
    price_traded = np.nan
    if (bar.open - stop_price) * direction <= 0:
        price_traded = bar.open
    else:
        if direction > 0:
            compare_price = bar.low
        else:
            compare_price = bar.high
        if (compare_price - stop_price) * direction <= 0:
            price_traded = compare_price
    return price_traded

def pnl_stats(pnl_df):
    res = {}
    res['avg_pnl'] = float(pnl_df['daily_pnl'].mean())
    res['std_pnl'] = float(pnl_df['daily_pnl'].std())
    res['tot_pnl'] = float(pnl_df['daily_pnl'].sum())
    res['tot_cost'] = float(pnl_df['daily_cost'].sum())
    res['num_days'] = len(pnl_df['daily_pnl'])
    if res['std_pnl'] > 0:
        res['sharp_ratio'] = float(res['avg_pnl'] / res['std_pnl'] * np.sqrt(252.0))
        max_dd, max_dur = max_drawdown(pnl_df['cum_pnl'])
        res['max_drawdown'] = float(max_dd)
        res['max_dd_period'] = int(max_dur)
        if abs(max_dd) > 0:
            res['profit_dd_ratio'] = float(res['tot_pnl'] / abs(max_dd))
        else:
            res['profit_dd_ratio'] = 0
    else:
        res['sharp_ratio'] = 0
        res['max_drawdown'] = 0
        res['max_dd_period'] = 0
        res['profit_dd_ratio'] = 0
    return res

def get_pnl_stats(df_list, marginrate, freq, tenors = ['3m', '6m', '1y', '2y', '3y'], start_capital = 10000.0, cost_ratio = 0.0):
    sum_pnl = pd.Series(name='pnl')
    sum_margin = pd.Series(name='margin')
    sum_cost = pd.Series(name='cost')
    if freq == 'm':
        index_col = ['date', 'min_id']
    else:
        index_col = ['date']
    for df in df_list:
        xdf = df.reset_index().set_index(index_col)
        if 'traded_price' in xdf.columns:
            field = 'traded_price'
        else:
            field  = 'close'
        pnl = xdf['pos'].shift(1).fillna(0.0) * (xdf[field] - xdf[field].shift(1)).fillna(0.0) - xdf['cost'] * cost_ratio
        if 'closeout' in xdf.columns:
            pnl = pnl + xdf['closeout']
        # pnl = pnl + (xdf['pos'] - xdf['pos'].shift(1).fillna(0.0)) * (xdf['close'] - xdf['traded_price'])
        if len(sum_pnl) == 0:
            sum_pnl = pd.Series(pnl, name='pnl')
        else:
            sum_pnl = sum_pnl.add(pnl, fill_value=0)
        margin = pd.Series(
            pd.concat([xdf.pos * marginrate[0] * xdf.close, -xdf.pos * marginrate[1] * xdf.close], join='outer',
                      axis=1).max(1), name='margin')
        if len(sum_margin) == 0:
            sum_margin = margin
        else:
            sum_margin = sum_margin.add(margin, fill_value=0)
        if len(sum_cost) == 0:
            if 'cost' in xdf.columns:
                sum_cost = xdf['cost']
            else:
                sum_cost = xdf['close'] * 0.0
        else:
            sum_cost = sum_cost.add(xdf['cost'], fill_value=0)
    if freq == 'm':
        daily_pnl = pd.Series(sum_pnl.groupby(level=0).sum(), name='daily_pnl')
        daily_margin = pd.Series(sum_margin.groupby(level=0).last(), name='daily_margin')
        daily_cost = pd.Series(sum_cost.groupby(level=0).sum(), name='daily_cost')
    else:
        daily_pnl = sum_pnl
        daily_margin = sum_margin
        daily_cost = sum_cost
    daily_pnl.name = 'daily_pnl'
    daily_margin.name = 'daily_margin'
    daily_cost.name = 'daily_cost'
    cum_pnl = pd.Series(daily_pnl.cumsum() + start_capital, name='cum_pnl')
    df = pd.concat([cum_pnl, daily_pnl, daily_margin, daily_cost], join='outer', axis=1)
    res = {}
    for tenor in tenors:
        edate = df.index[-1]
        sdate = misc.day_shift(edate, '-' + tenor)
        pnl_df = df[df.index >= sdate]
        res_by_tenor = pnl_stats(pnl_df)
        for field in res_by_tenor:
            res[field + '_' + tenor] = 0 if np.isnan(res_by_tenor[field]) else res_by_tenor[field]
        if sdate < df.index[0]:
            break
    return res, df

def get_trade_stats(trade_list):
    res = {}
    profits = pd.Series([trade.profit for trade in trade_list])
    wins = profits[profits > 0]
    loss = profits[profits <= 0]
    for ts, prefix in zip([profits, wins, loss], ['trade_', 'win_', 'loss_']):
        desc = ts.describe().to_dict()
        desc['sum'] = ts.sum()
        for field in desc:
            fstr = field.replace('%', 'pct')
            res[prefix + fstr] = 0 if np.isnan(desc[field]) else desc[field]
    res['win_ratio'] = float(len(wins))/float(len(profits)) if len(profits) > 0 else 0.0
    return res

def max_drawdown(ts):
    dd = ts - ts.cummax()
    max_dd = dd.min()
    end = dd.argmin()
    start = ts.loc[:end].argmax()
    max_duration = (start - end).days
    return max_dd, max_duration

def max_drawdown2(ts):
    i = np.argmax(np.maximum.accumulate(ts) - ts)
    j = np.argmax(ts[:i])
    max_dd = ts[i] - ts[j]
    max_duration = (i - j).days
    return max_dd, max_duration

def scen_dict_to_df(data):
    res = pd.DataFrame.from_dict(data, orient='index')
    res.index.name = 'scenario'
    res = res.sort_values(by=['sharp_ratio'], ascending=False)
    res = res.reset_index()
    res.set_index(['asset', 'scenario'])
    return res

class BacktestManager(object):
    def __init__(self, config_file):
        with open(config_file, 'r') as fp:
            sim_config = json.load(fp)
        bktest_split = sim_config['sim_class'].split('.')
        sim_class = __import__('.'.join(bktest_split[:2]))
        for i in range(1, len(bktest_split)):
            sim_class = getattr(sim_class, bktest_split[i])
        self.sim_class = sim_class
        self.sim_func = sim_config['sim_func']
        self.need_shift = sim_config.get('need_shift', True)
        self.sim_freq = sim_config.get('sim_freq', 'm')
        self.sim_name = sim_config['sim_name']
        self.cost_ratio = sim_config.get('cost_ratio', 1.0)
        self.set_bktest_env()
        self.dbtable = sim_config.get('dbtable', 'bktest_output')
        if type(sim_config['products'][0]).__name__ != 'list':
            self.sim_assets = [[str(asset)] for asset in sim_config['products']]
        else:
            self.sim_assets = sim_config['products']
        self.sim_by_product = sim_config.get('sim_by_product', [{} for asset in self.sim_assets])
        self.sim_offset = sim_config.get('offset', 0)
        self.sim_mode = sim_config.get('sim_mode', 'OR')
        self.calc_coeffs = sim_config.get('calc_coeffs', [1, -1])
        if 'cont_maplist' in sim_config:
            self.cont_maplist = sim_config['cont_maplist']
        else:
            self.cont_maplist = [[0]] * len(self.sim_assets)
        self.sim_period = sim_config.get('sim_period', '-12m')
        self.start_date = datetime.datetime.strptime(sim_config['start_date'], '%Y%m%d').date()
        self.end_date = datetime.datetime.strptime(sim_config['end_date'], '%Y%m%d').date()
        scen_dim = [len(sim_config[s]) for s in sim_config['scen_keys']]
        self.scenarios = [list(s) for s in np.ndindex(tuple(scen_dim))]
        self.scen_keys = sim_config['scen_keys']
        self.scen_param = dict([(key, sim_config[key]) for key in self.scen_keys])
        self.config = {}
        self.config.update(sim_config['config'])
        if 'pos_class' in sim_config:
            self.config['pos_class'] = eval(sim_config['pos_class'])
        if 'proc_func' in sim_config:
            self.config['proc_func'] = eval(sim_config['proc_func'])
        self.trade_offset_dict = sim_config.get('trade_offset_dict', trade_offset_dict)
        self.sim_margin_dict = sim_config.get('sim_margin_dict', sim_margin_dict)
        self.start_capital = self.config['capital']
        self.config['data_freq'] = self.sim_freq
        self.data_store = {}
        self.contlist = {}
        self.exp_dates = {}
        self.pnl_tenors = sim_config.get('pnl_tenors', ['3m', '6m', '1y', '2y', '3y'])

    def set_bktest_env(self):
        system = platform.system()
        if system == 'Linux':
            folder = '/home/harvey/dev/data/'
        elif system == 'Windows':
            folder = 'C:\\dev\\data\\'
        else:
            folder = ''
        file_prefix = folder + self.sim_name + os.path.sep
        if not os.path.exists(file_prefix):
            os.makedirs(file_prefix)
        self.file_prefix = file_prefix + self.sim_name
        self.dbconfig = dbaccess.bktest_dbconfig

    def set_config(self, idx):
        assets = self.sim_assets[idx]
        self.config.update(self.sim_by_product[idx])
        self.config['start_date'] = max([sim_start_dict.get(asset, self.start_date) for asset in assets] + [self.start_date])
        self.config['end_date'] = self.end_date
        self.config['tick_base'] = [self.trade_offset_dict.get(prod, 0.0) for prod in assets]
        self.config['offset'] = [self.sim_offset * tbase for tbase in self.config['tick_base']]
        self.config['marginrate'] = [self.sim_margin_dict.get(prod, 0.0) for prod in assets]
        self.config['nearby'] = []
        self.config['rollrule'] = []
        if self.sim_freq == 'm':
            self.config['exit_min'] = 2057
            self.config['no_trade_set'] = []
        for asset in assets:
            nb = 1
            rr = '-40b'
            if asset in ['cu', 'al', 'zn']:
                nb = 3
                rr = '-1b'
            elif asset in ['IF', 'IH', 'IC']:
                rr = '-2b'
            elif asset in ['au', 'ag']:
                rr = '-25b'
            elif asset in ['TF', 'T']:
                rr = '-20b'
            elif asset in ['ni']:
                rr = '-40b'
            self.config['nearby'].append(nb)
            self.config['rollrule'].append(rr)
        if len(assets) == 1:
            self.config['tick_base'] = self.config['tick_base'][0]
            self.config['offset'] = self.config['offset'][0]
            self.config['marginrate'] = (self.config['marginrate'][0], self.config['marginrate'][0])
            self.config['nearby'] = self.config['nearby'][0]
            self.config['rollrule'] = self.config['rollrule'][0]

    def load_curr_results(self, idx):
        asset = self.sim_assets[idx]
        file_prefix = self.file_prefix + '_' + '_'.join([self.sim_mode] + asset)
        fname = file_prefix + '_stats.json'
        output = {}
        if os.path.isfile(fname):
            with open(fname, 'r') as fp:
                output = json.load(fp)
        return output

    def load_data(self, idx):
        asset = self.sim_assets[idx]
        for prod in asset:
            df = misc.nearby(prod, self.config['nearby'], self.config['start_date'], self.config['end_date'],
                          self.config['rollrule'], self.sim_freq, need_shift = self.need_shift)
            if self.sim_freq == 'm':
                df = misc.cleanup_mindata(df, prod)
            self.data_store[prod] = df
        #if self.config['need_daily']:
        #    self.config['ddf'] = misc.nearby(asset, self.config['nearby'], self.config['start_date'], self.config['end_date'],
        #                                 self.config['rollrule'], 'd', need_shift=True, database='hist_data')
        #else:
        #    self.config['ddf'] = None

    def prepare_data(self, asset_idx, cont_idx = 0):
        asset = self.sim_assets[asset_idx]
        self.config['df'] = self.data_store[asset[0]]
        self.config['assets'] = asset

    def run_all_assets(self):
        for idx, asset in enumerate(self.sim_assets):
            output = self.load_curr_results(idx)
            if len(output.keys()) == len(self.scenarios):
                continue
            self.set_config(idx)
            self.load_data(idx)
            for ix, s in enumerate(self.scenarios):
                if str(ix) in output:
                    continue
                res = {'asset': '_'.join(asset), 'scen_id': ix,\
                       'sim_name': self.sim_name, 'sim_class': self.sim_class.__name__, 'sim_func': self.sim_func,
                       'end_date': str(self.config['end_date'])}
                for i in range(5):
                    res['par_name' + str(i)] = ''
                    res['par_value' + str(i)] = 0
                for i, (key, seq) in enumerate(zip(self.scen_keys, s)):
                    self.config[key] = self.scen_param[key][seq]
                    res['par_name' + str(i)] = key
                    res['par_value' + str(i)] = str(self.scen_param[key][seq])
                self.prepare_data(idx, cont_idx = 0)
                sim_strat = self.sim_class(self.config)
                sim_dfs, closed_trades = getattr(sim_strat, self.sim_func)()
                (res_pnl, ts) = get_pnl_stats( sim_dfs, self.config['marginrate'], self.sim_freq, self.pnl_tenors, cost_ratio = self.cost_ratio)
                res_trade = get_trade_stats(closed_trades)
                res.update(dict( res_pnl.items() + res_trade.items()))
                file_prefix = self.file_prefix + '_' + '_'.join([self.sim_mode] + asset)
                res['trade_file'] = file_prefix + '_'+ str(ix) + '_trades.csv'
                res['pnl_file'] = file_prefix + '_'+ str(ix) + '_dailydata.csv'
                output[str(ix)] = res
                all_trades = {}
                for i, tradepos in enumerate(closed_trades):
                    all_trades[i] = trade_position.tradepos2dict(tradepos)
                trades = pd.DataFrame.from_dict(all_trades).T
                trades.to_csv(res['trade_file'])
                ts.to_csv(res['pnl_file'])
                fname = file_prefix + '_stats.json'
                with open(fname, 'w') as ofile:
                    json.dump(output, ofile)
                cnx = dbaccess.connect(**self.dbconfig)
                #cnx.set_converter_class(mysql_helper.NumpyMySQLConverter)
                dbaccess.insert_row_by_dict(cnx, self.dbtable, res, is_replace=True)
                cnx.close()
                print 'The results for asset = %s, scen = %s are saved' % (asset, str(ix))

class SpdBktestManager(BacktestManager):
    def __init__(self, config_file):
        super(SpdBktestManager, self).__init__(config_file)

    def load_data(self, idx):
        asset = self.sim_assets[idx]
        for prod in asset:
            if prod in self.data_store:
                continue
            ticker = prod
            if '$' not in ticker:
                ticker_sp = [ticker, 'spot']
            else:
                ticker_sp = ticker.split('$')
            ticker = ticker_sp[0]
            postfix = '_daily'
            if self.sim_freq == 'm':
                postfix = '_min'
            dbtable = ticker_sp[-1] + postfix
            if ticker_sp[-1] in ['spot']:
                field_id = 'spotID'
            elif ticker_sp[-1] in ['ccy']:
                field_id = 'instID'
            if len(ticker_sp) > 2:
                nb = int(ticker_sp[1])
                if len(ticker_sp) > 3:
                    rollrule = ticker_sp[2]
                else:
                    rollrule = '-1b'
                df = misc.nearby(ticker, nb, self.config['start_date'], self.config['end_date'], rollrule,
                            self.sim_freq, need_shift = self.need_shift,
                            database = self.config.get('dbconfig', dbaccess.dbconfig)['database'])
            else:
                cnx = dbaccess.connect(**self.config.get('dbconfig', dbaccess.dbconfig))
                if self.sim_freq == 'd':
                    df = dbaccess.load_daily_data_to_df(cnx, dbtable, ticker,
                            self.config['start_date'], self.config['end_date'], index_col='date',
                            field = field_id)
                else:
                    minid_start = 1500
                    minid_end = 2114
                    if ticker in misc.night_session_markets:
                        minid_start = 300
                    df = dbaccess.load_min_data_to_df(cnx, dbtable, ticker, self.config['start_date'],
                                                      self.config['end_date'], minid_start, minid_end)
                df['contract'] = ticker
            if self.sim_freq == 'm':
                df = misc.cleanup_mindata(df, ticker)
            df.columns = [(prod, col) for col in df.columns]
            self.data_store[prod] = df

    def prepare_data(self, asset_idx, cont_idx = 0):
        assets = self.sim_assets[asset_idx]
        df = pd.concat([self.data_store[prod] for prod in assets], axis = 1).fillna(method = 'ffill').dropna()
        df['contract'] = df[(assets[0], 'contract')]
        df.index.names = ['date']
        for asset in assets[1:]:
            df['contract'] = df['contract'] + '_' + df[(asset, 'contract')]
        self.config['df'] = df
        self.config['assets'] = assets


class ContBktestManager(BacktestManager):
    def __init__(self, config_file):
        super(ContBktestManager, self).__init__(config_file)

    def load_data(self, assets):
        contlist = {}
        exp_dates = {}
        dbconfig = self.config.get('dbconfig', dbaccess.hist_dbconfig)
        cnx = dbaccess.connect(**dbconfig)
        for i, prod in enumerate(assets):
            cont_mth, exch = dbaccess.prod_main_cont_exch(prod)
            self.contlist[prod], _ = misc.contract_range(prod, exch, cont_mth, self.start_date, self.end_date)
            self.exp_dates[prod] = [misc.contract_expiry(cont) for cont in contlist[prod]]
            edates = [ misc.day_shift(d, self.config['rollrule']) for d in exp_dates[prod] ]
            sdates = [ misc.day_shift(d, self.sim_period) for d in exp_dates[prod] ]
            self.data_store[prod] = {}
            for cont, sd, ed in zip(contlist[prod], sdates, edates):
                if self.sim_freq == 'd':
                    tmp_df = dbaccess.load_daily_data_to_df(cnx, 'fut_min', cont, sd, ed)
                else:
                    minid_start = 1500
                    minid_end = 2114
                    if prod in misc.night_session_markets:
                        minid_start = 300
                    tmp_df = dbaccess.load_min_data_to_df(cnx, 'fut_min', cont, sd, ed, minid_start, minid_end)
                    misc.cleanup_mindata(tmp_df, prod)
                tmp_df['contract'] = cont
                self.data_store[prod][cont] = tmp_df
                cnx.close()

    def prepare_data(self, asset_idx, cont_idx = 0):
        assets = self.sim_assets[asset_idx]
        cont_map = self.cont_maplist[asset_idx]
        cont = self.contlist[assets[0]][cont_idx]
        edate = misc.day_shift(self.exp_dates[assets[0]][cont_idx], self.config['rollrule'])
        if self.sim_mode == 'OR':
            df = self.data_store[assets[0]][cont]
            df = df[df.date <= edate]
        else:
            mode_keylist = self.sim_mode.split('-')
            smode = mode_keylist[0]
            cmode = mode_keylist[1]
            all_data = []
            if smode == 'TS':
                all_data = [self.data_store[assets[0]][self.contlist[assets[0]][cont_idx+i]] for i in cont_map]
            else:
                all_data = [self.data_store[asset][self.contlist[asset][cont_idx+i]] for asset, i in zip(assets, cont_map)]
            if cmode == 'Full':
                df = pd.concat(all_data, axis = 1, join = 'inner')
                df.columns = [iter + str(i) for i, x in enumerate(all_data) for iter in x.columns]
                df = df[ df.date0 < edate]
            else:
                for i, (coeff, tmpdf) in enumerate(zip(self.calc_coeffs, all_data)):
                    if i == 0:
                        xopen = tmpdf['open'] * coeff
                        xclose = tmpdf['close'] * coeff
                    else:
                        xopen = xopen + tmpdf['open'] * coeff
                        xclose = xclose + tmpdf['close'] * coeff
                xopen = xopen.dropna()
                xclose = xclose.dropna()
                xhigh = pd.concat([xopen, xclose], axis = 1).max(axis = 1)
                xlow = pd.concat([xopen, xclose], axis = 1).min(axis = 1)
                col_list = ['date', 'min_id', 'volume', 'openInterest']
                df = pd.concat([ xopen, xhigh, xlow, xclose] + [all_data[0][col] for col in col_list], axis = 1, join = 'inner')
                df.columns = ['open', 'high', 'low', 'close'] + col_list
                df['contract'] = cont
        self.config['df'] = df

    def run_all_assets(self):
        for idx, asset in enumerate(self.sim_assets):
            cont_map = self.cont_maplist[idx]
            output = self.load_curr_results(idx)
            if len(output) == 0:
                output = {'total': {}, 'cont': {}}
            elif len(output.keys()) == len(self.scenarios):
                continue
            self.set_config(idx)
            self.load_data(idx)
            for ix, s in enumerate(self.scenarios):
                file_prefix = self.file_prefix + '_' + '_'.join(self.sim_mode + asset)
                fname1 = file_prefix + str(ix) + '_trades.csv'
                fname2 = file_prefix + str(ix) + '_dailydata.csv'
                if os.path.isfile(fname1) and os.path.isfile(fname2):
                    continue
                for key, seq in zip(self.scen_keys, s):
                    self.config[key] = self.scen_param[key][seq]
                df_list = []
                trade_list = []
                for idy in range(abs(min(cont_map)), len(self.contlist[asset[0]]) - max(cont_map)):
                    cont = self.contlist[asset[0]][idy]
                    self.prepare_data(idx, cont_idx = idy)
                    sim_strat = self.sim_class(self.config)
                    sim_df, closed_trades = getattr(sim_strat, self.sim_func)()
                    df_list.append(sim_df)
                    trade_list = trade_list + closed_trades
                    (res_pnl, ts) = get_pnl_stats( [sim_df], self.config['marginrate'], 'm', cost_ratio = self.cost_ratio)
                    res_trade = get_trade_stats(closed_trades)
                    res =  dict( res_pnl.items() + res_trade.items())
                    res.update(dict(zip(self.scen_keys, s)))
                    res['asset'] = cont
                    if cont not in output['cont']:
                        output['cont'][cont] = {}
                    output['cont'][cont][ix] = res
                (res_pnl, ts) = get_pnl_stats(df_list, self.config['marginrate'], 'm', cost_ratio = self.cost_ratio)
                output[ix] = res
                res_trade = get_trade_stats(trade_list)
                res = dict(res_pnl.items() + res_trade.items())
                res.update(dict(zip(self.scen_keys, s)))
                res['asset'] = '_'.join(asset)
                output['total'][ix] = res
                print 'saving results for asset = %s, scen = %s' % (asset, str(ix))
                all_trades = {}
                for i, tradepos in enumerate(trade_list):
                    all_trades[i] = trade_position.tradepos2dict(tradepos)
                trades = pd.DataFrame.from_dict(all_trades).T
                trades.to_csv(fname1)
                ts.to_csv(fname2)
                fname = file_prefix + '_stats.json'
                with open(fname, 'w') as ofile:
                    json.dump(output, ofile)
            cont_df = pd.DataFrame()
            for idy in range(abs(min(cont_map)), len(self.contlist[asset[0]]) - max(cont_map)):
                cont = self.contlist[asset[0]][idy]
                if cont not in output['cont']:
                    continue
                res = scen_dict_to_df(output['cont'][cont])
                out_res = res[self.output_columns()]
                if len(cont_df) == 0:
                    cont_df = out_res[:30].copy(deep=True)
                else:
                    cont_df = cont_df.append(out_res[:30])
            fname = file_prefix + 'cont_stat.csv'
            cont_df.to_csv(fname)
            res = scen_dict_to_df(output['total'])
            out_res = res[self.output_columns()]
            if len(summary_df)==0:
                summary_df = out_res[:30].copy(deep = True)
            else:
                summary_df = summary_df.append(out_res[:30])
            fname = self.file_prefix + 'summary.csv'
            summary_df.to_csv(fname)

if __name__=="__main__":
    args = sys.argv[1:]
    if len(args) < 2:
        print "need to input a sim func and a file name for simulation"
    else:
        mode = int(args[0])
        if mode == 0:
            bktest_sim = BacktestManager(args[1])
            bktest_sim.run_all_assets()
        elif mode == 1:
            bktest_sim = ContBktestManager(args[1])
            bktest_sim.run_all_assets()
        elif mode == 2:
            bktest_sim = SpdBktestManager(args[1])
            bktest_sim.run_all_assets()

