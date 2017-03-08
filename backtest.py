import datetime
import os
import copy
import sys
import json
import pandas as pd
import numpy as np
import data_handler as dh
import strategy as strat
import mysqlaccess
import misc
import platform

sim_margin_dict = { 'au': 0.06, 'ag': 0.08, 'cu': 0.07, 'al':0.05,
                'zn': 0.06, 'rb': 0.06, 'ru': 0.12, 'a': 0.05,
                'm':  0.05, 'RM': 0.05, 'y' : 0.05, 'p': 0.05,
                'c':  0.05, 'CF': 0.05, 'i' : 0.05, 'j': 0.05,
                'jm': 0.05, 'pp': 0.05, 'l' : 0.05, 'SR': 0.06,
                'TA': 0.06, 'TC': 0.05, 'ME': 0.06, 'IF': 0.1,
                'jd': 0.06, 'ni': 0.07, 'IC': 0.1,  'ZC': 0.05,
                'IH': 0.01, 'FG': 0.05, 'TF':0.015, 'OI': 0.05,
                'T': 0.015, 'MA': 0.06, 'cs': 0.05, 'bu': 0.07, 
                'sn': 0.05, 'v': 0.05, 'hc': 0.09 }
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
    'ZC':datetime.date(2015,12,1), 'hc':datetime.date(2012, 1, 1),
    }

trade_offset_dict = {
                'au': 0.05, 'ag': 1,    'cu': 10,   'al':5,
                'zn': 5,    'rb': 1,    'ru': 5,    'a': 1,
                'm':  1,    'RM': 1,    'y' : 2,    'p': 2,
                'c':  1,    'CF': 5,    'i' : 0.5,  'j': 0.5,
                'jm': 0.5,  'pp': 1,    'l' : 5,    'SR': 1,
                'TA': 2,    'TC': 0.2,  'ME': 1,    'IF': 0.2,
                'jd': 1,    'ni': 10,   'IC': 0.2,
                'IH': 0.2,  'FG': 1,    'TF':0.005, 'OI': 2,
                'T': 0.005, 'MA': 1,    'cs': 1,    'bu': 1,
                'sn': 10,   'v':  5,    'ZC': 0.2,  'hc': 1,
                }

def get_bktest_folder():
    folder = ''
    system = platform.system()
    if system == 'Linux':
        folder = '/home/harvey/dev/data/'
    elif system == 'Windows':
        folder = 'C:\\dev\\data\\'
    return folder

class StratSim(object):
    def __init__(self, config):
        self.pos_update = False
        self.pos_class = None
        self.pos_args = {}
        self.weights = [1]
        self.offset = 0
        self.config = config
        self.process_config(config)
        self.process_data(config['mdf'])
        self.positions = []
        self.closed_trades = []
        self.tradeid = 0
        self.timestamp = 0
        self.traded_vol = 0
        self.traded_cost = 0
        self.traded_price = 0.0
        self.scur_day = None

    def process_config(self, config):
        pass

    def process_data(self, mdf):
        pass

    def on_bar(self, sim_data, n):
        pass

    def get_tradepos_exit(self, sim_data, n):
        return 0

    def run_loop_sim(self):
        dra = dh.DynamicRecArray(dataframe=self.df)
        sim_data = dra.data
        nlen = len(dra)
        for n in range(1, nlen-1):
            self.timestamp = datetime.datetime.utcfromtimestamp(sim_data['datetime'][n].astype('O')/1e9)
            sim_data['pos'][n] = sim_data['pos'][n - 1]
            if self.check_data_invalid(sim_data, n):
                continue
            if self.scur_day != sim_data['date'][n]:
                self.scur_day = sim_data['date'][n]
                self.daily_initialize(sim_data, n)
            exit_gap = self.get_tradepos_exit(sim_data, n)
            self.check_curr_pos([sim_data['open'][n], sim_data['high'][n], sim_data['low'][n], sim_data['close'][n]], exit_gap)
            sim_data['pos'][n] += self.traded_vol
            sim_data['cost'][n] = self.traded_cost
            sim_data['traded_price'][n] = self.traded_price
            self.traded_vol = self.traded_cost = 0
            self.traded_price = sim_data['close'][n]
            self.on_bar(sim_data, n)
        pos = pd.Series(sim_data['pos'], index = self.df.index, name = 'pos')
        tp = pd.Series(sim_data['traded_price'], index=self.df.index, name='traded_price')
        cost = pd.Series(sim_data['cost'], index=self.df.index, name='cost')
        out_df = pd.concat([self.df.open, self.df.high, self.df.low, self.df.close, self.df.date, self.df.min_id, pos, tp, cost], \
                           join='outer', axis = 1)
        return out_df, self.closed_trades

    def run_vec_sim(self):
        pass

    def check_data_invalid(self, sim_data, n):
        return False

    def close_tradepos(self, tradepos, traded_price):
        tradepos.close(traded_price - self.offset * tradepos.direction, self.timestamp)
        tradepos.exit_tradeid = self.tradeid
        self.tradeid += 1
        self.closed_trades.append(tradepos)
        self.traded_price = (self.traded_price * self.traded_vol - traded_price * tradepos.pos)/(self.traded_vol - tradepos.pos)
        self.traded_vol -= tradepos.pos
        self.traded_cost += abs(tradepos.pos) * (self.offset + traded_price * self.tcost)

    def open_tradepos(self, contracts, price, traded_pos):
        traded_price = price + misc.sign(traded_pos) * self.offset
        new_pos = self.pos_class(contracts, self.weights, self.unit * traded_pos, traded_price, traded_price, multiple = 1, **self.pos_args)
        new_pos.entry_tradeid = self.tradeid
        self.tradeid += 1
        new_pos.open(traded_price, self.unit * traded_pos, self.timestamp)
        self.positions.append(new_pos)
        self.traded_price = (self.traded_price * self.traded_vol + traded_price * new_pos.pos)/(self.traded_vol + new_pos.pos)
        self.traded_vol += new_pos.pos
        self.traded_cost += abs(new_pos.pos) * (self.offset + price * self.tcost)

    def check_curr_pos(self, ohlc, exit_gap = 0):
        pos = cost = 0
        for tradepos in self.positions:
            ep =  ohlc[2] if tradepos.pos > 0 else ohlc[1]
            if tradepos.check_exit(ep, exit_gap):
                if tradepos.check_exit(ohlc[0], exit_gap):
                    traded_price = ohlc[0]
                else:
                    tp = (tradepos.exit_target - tradepos.direction * exit_gap)/self.offset
                    traded_price = int(tp) * self.offset if tp > 0 else (int(tp)-1) * self.offset
                self.close_tradepos(tradepos, traded_price)
            elif self.pos_update:
                tradepos.update_price(ep)
        self.positions = [pos for pos in self.positions if not pos.is_closed]

    def daily_initialize(self):
        pass

def get_asset_tradehrs(asset):
    exch = 'SHFE'
    for ex in misc.product_code:
        if asset in misc.product_code[ex]:
            exch = ex
            break
    hrs = [(1500, 1615), (1630, 1730), (1930, 2100)]
    if exch in ['SSE', 'SZE']:
        hrs = [(1530, 1730), (1900, 2100)]
    elif asset in ['TF', 'IF']:
        hrs = [(1515, 1730), (1900, 2115)]
    else:
        if asset in misc.night_session_markets:
            night_idx = misc.night_session_markets[asset]
            hrs = [misc.night_trading_hrs[night_idx]] + hrs
    return hrs
    
def cleanup_mindata(df, asset, index_col = 'datetime'):
    cond = None
    if index_col == None:
        xdf = df.set_index('datetime')
    else:
        xdf = df
    tradehrs = get_asset_tradehrs(asset)
    for idx, hrs in enumerate(tradehrs):
        if idx == 0:
            cond = (xdf.min_id>= tradehrs[idx][0]) & (xdf.min_id < tradehrs[idx][1])
        else:
            cond = cond | (xdf.min_id>= tradehrs[idx][0]) & (xdf.min_id < tradehrs[idx][1])
    if asset in ['a', 'b', 'p', 'y', 'm', 'i', 'j', 'jm']:
        cond = cond | ((xdf.index < datetime.datetime(2015, 5, 12, 15, 0, 0)) & (xdf.min_id>=300) & (xdf.min_id<830))
    if asset in ['rb', 'hc', 'bu']:
        cond = cond | ((xdf.index < datetime.datetime(2016, 5, 1, 15, 0, 0)) & (xdf.min_id>=300) & (xdf.min_id < 700))
    if asset in ['IF', 'IH', 'IC']:
        cond = cond | ((xdf.index < datetime.datetime(2016, 1, 1, 15, 0, 0)) & (xdf.min_id>=1515) & (xdf.min_id < 1530))
        cond = cond | ((xdf.index < datetime.datetime(2016, 1, 1, 15, 0, 0)) & (xdf.min_id>=2100) & (xdf.min_id < 2115))
    xdf = xdf.ix[cond]
    xdf = xdf[(xdf.close > 0) & (xdf.high > 0) & (xdf.open > 0) & (xdf.low > 0)]
    if index_col == None:
        xdf = xdf.reset_index()
    return xdf

def stat_min2daily(df):
    return pd.Series([df['pnl'].sum(), df['cost'].sum(), df['margin'][-1]], index = ['pnl','cost','margin'])

def simdf_to_trades1(df, slippage = 0):
    xdf = df[df['pos'] != df['pos'].shift(1)]
    prev_pos = 0
    tradeid = 0
    pos_list = []
    closed_trades = []
    for o, c, pos, tprice, cont, dtime in zip(xdf['open'], xdf['close'], xdf['pos'], xdf['traded_price'], xdf['contract'], xdf.index):
        if (prev_pos * pos >=0) and (abs(prev_pos)<abs(pos)):
            if len(pos_list)>0 and (pos_list[-1].pos*(pos - prev_pos) < 0):
                print "Error: the new trade should be on the same direction of the existing trade cont=%s, prev_pos=%s, pos=%s, time=%s" % (cont, prev_pos, pos, dtime)
            new_pos = strat.TradePos([cont], [1], pos - prev_pos, tprice, tprice)
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
            pos_list = [ tp for tp in pos_list if not tp.is_closed ]
            if prev_pos != pos:
                if len(pos_list) == 0:
                    new_pos = strat.TradePos([cont], [1], pos - prev_pos, tprice, tprice)
                    tradeid += 1
                    new_pos.entry_tradeid = tradeid
                    new_pos.open(tprice, pos - prev_pos, dtime)
                    pos_list.append(new_pos)
                else:  
                    print "Warning: handling partial position for prev_pos=%s, pos=%s, cont=%s, time=%s, should avoid this situation!" % (prev_pos, pos, cont, dtime) 
                    partial_tp = copy.deepcopy(pos_list[-1])
                    partial_tp.pos = prev_pos - pos
                    partial_tp.close(tprice, dtime)
                    tradeid += 1
                    partial_tp.exit_tradeid = tradeid
                    closed_trades.append(partial_tp)
                    pos_list[-1].pos -= prev_pos - pos
        prev_pos = pos
    if (len(pos_list) !=0) or (prev_pos!=0):
        print "ERROR: something wrong with the backtest position management - there are unclosed positions after the test"
    return closed_trades

def simdf_to_trades2(df, slippage = 0.0):
    xdf = df[df['pos'] != df['pos'].shift(1)]
    prev_pos = 0
    tradeid = 0
    pos_list = []
    closed_trades = []
    for o, c, pos, tprice, cont, dtime in zip(xdf['open'], xdf['close'], xdf['pos'], xdf['traded_price'], xdf['contract'], xdf.index):
        if (prev_pos * pos >=0) and (abs(prev_pos)<abs(pos)):
            if len(pos_list)>0 and (pos_list[-1].pos*(pos - prev_pos) < 0):
                print "Error: the new trade should be on the same direction of the existing trade cont=%s, prev_pos=%s, pos=%s, time=%s" % (cont, prev_pos, pos, dtime)            
            npos = int(abs(pos-prev_pos))
            new_pos = [ strat.TradePos([cont], [1], misc.sign(pos-prev_pos), tprice, tprice) for i in range(npos)]
            for tpos in new_pos:
                tradeid += 1
                tpos.entry_tradeid = tradeid
                tpos.open(tprice + misc.sign(pos - prev_pos)*slippage, misc.sign(pos-prev_pos), dtime)
            pos_list = pos_list + new_pos
            new_pos = [ strat.TradePos([cont], [1], misc.sign(pos-prev_pos), tprice, tprice) for i in range(npos)]
            for tpos in new_pos:
                tradeid += 1
                tpos.entry_tradeid = tradeid
                tpos.open(tprice + misc.sign(pos - prev_pos)*slippage, misc.sign(pos-prev_pos), dtime)
            pos_list = pos_list + new_pos
        else:
            for i, tp in enumerate(reversed(pos_list)):
                if (prev_pos - tp.pos - pos) * (prev_pos) < 0:                    
                    break
                else:
                    tp.close(tprice - misc.sign(tp.pos)*slippage, dtime)
                    prev_pos -= tp.pos
                    tradeid += 1
                    tp.exit_tradeid = tradeid
                    closed_trades.append(tp)
            pos_list = [ tp for tp in pos_list if not tp.is_closed ]
            if prev_pos != pos:
                if len(pos_list) == 0:
                    npos = int(abs(pos-prev_pos))
                    new_pos = [ strat.TradePos([cont], [1], misc.sign(pos-prev_pos), tprice, tprice) for i in range(npos)]
                    for tpos in new_pos:
                        tradeid += 1
                        tpos.entry_tradeid = tradeid
                        tpos.open(tprice + misc.sign(pos - prev_pos)*slippage, misc.sign(pos-prev_pos), dtime)
                    pos_list = pos_list + new_pos                    
                else:  
                    print "Warning: This should not happen for unit tradepos for prev_pos=%s, pos=%s, cont=%s, time=%s, should avoid this situation!" % (prev_pos, pos, cont, dtime) 
        prev_pos = pos
    if (len(pos_list) !=0) or (prev_pos!=0):
        print "ERROR: something wrong with the backtest position management - there are unclosed positions after the test"
    return closed_trades
    
def check_bktest_bar_stop(bar, stop_price, direction = 1):
    price_traded = np.nan
    if (bar.open - stop_price)*direction <= 0:
        price_traded = bar.open
    else:
        if direction > 0:
            compare_price = bar.low
        else:
            compare_price = bar.high
        if (compare_price - stop_price)*direction <= 0:
            price_traded = compare_price
    return price_traded
    
def get_pnl_stats(df_list, start_capital, marginrate, freq):
    sum_pnl = pd.Series(name = 'pnl')
    sum_margin = pd.Series(name='margin')
    sum_cost = pd.Series(name='cost')
    if freq == 'm':
        index_col = ['date', 'min_id']
    else:
        index_col = ['date']
    for df in df_list:
        xdf = df.reset_index().set_index(index_col)
        pnl = xdf['pos'].shift(1).fillna(0.0)*(xdf['close'] - xdf['close'].shift(1)).fillna(0.0)
        if 'traded_price' in xdf.columns:
            pnl = pnl + (xdf['pos'] - xdf['pos'].shift(1).fillna(0.0))*(xdf['close'] - xdf['traded_price'])
        if len(sum_pnl) == 0:
            sum_pnl = pd.Series(pnl, name = 'pnl')
        else:
            sum_pnl = sum_pnl.add(pnl, fill_value = 0)
        margin = pd.Series(pd.concat([xdf.pos*marginrate[0]*xdf.close, -xdf.pos*marginrate[1]*xdf.close], join='outer', axis=1).max(1), name='margin')
        if len(sum_margin) == 0:
            sum_margin = margin
        else:
            sum_margin = sum_margin.add( margin, fill_value = 0)
        if len(sum_cost) == 0:
            sum_cost = xdf['cost']
        else:
            sum_cost = sum_cost.add(xdf['cost'], fill_value = 0)
    if freq == 'm':
        daily_pnl = pd.Series(sum_pnl.groupby(level=0).sum(), name = 'daily_pnl')
        daily_margin = pd.Series(sum_margin.groupby(level=0).last(), name = 'daily_margin')
        daily_cost = pd.Series(sum_cost.groupby(level=0).sum(), name = 'daily_cost')
    else:
        daily_pnl = sum_pnl
        daily_margin = sum_margin
        daily_cost = sum_cost
    daily_pnl.name = 'daily_pnl'
    daily_margin.name = 'daily_margin'
    daily_cost.name = 'daily_cost'
    cum_pnl = pd.Series(daily_pnl.cumsum() + daily_cost.cumsum() + start_capital, name = 'cum_pnl')
    available = cum_pnl - daily_margin
    res = {}
    res['avg_pnl'] = float(daily_pnl.mean())
    res['std_pnl'] = float(daily_pnl.std())
    res['tot_pnl'] = float(daily_pnl.sum())
    res['tot_cost'] = float(daily_cost.sum())
    res['num_days'] = len(daily_pnl)
    res['max_margin'] = float(daily_margin.max())
    res['min_avail'] = float(available.min())
    if res['std_pnl'] > 0:
        res['sharp_ratio'] = float(res['avg_pnl']/res['std_pnl']*np.sqrt(252.0))
        max_dd, max_dur = max_drawdown(cum_pnl)
        res['max_drawdown'] =  float(max_dd)
        res['max_dd_period'] =  int(max_dur)
        if abs(max_dd) > 0:
            res['profit_dd_ratio'] = float(res['tot_pnl']/abs(max_dd))
        else:
            res['profit_dd_ratio'] = 0
    else:
        res['sharp_ratio'] = 0
        res['max_drawdown'] = 0
        res['max_dd_period'] = 0
        res['profit_dd_ratio'] = 0
    ts = pd.concat([cum_pnl, daily_margin, daily_cost], join='outer', axis=1)
    return res, ts

def get_trade_stats(trade_list):
    res = {}
    res['n_trades'] = len(trade_list)
    res['all_profit'] = float(sum([trade.profit for trade in trade_list]))
    res['win_profit'] = float(sum([trade.profit for trade in trade_list if trade.profit>0]))
    res['loss_profit'] = float(sum([trade.profit for trade in trade_list if trade.profit<0]))
    sorted_profit = sorted([trade.profit for trade in trade_list])
    if len(sorted_profit)>5:
        res['largest_profit'] = float(sorted_profit[-1])
    else:
        res['largest_profit'] = 0
    if len(sorted_profit)>4:
        res['second largest'] = float(sorted_profit[-2])
    else:
        res['second largest'] = 0
    if len(sorted_profit) > 3:
        res['third_profit'] = float(sorted_profit[-3])
    else:
        res['third_profit'] = 0
    if len(sorted_profit) > 0:
        res['largest_loss'] = float(sorted_profit[0])
    else:
        res['largest_loss'] = 0
    if len(sorted_profit) > 1:
        res['second_loss'] = float(sorted_profit[1])
    else:
        res['second_loss'] = 0
    if len(sorted_profit) > 2:
        res['third_loss'] = float(sorted_profit[2])
    else:
        res['third_loss'] = 0
    res['num_win'] = len([trade.profit for trade in trade_list if trade.profit>0])
    res['num_loss'] = len([trade.profit for trade in trade_list if trade.profit<0])
    res['win_ratio'] = 0
    if res['n_trades'] > 0:
        res['win_ratio'] = float(res['num_win'])/float(res['n_trades'])
    res['profit_per_win'] = 0
    if res['num_win'] > 0:
        res['profit_per_win'] = float(res['win_profit']/float(res['num_win']))
    res['profit_per_loss'] = 0
    if res['num_loss'] > 0:    
        res['profit_per_loss'] = float(res['loss_profit']/float(res['num_loss']))
    return res

def create_drawdowns(ts):
    """
    Calculate the largest peak-to-trough drawdown of the PnL curve
    as well as the duration of the drawdown. Requires that the 
    pnl_returns is a pandas Series.
    Parameters:
    pnl - A pandas Series representing period percentage returns.
    Returns:
    drawdown, duration - Highest peak-to-trough drawdown and duration.
    """

    # Calculate the cumulative returns curve 
    # and set up the High Water Mark
    # Then create the drawdown and duration series
    ts_idx = ts.index
    drawdown = pd.Series(index = ts_idx)
    duration = pd.Series(index = ts_idx)
    hwm = pd.Series([0]*len(ts), index = ts_idx)
    last_t = ts_idx[0]
    # Loop over the index range
    for idx, t in enumerate(ts_idx):
        if idx > 0:
            cur_hwm = max(hwm[last_t], ts_idx[idx])
            hwm[t] = cur_hwm
            drawdown[t]= hwm[t] - ts[t]
            duration[t]= 0 if drawdown[t] == 0 else duration[last_t] + 1
        last_t = t
    return drawdown.max(), duration.max()

def max_drawdown(ts):
    i = np.argmax(np.maximum.accumulate(ts)-ts)
    j = np.argmax(ts[:i])
    max_dd = ts[i] - ts[j]
    max_duration = (i - j).days
    return max_dd, max_duration

def simnearby_min(config_file):
    sim_config = {}
    with open(config_file, 'r') as fp:
        sim_config = json.load(fp)
    bktest_split = sim_config['sim_func'].split('.')
    run_sim = __import__('.'.join(bktest_split[:-1]))
    for i in range(1, len(bktest_split)):
        run_sim = getattr(run_sim, bktest_split[i])
    dir_name = config_file.split('.')[0]
    dir_name = dir_name.split(os.path.sep)[-1]
    test_folder = get_bktest_folder()
    file_prefix = test_folder + dir_name + os.path.sep
    if not os.path.exists(file_prefix):
        os.makedirs(file_prefix)
    sim_list = sim_config['products']
    need_daily = sim_config.get('need_daily', False)
    config = {}
    start_date = datetime.datetime.strptime(sim_config['start_date'], '%Y%m%d').date()
    config['start_date'] = start_date
    end_date   = datetime.datetime.strptime(sim_config['end_date'], '%Y%m%d').date()
    config['end_date'] = end_date
    scen_dim = [ len(sim_config[s]) for s in sim_config['scen_keys']]
    outcol_list = ['asset', 'scenario'] + sim_config['scen_keys'] \
                + ['sharp_ratio', 'tot_pnl', 'std_pnl', 'num_days', \
                    'max_drawdown', 'max_dd_period', 'profit_dd_ratio', \
                    'all_profit', 'tot_cost', 'win_ratio', 'num_win', 'num_loss', \
                    'profit_per_win', 'profit_per_loss']
    scenarios = [list(s) for s in np.ndindex(tuple(scen_dim))]
    config.update(sim_config['config'])
    if 'pos_class' in sim_config:
        config['pos_class'] = eval(sim_config['pos_class'])
    if 'proc_func' in sim_config:
        config['proc_func'] = eval(sim_config['proc_func'])
    file_prefix = file_prefix + sim_config['sim_name']
    if 'close_daily' in config and config['close_daily']:
        file_prefix = file_prefix + 'daily_'
    config['file_prefix'] = file_prefix
    summary_df = pd.DataFrame()
    fname = config['file_prefix'] + 'summary.csv'
    if os.path.isfile(fname):
        summary_df = pd.DataFrame.from_csv(fname)
    for asset in sim_list:
        file_prefix = config['file_prefix'] + '_' + asset + '_'
        fname = file_prefix + 'stats.json'
        output = {}
        if os.path.isfile(fname):
            with open(fname, 'r') as fp:
                output = json.load(fp)
        if len(output.keys()) < len(scenarios):
            if asset in sim_start_dict:
                start_date =  max(sim_start_dict[asset], config['start_date'])
            else:
                start_date = config['start_date']
            config['tick_base'] = trade_offset_dict[asset]
            if 'offset' in sim_config:
                config['offset'] = sim_config['offset'] * trade_offset_dict[asset]
            else:
                config['offset'] = trade_offset_dict[asset]
            config['marginrate'] = ( sim_margin_dict[asset], sim_margin_dict[asset])
            config['nearby'] = 1
            config['rollrule'] = config.get('rollrule', '-50b')
            config['exit_min'] = config.get('exit_min', 2057)
            config['no_trade_set'] = config.get('no_trade_set', range(300, 301) + range(1500, 1501) + range(2059, 2100))
            if asset in ['cu', 'al', 'zn']:
                config['nearby'] = 3
                config['rollrule'] = '-1b'
            elif asset in ['IF', 'IH', 'IC']:
                config['rollrule'] = '-2b'
                config['no_trade_set'] = range(1515, 1520) + range(2110, 2115)
            elif asset in ['au', 'ag']:
                config['rollrule'] = '-25b'
            elif asset in ['TF', 'T']:
                config['rollrule'] = '-20b'
                config['no_trade_set'] = range(1515, 1520) + range(2110, 2115)
            config['no_trade_set'] = []
            nearby   = config['nearby']
            rollrule = config['rollrule']
            if nearby > 0:
                mdf = misc.nearby(asset, nearby, start_date, end_date, rollrule, 'm', need_shift=True, database = 'hist_data')
            mdf = cleanup_mindata(mdf, asset)
            if need_daily:
                ddf = misc.nearby(asset, nearby, start_date, end_date, rollrule, 'd', need_shift=True, database = 'hist_data')
                config['ddf'] = ddf
            for ix, s in enumerate(scenarios):
                fname1 = file_prefix + str(ix) + '_trades.csv'
                fname2 = file_prefix + str(ix) + '_dailydata.csv'
                if os.path.isfile(fname1) and os.path.isfile(fname2):
                    continue
                for key, seq in zip(sim_config['scen_keys'], s):
                    config[key] = sim_config[key][seq]
                df = mdf.copy(deep = True)
                df, closed_trades = run_sim( df, config)
                (res_pnl, ts) = get_pnl_stats( [df], config['capital'], config['marginrate'], 'm')
                res_trade = get_trade_stats( closed_trades )
                res = dict( res_pnl.items() + res_trade.items())
                res.update(dict(zip(sim_config['scen_keys'], s)))
                res['asset'] = asset
                output[ix] = res
                print 'saving results for asset = %s, scen = %s' % (asset, str(ix))
                all_trades = {}
                for i, tradepos in enumerate(closed_trades):
                    all_trades[i] = strat.tradepos2dict(tradepos)
                trades = pd.DataFrame.from_dict(all_trades).T
                trades.to_csv(fname1)
                ts.to_csv(fname2)
                fname = file_prefix + 'stats.json'
                with open(fname, 'w') as ofile:
                    json.dump(output, ofile)
        res = pd.DataFrame.from_dict(output, orient = 'index')
        res.index.name = 'scenario'
        res = res.sort_values(by = ['sharp_ratio'], ascending=False)
        res = res.reset_index()
        res.set_index(['asset', 'scenario'])
        out_res = res[outcol_list]
        if len(summary_df) == 0:
            summary_df = out_res[:30].copy(deep = True)
        else:
            summary_df = summary_df.append(out_res[:30])
        fname = config['file_prefix'] + 'summary.csv'
        summary_df.to_csv(fname)
    return

def simcontract_min(config_file):
    sim_config = {}
    with open(config_file, 'r') as fp:
        sim_config = json.load(fp)
    bktest_split = sim_config['sim_func'].split('.')
    run_sim = __import__('.'.join(bktest_split[:-1]))
    for i in range(1, len(bktest_split)):
        run_sim = getattr(run_sim, bktest_split[i])
    dir_name = config_file.split('.')[0]
    dir_name = dir_name.split(os.path.sep)[-1]
    test_folder = get_bktest_folder()
    file_prefix = test_folder + dir_name + os.path.sep
    if not os.path.exists(file_prefix):
        os.makedirs(file_prefix)
    sim_list = sim_config['products']
    if type(sim_list[0]).__name__ != 'list':
        sim_list = [[str(asset)] for asset in sim_list]
    sim_mode = sim_config.get('sim_mode', 'OR')
    calc_coeffs = sim_config.get('calc_coeffs', [1, -1])
    cont_maplist = sim_config.get('cont_maplist', [])
    sim_period = sim_config.get('sim_period', '-12m')
    need_daily = sim_config.get('need_daily', False)
    if len(cont_maplist) == 0:
        cont_maplist = [[0]] * len(sim_list)
    config = {}
    start_date = datetime.datetime.strptime(sim_config['start_date'], '%Y%m%d').date()
    config['start_date'] = start_date
    end_date   = datetime.datetime.strptime(sim_config['end_date'], '%Y%m%d').date()
    config['end_date'] = end_date
    scen_dim = [ len(sim_config[s]) for s in sim_config['scen_keys']]
    outcol_list = ['asset', 'scenario'] + sim_config['scen_keys'] \
                + ['sharp_ratio', 'tot_pnl', 'std_pnl', 'num_days', \
                    'max_drawdown', 'max_dd_period', 'profit_dd_ratio', \
                    'all_profit', 'tot_cost', 'win_ratio', 'num_win', 'num_loss', \
                    'profit_per_win', 'profit_per_loss']
    scenarios = [list(s) for s in np.ndindex(tuple(scen_dim))]
    config.update(sim_config['config'])
    if 'pos_class' in sim_config:
        config['pos_class'] = eval(sim_config['pos_class'])
    if 'proc_func' in sim_config:
        config['proc_func'] = eval(sim_config['proc_func'])
    file_prefix = file_prefix + sim_config['sim_name']
    if 'close_daily' in config and config['close_daily']:
        file_prefix = file_prefix + 'daily_'
    config['file_prefix'] = file_prefix
    summary_df = pd.DataFrame()
    fname = config['file_prefix'] + 'summary.csv'
    if os.path.isfile(fname):
        summary_df = pd.DataFrame.from_csv(fname)
    for assets, cont_map in zip(sim_list, cont_maplist):
        file_prefix = config['file_prefix'] + '_' + sim_mode + '_' + '_'.join(assets) + '_'
        fname = file_prefix + 'stats.json'
        output = {'total': {}, 'cont': {}}
        if os.path.isfile(fname):
            with open(fname, 'r') as fp:
                output = json.load(fp)
        #if len(output['total'].keys()) == len(scenarios):
        #    continue
        min_data = {}
        day_data = {}
        config['tick_base'] = 0
        config['marginrate'] = (0, 0)
        rollrule = '-50b'
        config['exit_min'] = config.get('exit_min', 2057)
        config['no_trade_set'] = config.get('no_trade_set', [])
        if assets[0] in ['cu', 'al', 'zn']:
            rollrule = '-1b'
        elif assets[0] in ['IF', 'IH', 'IC']:
            rollrule = '-2b'
        elif assets[0] in ['au', 'ag']:
            rollrule = '-25b'
        elif assets[0] in ['TF', 'T']:
            rollrule = '-20b'
        rollrule = config.get('rollrule', rollrule)
        contlist = {}
        exp_dates = {}
        for i, prod in enumerate(assets):
            cont_mth, exch = mysqlaccess.prod_main_cont_exch(prod)
            contlist[prod] = misc.contract_range(prod, exch, cont_mth, start_date, end_date)
            exp_dates[prod] = [misc.contract_expiry(cont) for cont in contlist[prod]]
            edates = [ misc.day_shift(d, rollrule) for d in exp_dates[prod] ]
            sdates = [ misc.day_shift(d, sim_period) for d in exp_dates[prod] ]
            config['tick_base'] += trade_offset_dict[prod]
            config['marginrate'] = ( max(config['marginrate'][0], sim_margin_dict[prod]), max(config['marginrate'][1], sim_margin_dict[prod]))
            min_data[prod] = {}
            day_data[prod] = {}
            for cont, sd, ed in zip(contlist[prod], sdates, edates):
                minid_start = 1500
                minid_end = 2114
                if prod in misc.night_session_markets:
                    minid_start = 300
                tmp_df = mysqlaccess.load_min_data_to_df('fut_min', cont, sd, ed, minid_start, minid_end, database = 'hist_data')
                tmp_df['contract'] = cont
                min_data[prod][cont] = cleanup_mindata( tmp_df, prod)
                if need_daily:
                    tmp_df = mysqlaccess.load_daily_data_to_df('fut_daily', cont, sd, ed, database = 'hist_data')
                    day_data[prod][cont] = tmp_df
        if 'offset' in sim_config:
            config['offset'] = sim_config['offset'] * config['tick_base']
        else:
            config['offset'] = config['tick_base']
        for ix, s in enumerate(scenarios):
            fname1 = file_prefix + str(ix) + '_trades.csv'
            fname2 = file_prefix + str(ix) + '_dailydata.csv'
            if os.path.isfile(fname1) and os.path.isfile(fname2):
                continue
            for key, seq in zip(sim_config['scen_keys'], s):
                config[key] = sim_config[key][seq]
            df_list = []
            trade_list = []
            for idx in range(abs(min(cont_map)), len(contlist[assets[0]]) - max(cont_map)):
                cont = contlist[assets[0]][idx]
                edate = misc.day_shift(exp_dates[assets[0]][idx], rollrule)
                if sim_mode == 'OR':
                    mdf = min_data[assets[0]][cont]
                    mdf = mdf[mdf.date <= edate]
                    if need_daily:
                        ddf = day_data[assets[0]][cont]
                        config['ddf'] = ddf[ddf.index <= edate]
                        if len(config['ddf']) < 10:
                            continue
                else:
                    mode_keylist = sim_mode.split('-')
                    smode = mode_keylist[0]
                    cmode = mode_keylist[1]
                    all_data = []
                    if smode == 'TS':
                        all_data = [min_data[assets[0]][contlist[assets[0]][idx+i]] for i in cont_map]
                    else:
                        all_data = [min_data[asset][contlist[asset][idx+i]] for asset, i in zip(assets, cont_map)]
                    if cmode == 'Full':
                        mdf = pd.concat(all_data, axis = 1, join = 'inner')
                        mdf.columns = [iter + str(i) for i, x in enumerate(all_data) for iter in x.columns]
                        mdf = mdf[ mdf.date0 < edate]
                    else:
                        #print all_data[0], all_data[1]
                        for i, (coeff, tmpdf) in enumerate(zip(calc_coeffs, all_data)):
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
                        mdf = pd.concat([ xopen, xhigh, xlow, xclose] + [all_data[0][col] for col in col_list], axis = 1, join = 'inner')
                        mdf.columns = ['open', 'high', 'low', 'close'] + col_list
                        mdf['contract'] = cont
                        #print mdf
                    if need_daily:
                        if smode == 'TS':
                            all_data = [day_data[assets[0]][contlist[assets[0]][idx+i]] for i in cont_map]
                        else:
                            all_data = [day_data[asset][contlist[asset]][idx+i] for asset, i in zip(assets, cont_map)]
                        if cmode == 'Full':
                            ddf = pd.concat(all_data, axis = 1, join = 'inner')
                            ddf.columns = [iter + str(i) for i, x in enumerate(all_data) for iter in x.columns]
                            config['ddf'] = ddf[ddf.index <= edate]
                        else:
                            for i, (coeff, tmpdf) in enumerate(zip(calc_coeffs, all_data)):
                                if i == 0:
                                    xopen = tmpdf['open'] * coeff
                                    xclose = tmpdf['close'] * coeff
                                else:
                                    xopen = xopen + tmpdf['open'] * coeff
                                    xclose = xclose + tmpdf['close'] * coeff
                            xhigh = pd.concat([xopen, xclose], axis = 1).max(axis = 1)
                            xlow = pd.concat([xopen, xclose], axis = 1).min(axis = 1)
                            col_list = ['volume', 'openInterest']
                            ddf = pd.concat([ xopen, xhigh, xlow, xclose] + [all_data[0][col] for col in col_list], axis = 1, join = 'inner')
                            ddf.columns = ['open', 'high', 'low', 'close'] + col_list
                            ddf['contract'] = cont
                            config['ddf'] = ddf[ddf.index <= edate]
                        if len(config['ddf']) < 10:
                            continue
                df = mdf.copy(deep = True)
                df, closed_trades = run_sim( df, config)
                df_list.append(df)
                trade_list = trade_list + closed_trades
                (res_pnl, ts) = get_pnl_stats( [df], config['capital'], config['marginrate'], 'm')
                res_trade = get_trade_stats( trade_list )
                res = dict( res_pnl.items() + res_trade.items())
                res.update(dict(zip(sim_config['scen_keys'], s)))
                res['asset'] = cont
                if cont not in output['cont']:
                    output['cont'][cont] = {}
                output['cont'][cont][ix] = res
            (res_pnl, ts) = get_pnl_stats( df_list, config['capital'], config['marginrate'], 'm')
            res_trade = get_trade_stats( trade_list )
            res = dict( res_pnl.items() + res_trade.items())
            res.update(dict(zip(sim_config['scen_keys'], s)))
            res['asset'] = '_'.join(assets)
            output['total'][ix] = res
            print 'saving results for asset = %s, scen = %s' % ('_'.join(assets), str(ix))
            all_trades = {}
            for i, tradepos in enumerate(trade_list):
                all_trades[i] = strat.tradepos2dict(tradepos)
            trades = pd.DataFrame.from_dict(all_trades).T
            trades.to_csv(fname1)
            ts.to_csv(fname2)
            fname = file_prefix + 'stats.json'
            try:
                with open(fname, 'w') as ofile:
                    json.dump(output, ofile)
            except:
                continue
        cont_df = pd.DataFrame()
        for idx in range(abs(min(cont_map)), len(contlist[assets[0]]) - max(cont_map)):
            cont = contlist[assets[0]][idx]
            if cont not in output['cont']:
                continue
            res = scen_dict_to_df(output['cont'][cont])
            out_res = res[outcol_list]
            if len(cont_df) == 0:
                cont_df = out_res[:20].copy(deep = True)
            else:
                cont_df = cont_df.append(out_res[:20])
        fname = file_prefix + 'cont_stat.csv'
        cont_df.to_csv(fname)
        res = scen_dict_to_df(output['total'])
        out_res = res[outcol_list]
        if len(summary_df) == 0:
            summary_df = out_res[:20].copy(deep = True)
        else:
            summary_df = summary_df.append(out_res[:20])
        fname = config['file_prefix'] + 'summary.csv'
        summary_df.to_csv(fname)
    return

def scen_dict_to_df(data):
    res = pd.DataFrame.from_dict(data, orient = 'index')
    res.index.name = 'scenario'
    res = res.sort_values(by = ['sharp_ratio'], ascending=False)
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
        dir_name = config_file.split('.')[0]
        dir_name = dir_name.split(os.path.sep)[-1]
        test_folder = self.get_bktest_folder()
        file_prefix = test_folder + dir_name + os.path.sep
        if not os.path.exists(file_prefix):
            os.makedirs(file_prefix)
        if type(sim_config['products'][0]).__name__ != 'list':
            self.sim_assets = [[str(asset)] for asset in sim_config['products']]
        else:
            self.sim_assets = sim_config['products']
        # self.need_daily = sim_config.get('need_daily', False)
        self.sim_offset = sim_config.get('offset', 0)
        self.sim_mode = sim_config.get('sim_mode', 'OR')
        self.calc_coeffs = sim_config.get('calc_coeffs', [1, -1])
        if 'cont_maplist' in sim_config:
            self.cont_maplist = sim_config['cont_maplist']
        else:
            self.cont_maplist = [[0]] * len(self.sim_assets)
        self.sim_period = sim_config.get('sim_period', '-12m')
        self.config = {}
        self.start_date = datetime.datetime.strptime(sim_config['start_date'], '%Y%m%d').date()
        self.end_date = datetime.datetime.strptime(sim_config['end_date'], '%Y%m%d').date()
        scen_dim = [len(sim_config[s]) for s in sim_config['scen_keys']]
        self.scenarios = [list(s) for s in np.ndindex(tuple(scen_dim))]
        self.scen_keys = sim_config['scen_keys']
        self.scen_param = dict([(key, sim_config[key]) for key in self.scen_keys])
        self.config.update(sim_config['config'])
        if 'pos_class' in sim_config:
            self.config['pos_class'] = eval(sim_config['pos_class'])
        if 'proc_func' in sim_config:
            self.config['proc_func'] = eval(sim_config['proc_func'])
        self.file_prefix = file_prefix + sim_config['sim_name']
        self.start_capital = self.config['capital']
        self.min_data = {}
        self.contlist = {}
        self.exp_dates = {}
        self.restart()

    def get_bktest_folder(self):
        folder = ''
        system = platform.system()
        if system == 'Linux':
            folder = '/home/harvey/dev/data/'
        elif system == 'Windows':
            folder = 'C:\\dev\\data\\'
        return folder

    def output_columns(self):
        return ['asset', 'scenario'] + self.scen_keys + ['sharp_ratio', 'tot_pnl', 'std_pnl', 'num_days', \
                 'max_drawdown', 'max_dd_period', 'profit_dd_ratio', \
                 'all_profit', 'tot_cost', 'win_ratio', 'num_win', 'num_loss', \
                 'profit_per_win', 'profit_per_loss']

    def restart(self):
        self.summary_df = pd.DataFrame()
        fname = self.file_prefix + 'summary.csv'
        if os.path.isfile(fname):
            self.summary_df = pd.DataFrame.from_csv(fname)

    def set_config(self, idx):
        assets = self.sim_assets[idx]
        asset = assets[0]
        if asset in sim_start_dict:
            self.config['start_date'] = max(sim_start_dict[asset], self.start_date)
        else:
            self.config['start_date'] = self.start_date
        self.config['end_date'] = self.end_date
        self.config['tick_base'] = sum([trade_offset_dict[prod] for prod in assets])
        self.config['offset'] = self.sim_offset * self.config['tick_base']
        max_margin = max([sim_margin_dict[prod] for prod in assets])
        self.config['marginrate'] = (max_margin, max_margin)
        self.config['nearby'] = 1
        self.config['rollrule'] = '-50b'
        self.config['exit_min'] = 2057
        self.config['no_trade_set'] = range(300, 301) + range(1500, 1501) + range(2059, 2100) \
                                                if 'no_trade_set' not in self.config else self.config['no_trade_set']
        if asset in ['cu', 'al', 'zn']:
            self.config['nearby'] = 3
            self.config['rollrule'] = '-1b'
        elif asset in ['IF', 'IH', 'IC']:
            self.config['rollrule'] = '-2b'
            self.config['no_trade_set'] = range(1515, 1520) + range(2110, 2115)
        elif asset in ['au', 'ag']:
            self.config['rollrule'] = '-25b'
        elif asset in ['TF', 'T']:
            self.config['rollrule'] = '-20b'
            self.config['no_trade_set'] = range(1515, 1520) + range(2110, 2115)
        self.config['no_trade_set'] = []

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
            mdf = misc.nearby(prod, self.config['nearby'], self.config['start_date'], self.config['end_date'],
                          self.config['rollrule'], 'm', need_shift=True, database='hist_data')
            mdf = cleanup_mindata(mdf, prod)
            self.min_data[prod] = mdf
        #if self.config['need_daily']:
        #    self.config['ddf'] = misc.nearby(asset, self.config['nearby'], self.config['start_date'], self.config['end_date'],
        #                                 self.config['rollrule'], 'd', need_shift=True, database='hist_data')
        #else:
        #    self.config['ddf'] = None

    def prepare_data(self, asset_idx, cont_idx = 0):
        asset = self.sim_assets[asset_idx]
        self.config['mdf'] = self.min_data[asset[0]]

    def get_pnl_stats(self, df_list, marginrate, freq):
        sum_pnl = pd.Series(name='pnl')
        sum_margin = pd.Series(name='margin')
        sum_cost = pd.Series(name='cost')
        if freq == 'm':
            index_col = ['date', 'min_id']
        else:
            index_col = ['date']
        for df in df_list:
            xdf = df.reset_index().set_index(index_col)
            pnl = xdf['pos'].shift(1).fillna(0.0) * (xdf['close'] - xdf['close'].shift(1)).fillna(0.0)
            if 'traded_price' in xdf.columns:
                pnl = pnl + (xdf['pos'] - xdf['pos'].shift(1).fillna(0.0)) * (xdf['close'] - xdf['traded_price'])
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
                sum_cost = xdf['cost']
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
        cum_pnl = pd.Series(daily_pnl.cumsum() + daily_cost.cumsum() + self.start_capital, name='cum_pnl')
        available = cum_pnl - daily_margin
        res = {}
        res['avg_pnl'] = float(daily_pnl.mean())
        res['std_pnl'] = float(daily_pnl.std())
        res['tot_pnl'] = float(daily_pnl.sum())
        res['tot_cost'] = float(daily_cost.sum())
        res['num_days'] = len(daily_pnl)
        res['max_margin'] = float(daily_margin.max())
        res['min_avail'] = float(available.min())
        if res['std_pnl'] > 0:
            res['sharp_ratio'] = float(res['avg_pnl'] / res['std_pnl'] * np.sqrt(252.0))
            max_dd, max_dur = max_drawdown(cum_pnl)
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
        ts = pd.concat([cum_pnl, daily_margin, daily_cost], join='outer', axis=1)
        return res, ts

    def get_trade_stats(self, trade_list):
        res = {}
        res['n_trades'] = len(trade_list)
        res['all_profit'] = float(sum([trade.profit for trade in trade_list]))
        res['win_profit'] = float(sum([trade.profit for trade in trade_list if trade.profit > 0]))
        res['loss_profit'] = float(sum([trade.profit for trade in trade_list if trade.profit < 0]))
        sorted_profit = sorted([trade.profit for trade in trade_list])
        if len(sorted_profit) > 5:
            res['largest_profit'] = float(sorted_profit[-1])
        else:
            res['largest_profit'] = 0
        if len(sorted_profit) > 4:
            res['second largest'] = float(sorted_profit[-2])
        else:
            res['second largest'] = 0
        if len(sorted_profit) > 3:
            res['third_profit'] = float(sorted_profit[-3])
        else:
            res['third_profit'] = 0
        if len(sorted_profit) > 0:
            res['largest_loss'] = float(sorted_profit[0])
        else:
            res['largest_loss'] = 0
        if len(sorted_profit) > 1:
            res['second_loss'] = float(sorted_profit[1])
        else:
            res['second_loss'] = 0
        if len(sorted_profit) > 2:
            res['third_loss'] = float(sorted_profit[2])
        else:
            res['third_loss'] = 0
        res['num_win'] = len([trade.profit for trade in trade_list if trade.profit > 0])
        res['num_loss'] = len([trade.profit for trade in trade_list if trade.profit < 0])
        res['win_ratio'] = 0
        if res['n_trades'] > 0:
            res['win_ratio'] = float(res['num_win']) / float(res['n_trades'])
        res['profit_per_win'] = 0
        if res['num_win'] > 0:
            res['profit_per_win'] = float(res['win_profit'] / float(res['num_win']))
        res['profit_per_loss'] = 0
        if res['num_loss'] > 0:
            res['profit_per_loss'] = float(res['loss_profit'] / float(res['num_loss']))
        return res

    def run_all_assets(self):
        self.restart()
        for idx, asset in enumerate(self.sim_assets):
            output = self.load_curr_results(idx)
            if len(output.keys()) == len(self.scenarios):
                continue
            self.set_config(idx)
            self.load_data(idx)
            for ix, s in enumerate(self.scenarios):
                if ix in output:
                    continue
                file_prefix = self.file_prefix + '_' + '_'.join([self.sim_mode] + asset)
                fname1 = file_prefix + '_'+ str(ix) + '_trades.csv'
                fname2 = file_prefix + '_'+ str(ix) + '_dailydata.csv'
                for key, seq in zip(self.scen_keys, s):
                    self.config[key] = self.scen_param[key][seq]
                self.prepare_data(idx, cont_idx = 0)
                sim_strat = self.sim_class(self.config)
                #sim_strat.process_config()
                # sim_strat.process_data()
                sim_df, closed_trades = getattr(sim_strat, self.sim_func)()
                (res_pnl, ts) = self.get_pnl_stats( [sim_df], self.config['marginrate'], 'm')
                res_trade = self.get_trade_stats(closed_trades)
                res = dict( res_pnl.items() + res_trade.items())
                res.update(dict(zip(self.scen_keys, s)))
                res['asset'] = '_'.join(asset)
                output[ix] = res
                print 'saving results for asset = %s, scen = %s' % (asset, str(ix))
                all_trades = {}
                for i, tradepos in enumerate(closed_trades):
                    all_trades[i] = strat.tradepos2dict(tradepos)
                trades = pd.DataFrame.from_dict(all_trades).T
                trades.to_csv(fname1)
                ts.to_csv(fname2)
                fname = file_prefix + 'stats.json'
                with open(fname, 'w') as ofile:
                    json.dump(output, ofile)
            res = pd.DataFrame.from_dict(output, orient = 'index')
            res.index.name = 'scenario'
            res = res.sort_values(by = ['sharp_ratio'], ascending=False)
            res = res.reset_index()
            res.set_index(['asset', 'scenario'])
            out_res = res[self.output_columns()]
            if len(summary_df):
                summary_df = out_res[:30].copy(deep = True)
            else:
                summary_df = summary_df.append(out_res[:30])
            fname = self.file_prefix + 'summary.csv'
            summary_df.to_csv(fname)

class ContBktestManager(BacktestManager):
    def __init__(self, config_file):
        super(ContBktestManager, self).__init__(config_file)

    def load_data(self, assets):
        contlist = {}
        exp_dates = {}
        for i, prod in enumerate(assets):
            cont_mth, exch = mysqlaccess.prod_main_cont_exch(prod)
            self.contlist[prod] = misc.contract_range(prod, exch, cont_mth, self.start_date, self.end_date)
            self.exp_dates[prod] = [misc.contract_expiry(cont) for cont in contlist[prod]]
            edates = [ misc.day_shift(d, self.config['rollrule']) for d in exp_dates[prod] ]
            sdates = [ misc.day_shift(d, self.sim_period) for d in exp_dates[prod] ]
            self.min_data[prod] = {}
            for cont, sd, ed in zip(contlist[prod], sdates, edates):
                minid_start = 1500
                minid_end = 2114
                if prod in misc.night_session_markets:
                    minid_start = 300
                tmp_df = mysqlaccess.load_min_data_to_df('fut_min', cont, sd, ed, minid_start, minid_end, database = 'hist_data')
                tmp_df['contract'] = cont
                self.min_data[prod][cont] = cleanup_mindata( tmp_df, prod)

    def prepare_data(self, asset_idx, cont_idx = 0):
        assets = self.sim_assets[asset_idx]
        cont_map = self.cont_maplist[asset_idx]
        cont = self.contlist[assets[0]][cont_idx]
        edate = misc.day_shift(self.exp_dates[assets[0]][cont_idx], self.config['rollrule'])
        if self.sim_mode == 'OR':
            mdf = self.min_data[assets[0]][cont]
            mdf = mdf[mdf.date <= edate]
        else:
            mode_keylist = self.sim_mode.split('-')
            smode = mode_keylist[0]
            cmode = mode_keylist[1]
            all_data = []
            if smode == 'TS':
                all_data = [self.min_data[assets[0]][self.contlist[assets[0]][cont_idx+i]] for i in cont_map]
            else:
                all_data = [self.min_data[asset][self.contlist[asset][cont_idx+i]] for asset, i in zip(assets, cont_map)]
            if cmode == 'Full':
                mdf = pd.concat(all_data, axis = 1, join = 'inner')
                mdf.columns = [iter + str(i) for i, x in enumerate(all_data) for iter in x.columns]
                mdf = mdf[ mdf.date0 < edate]
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
                mdf = pd.concat([ xopen, xhigh, xlow, xclose] + [all_data[0][col] for col in col_list], axis = 1, join = 'inner')
                mdf.columns = ['open', 'high', 'low', 'close'] + col_list
                mdf['contract'] = cont
        self.config['mdf'] = mdf

    def run_all_assets(self):
        summary_df = pd.DataFrame()
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
                    sim_df, closed_trades = self.sim_func(self.config)
                    df_list.append(sim_df)
                    trade_list = trade_list + closed_trades
                    (res_pnl, ts) = self.get_pnl_stats( [sim_df], self.config['marginrate'], 'm')
                    res_trade = self.get_trade_stats(closed_trades)
                    res =  dict( res_pnl.items() + res_trade.items())
                    res.update(dict(zip(self.scen_keys, s)))
                    res['asset'] = cont
                    if cont not in output['cont']:
                        output['cont'][cont] = {}
                    output['cont'][cont][ix] = res
                (res_pnl, ts) = self.get_pnl_stats(df_list, self.config['marginrate'], 'm')
                output[ix] = res
                res_trade = self.get_trade_stats(closed_trades)
                res = dict(res_pnl.items() + res_trade.items())
                res.update(dict(zip(self.scen_keys, s)))
                res['asset'] = '_'.join(asset)
                output['total'][ix] = res
                print 'saving results for asset = %s, scen = %s' % (asset, str(ix))
                all_trades = {}
                for i, tradepos in enumerate(closed_trades):
                    all_trades[i] = strat.tradepos2dict(tradepos)
                trades = pd.DataFrame.from_dict(all_trades).T
                trades.to_csv(fname1)
                ts.to_csv(fname2)
                fname = file_prefix + 'stats.json'
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
            # simnearby_min(args[1])
            bktest_sim = BacktestManager(args[1])
        elif mode == 1:
            # simcontract_min(args[1])
            bktest_sim = ContBktestManager(args[1])
        bktest_sim.run_all_assets()
