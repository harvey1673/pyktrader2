import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

import json
import pandas as pd
import numpy as np
import dbaccess
import misc
import ts_tool
import datetime
from collections import OrderedDict
sim_config_folder = "C:/dev/pyktlib/pyktrader2/btest_setup/"

output_columns = ['asset', 'sim_name', 'scen_id', 'std_unit', \
                'w_sharp', 'sharp_ratio_3m', 'sharp_ratio_6m', 'sharp_ratio_1y', 'sharp_ratio_2y', 'sharp_ratio_3y',\
                'tot_pnl_3m', 'tot_pnl_6m','tot_pnl_1y', 'tot_pnl_2y','tot_pnl_3y', \
                'tot_cost_3m', 'tot_cost_6m', 'tot_cost_1y', 'tot_cost_2y', 'tot_cost_3y',\
                'par_name0', 'par_value0', 'par_name1', 'par_value1','par_name2', 'par_value2',\
                'par_name3', 'par_value3', 'par_name4', 'par_value4', ]

asset_list =  ["rb", "hc", "i", "j", "jm", "ZC", "ni", "ru", \
              "m", "RM", "FG", "y", "p", "OI", "a", "cs", "c", \
              "jd", "SR", "CF", "pp", "l", "v", "TA", "MA", "ag", \
              "au", "cu", "al", "zn", "SM", "SF", \
              "IF", "IH", "IC", "TF", "T", "sn", "AP"]

def load_btest_res(sim_names, dbtable = 'bktest_output'):
    cnx = dbaccess.connect(**dbaccess.bktest_dbconfig)
    stmt = "select * from {dbtable} where sim_name in ('{qlist}')".format( \
        dbtable=dbtable, qlist="','".join(sim_names))
    df = pd.read_sql(stmt, cnx)
    cnx.close()
    return df

def load_btest_from_file(csvfile):
    sim_df = pd.read_csv(csvfile)
    df = load_btest_pnl(sim_df[['sim_name', 'asset', 'scen_id']].values)
    return df

def load_btest_pnl(sim_keys, dbtable  = 'bktest_output'):
    cnx = dbaccess.connect(**dbaccess.bktest_dbconfig)
    df_list = []
    for sim_key in sim_keys:
        stmt = "select * from {dbtable} where sim_name = '{name}' and asset = '{asset}' and scen_id = {scen}".format( \
            dbtable=dbtable, name = sim_key[1], asset = sim_key[0], scen = int(sim_key[2]))
        tdf = pd.read_sql(stmt, cnx)
        pnl_file = tdf['pnl_file'][0]
        xdf = pd.read_csv(pnl_file)
        xdf['date'] = xdf['date'].apply(lambda x: datetime.datetime.strptime(x, "%Y-%m-%d").date())
        xdf = xdf[['date', 'daily_pnl']].set_index('date')
        xdf.rename(columns = {'daily_pnl': '-'.join([ str(k) for k in sim_key])}, inplace = True)
        df_list.append(xdf)
    df = ts_tool.merge_df(df_list)
    return df

def calc_mthly_by_prod(csvfile, products, xlfile, start_date = None, freq = '3M'):
    port_data = pd.read_csv(csvfile)
    writer = pd.ExcelWriter(xlfile)
    df_dict = {}
    for prod in products:
        prod_port = port_data[port_data['asset']==prod]
        prod_df = load_btest_pnl(prod_port[['asset', 'sim_name', 'scen_id']].values)
        if start_date:
            prod_df = prod_df[prod_df.index >= start_date]
        prod_df.fillna(0.0).cumsum().to_excel(writer, prod + '_D', startcol= 0, startrow=1)
        prod_df.index = pd.to_datetime(prod_df.index)
        prod_xdf = prod_df.fillna(0.0).resample(freq).sum()
        prod_xdf.to_excel(writer, prod + '_' + freq, startcol=0, startrow=1)
        df_dict[prod] = prod_df
    return df_dict

def calc_cov_by_asset(df, asset = None, start_date = None, end_date = None, tenor = None, bias = False):
    if asset == None:
        columns = df.columns
    else:
        columns = [ col for col in df.columns if col.startswith(asset + '-')]
    xdf = df[columns].fillna(0.0)
    if end_date:
        xdf = xdf[df.index <= end_date]
    end_date = xdf.index[-1]
    if tenor:
        start_date = misc.day_shift(end_date, tenor)
    if start_date:
        xdf = xdf[xdf.index >= start_date]
    cov = np.cov(xdf.values.T, bias = bias)
    avg = np.mean(xdf.values, axis = 0)
    weights = np.linalg.inv(cov).dot(avg)
    res = {'weight': weights, 'avg': avg, 'cov': cov, 'columns': columns}
    return res

def calc_weighted_port(df, weights, columns):
    combo_pnl = pd.Series(0.0, index = df.index)
    for w, col in zip(weights, columns):
        combo_pnl = combo_pnl + w * df[col]
    return combo_pnl

def load_sim_config(sim_names, config_folder = sim_config_folder):
    sim_dict = {}
    for sname in sim_names:
        config_file = config_folder + sname + '.json'
        with open(config_file, 'r') as fp:
            sim_dict[sname] = json.load(fp)
    return sim_dict

def filter_cond(df, key = 'sharp_ratio', cond = {'6m': 0.0, '1y': 0.5, '2y': 0.5}):
    selector = True
    for tenor in cond:
        selector = (df[key + '_' + tenor] >= cond[tenor]) & selector
    return df[selector]

def calc_w_col(df, key = 'sharp_ratio', weight = {'6m': 0.2, '1y': 0.4, '2y': 0.4}):
    ts = 0
    for tenor in weight:
        ts = ts + df[key + '_' + tenor] * weight[tenor]
    return ts

def extract_element(df, col_name, n):
    return df[col_name].apply(lambda x: json.loads(x)[n])

def create_strat_json(df, inst_list, asset_keys, common_keys, capital = 4000.0, strat_class = "strat_ma_system.MASystemTrader"):
    xdf = df.dropna(subset = ['name'])
    inst_dict = dict([(misc.inst2product(instID), instID) for instID in inst_list])
    xdf['instID'] = xdf['asset'].apply(lambda x: inst_dict[x])
    output = OrderedDict()
    sim_names = xdf['sim_name'].unique()
    sim_dict = load_sim_config(sim_names, config_folder = sim_config_folder)
    for idx, row in xdf.iterrows():
        if row['name'] not in output:
            output[row['name']]  = {'class': strat_class,
                                    'config': OrderedDict([('name', row['name']), ('num_tick', 1), ('daily_close_buffer', 5), \
                                                           ('pos_scaler', 1.0), ('trade_valid_time', 600), ]),}
            for key in common_keys:
                if key in xdf:
                    if isinstance(row[key], basestring) and ('[' in row[key] and ']' in row[key]):
                        output[row['name']]['config'][key] = json.loads(row[key])
                    else:
                        output[row['name']]['config'][key] = row[key]
                elif key in sim_dict[row['sim_name']]:
                    output[row['name']]['config'][key] = sim_dict[row['sim_name']][key]
                elif key in sim_dict[row['sim_name']]['config']:
                    output[row['name']]['config'][key] = sim_dict[row['sim_name']]['config'][key]
            output[row['name']]['config']['assets'] = []
        conf_dict = OrderedDict()
        conf_dict["underliers"] = [row['instID']]
        for key in asset_keys:
            if key == 'alloc_w':
                conf_dict[key] = round(capital/row['std_unit'] * row['w_sharp'], 1)
            elif key in xdf:
                if isinstance(row[key], basestring) and ('[' in row[key] and ']' in row[key]):
                    conf_dict[key] = json.loads(row[key])
                else:
                    conf_dict[key] = row[key]
            elif key in sim_dict[row['sim_name']]:
                conf_dict[key] = sim_dict[row['sim_name']][key]
            elif key in sim_dict[row['sim_name']]['config']:
                conf_dict[key] = sim_dict[row['sim_name']]['config'][key]
        output[row['name']]['config']['assets'].append(conf_dict)
    return output

def process_DTSim():
    sim_names = ['DTvec_181123', 'DT2sp_181123', 'DT3sp_181123', 'DT4sp_181123', \
                'DTvec_dchan_181123', 'DT2sp_dchan_181123', 'DT3sp_dchan_181123', 'DT4sp_dchan_181123', \
                'DT3p_pct25_181123', 'DT3p_pct45_181123', 'DT3p_pct10_181123', \
                'DT4p_pct25_181123', 'DT4p_pct45_181123', 'DT4p_pct10_181123']
    df = load_btest_res(sim_names)
    filter = df['sharp_ratio_3y'].isnull()
    df.ix[filter, 'sharp_ratio_3y'] = df.ix[filter, 'sharp_ratio_2y']
    weight = {'6m': 0.5/2.5, '1y': 1.0/3.5, '2y': 1.0/3.5, '3y': 1.0/3.5}
    df['w_sharp'] = calc_w_col(df, key = 'sharp_ratio', weight = weight)
    df['price_mode'] = df['par_value2']
    df['ma_chan'] = 0
    df['channels'] = 0
    df['min_rng'] = 0.0035
    df['freq'] = 1
    df['volumes'] = '[1]'
    df['vol_ratio'] = '[1.0, 0.0]'
    df['open_period'] = '[300, 2115]'
    df.ix[(df.sim_name == 'DT2sp_181123') | (df.sim_name == 'DT2sp_dchan_181123'), 'open_period'] = '[300, 1500, 2115]'
    df.ix[(df.sim_name == 'DT3sp_181123') | (df.sim_name == 'DT3sp_dchan_181123') \
          | (df.sim_name == 'DT3sp_pct10_181123') | (df.sim_name == 'DT3sp_pct25_181123') \
          | (df.sim_name == 'DT3sp_pct45_181123'), 'open_period'] = '[300, 1500, 1900, 2115]'
    df.ix[(df.sim_name == 'DT4sp_181123') | (df.sim_name == 'DT4sp_dchan_181123') \
          | (df.sim_name == 'DT4sp_pct10_181123') | (df.sim_name == 'DT4sp_pct25_181123') \
          | (df.sim_name == 'DT4sp_pct45_181123'), 'open_period'] = '[300, 1500, 1630, 1900, 2115]'
    filter = (df.sim_name == 'DTvec_181123') | (df.sim_name == 'DT2sp_181123') | (df.sim_name == 'DT3sp_181123') | (df.sim_name == 'DT4sp_181123')
    df.ix[filter, 'ma_chan'] = df.ix[filter, 'par_value1']
    df.ix[~filter, 'channels'] = df.ix[~filter, 'par_value1']
    df.ix[~filter, 'vol_ratio'] = '[0.0, 1.0]'
    df['lookbacks'] = extract_element(df, 'par_value0', 1)
    df['ratios'] = extract_element(df, 'par_value0', 0)
    df['trend_factor'] = extract_element(df, 'par_value0', 2)
    df['lot_size'] = df['asset'].apply(lambda x: misc.product_lotsize[x])
    df['std_unit'] = df['std_pnl_1y'] * df['lot_size']
    assets = asset_list
    res = pd.DataFrame()
    for asset in assets:
        xdf = df[(df.asset==asset) & (df.w_sharp > 0.8)]
        xdf1 = xdf[((xdf.sim_name == 'DTvec_181123'))].sort_values('w_sharp', ascending=False)
        if len(xdf1) > 20:
            xdf1 = xdf1[:20]
        res = res.append(xdf1, ignore_index=True)
        xdf1 = xdf[((xdf.sim_name == 'DT2sp_181123') | (xdf.sim_name == 'DT3sp_181123') | (xdf.sim_name == 'DT4sp_181123'))].sort_values('w_sharp', ascending=False)
        if len(xdf1) > 30:
            xdf1 = xdf1[:30]
        res = res.append(xdf1, ignore_index=True)
        xdf1 = xdf[(xdf.sim_name != 'DTvec_181123') & (xdf.sim_name != 'DT2sp_181123')\
            & (xdf.sim_name != 'DT3sp_181123') & (xdf.sim_name != 'DT4sp_181123')].sort_values('w_sharp', ascending=False)
        if len(xdf1) > 30:
            xdf1 = xdf1[:30]
        res = res.append(xdf1, ignore_index=True)
    out_cols = output_columns + ['freq', 'channels', 'ma_chan', 'price_mode', 'lookbacks', 'ratios', \
                                 'trend_factor', 'lot_size', 'min_rng', 'vol_ratio', 'volumes', 'open_period']
    out = res[out_cols]
    out.to_csv('DT_results_181123.csv')
    return out

def process_RSIATRsim():
    sim_names = ['RSI_ATRMA10_1m', 'RSI_ATRMA20_1m', 'RSI_ATRMA10_2m', 'RSI_ATRMA10_5m', \
                 'RSI_ATRMA10_3m', 'RSI_ATRMA10_15m']
    df = load_btest_res(sim_names)
    filter = df['sharp_ratio_3y'].isnull()
    df.ix[filter, 'sharp_ratio_3y'] = df.ix[filter, 'sharp_ratio_2y']
    weight = {'6m': 0.5/2.5, '1y': 1.0/3.5, '2y': 1.0/3.5, '3y': 1.0/3.5}
    df['w_sharp'] = calc_w_col(df, key = 'sharp_ratio', weight = weight)
    df['atrma_win'] = 10
    filter = df['sim_name'].str.contains('MA20')
    df.ix[filter, 'atrma_period'] = 20
    df['freq'] = 1
    df.ix[(df.sim_name ==  'RSI_ATRMA10_2m'), 'freq'] = 2
    df.ix[(df.sim_name ==  'RSI_ATRMA10_3m'), 'freq'] = 3
    df.ix[(df.sim_name ==  'RSI_ATRMA10_5m'), 'freq'] = 5
    df.ix[(df.sim_name ==  'RSI_ATRMA10_15m'), 'freq'] = 15
    df['rsi_th'] = df['par_value0']
    df['rsi_win'] = df['par_value1']
    df['atr_win'] = df['par_value2']
    df['stoploss'] = df['par_value3']
    df['close_tday'] = df['par_value4']
    df['lot_size'] = df['asset'].apply(lambda x: misc.product_lotsize[x])
    df['std_unit'] = df['std_pnl_1y'] * df['lot_size']
    df['volumes'] = '[1]'
    assets = asset_list
    res = pd.DataFrame()
    for asset in assets:
        xdf = df[(df.asset==asset) & (df.w_sharp > 0.6)]
        xdf1 = xdf[(xdf.sim_name == 'RSI_ATRMA10_1m') | (xdf.sim_name == 'RSI_ATRMA10_2m') | (xdf.sim_name =='RSI_ATRMA20_1m')].sort_values('w_sharp', ascending=False)
        if len(xdf1) > 20:
            xdf1 = xdf1[:20]
        res = res.append(xdf1, ignore_index=True)
        xdf2 = xdf[(xdf.sim_name == 'RSI_ATRMA10_3m') | (xdf.sim_name == 'RSI_ATRMA10_5m')].sort_values('w_sharp', ascending=False)
        if len(xdf2) > 20:
            xdf2 = xdf2[:20]
        res = res.append(xdf2, ignore_index=True)

    out_cols = output_columns + ['freq', 'rsi_th', 'rsi_win', 'stoploss', 'atr_win', 'atrma_win', 'close_tday', \
                                 'std_unit', 'lot_size', 'volumes']
    out = res[out_cols]
    out.to_csv('RSI_ATR_181123.csv')
    return out

def process_ChanbreakSim():
    sim_names = ['chanbreak_daily_181123', 'chanbreak_2sp_181123', 'chanbreak_3sp_181123', 'chanbreak_4sp_181123']
    df = load_btest_res(sim_names)
    filter = df['sharp_ratio_3y'].isnull()
    df.ix[filter, 'sharp_ratio_3y'] = df.ix[filter, 'sharp_ratio_2y']
    weight = {'6m': 0.5/2.5, '1y': 1.0/3.5, '2y': 1.0/3.5, '3y': 1.0/3.5}
    df['w_sharp'] = calc_w_col(df, key = 'sharp_ratio', weight = weight)
    df['stoploss_win'] = df['par_value0']
    df['stoploss'] = df['par_value1']
    df['channel'] = df['par_value2']
    df['lot_size'] = df['asset'].apply(lambda x: misc.product_lotsize[x])
    df['std_unit'] = df['std_pnl_1y'] * df['lot_size']
    df['volumes'] = '[1]'
    df['open_period'] = '[300, 2115]'
    df.ix[(df.sim_name == 'chanbreak_2sp_181123'), 'open_period'] = '[300, 1500, 2115]'
    df.ix[(df.sim_name == 'chanbreak_3sp_181123'), 'open_period'] = '[300, 1500, 1900, 2115]'
    df.ix[(df.sim_name == 'chanbreak_4sp_181123'), 'open_period'] = '[300, 1500, 1630, 1900, 2115]'
    assets = asset_list
    res = pd.DataFrame()
    for asset in assets:
        xdf = df[(df.asset==asset) & (df.sharp_ratio_3y > 0.6)]
        filter = (xdf['sim_name']=='chanbreak_daily_181123')
        xdf1 = xdf[filter].sort_values('w_sharp', ascending=False)
        if len(xdf1) > 10:
            xdf1 = xdf1[:10]
        res = res.append(xdf1, ignore_index=True)
        filter = (xdf['sim_name'] == 'chanbreak_2sp_181123')
        xdf1 = xdf[filter].sort_values('w_sharp', ascending=False)
        if len(xdf1) > 10:
            xdf1 = xdf1[:10]
        res = res.append(xdf1, ignore_index=True)
        filter = (xdf['sim_name'] == 'chanbreak_3sp_181123')
        xdf1 = xdf[filter].sort_values('w_sharp', ascending=False)
        if len(xdf1) > 10:
            xdf1 = xdf1[:10]
        res = res.append(xdf1, ignore_index=True)
        filter = (xdf['sim_name'] == 'chanbreak_4sp_181123')
        xdf1 = xdf[filter].sort_values('w_sharp', ascending=False)
        if len(xdf1) > 10:
            xdf1 = xdf1[:10]
        res = res.append(xdf1, ignore_index=True)
    out_cols = output_columns + ['stoploss_win', 'stoploss', 'channel','open_period', 'std_unit', 'lot_size', 'volumes']
    out = res[out_cols]
    out.to_csv('Chanbreak_results_181123.csv')
    return out

def process_MAChanSim():
    sim_names = ['MA2cross_daily_181123']
    df = load_btest_res(sim_names)
    filter = df['sharp_ratio_3y'].isnull()
    df.ix[filter, 'sharp_ratio_3y'] = df.ix[filter, 'sharp_ratio_2y']
    weight = {'6m': 0.5/2.5, '1y': 1.0/3.5, '2y': 1.0/3.5, '3y': 1.0/3.5}
    df['w_sharp'] = calc_w_col(df, key = 'sharp_ratio', weight = weight)
    df['win_s'] = extract_element(df, 'par_value0', 0)
    df['win_l'] = extract_element(df, 'par_value0', 1)
    df['win_list'] = df['par_value0']
    df['lot_size'] = df['asset'].apply(lambda x: misc.product_lotsize[x])
    df['std_unit'] = df['std_pnl_1y'] * df['lot_size']
    df['volumes'] = '[1]'
    assets = asset_list
    res = pd.DataFrame()
    for asset in assets:
        xdf = df[(df.asset==asset) & (df.w_sharp > 0.5)]
        xdf1 = xdf.sort_values('w_sharp', ascending=False)
        if len(xdf1) > 20:
            xdf1 = xdf1[:20]
        res = res.append(xdf1, ignore_index=True)
    out_cols = output_columns + ['win_l', 'win_s', 'std_unit', 'lot_size', 'volumes']
    out = res[out_cols]
    out.to_csv('MA2cross_results_181123.csv')
    return out

def process_MARibbonSim():
    sim_names = ['ma_ribbon']
    df = load_btest_res(sim_names)
    filter = df['sharp_ratio_3y'].isnull()
    df.ix[filter, 'sharp_ratio_3y'] = df.ix[filter, 'sharp_ratio_2y']
    weight = {'6m': 0.5/2.5, '1y': 1.0/3.5, '2y': 1.0/3.5, '3y': 1.0/3.5}
    df['w_sharp'] = calc_w_col(df, key = 'sharp_ratio', weight = weight)
    df['freq'] = df['par_value0']
    df['param'] = df['par_value1']
    df['lot_size'] = df['asset'].apply(lambda x: misc.product_lotsize[x])
    df['std_unit'] = df['std_pnl_1y'] * df['lot_size']
    df['volumes'] = '[1]'
    assets = asset_list
    res = pd.DataFrame()
    for asset in assets:
        xdf = df[(df.asset==asset) & (df.w_sharp > 0.5)]
        filter = (xdf['freq']=='1min') | (xdf['freq']=='3min') | (xdf['freq']=='5min')
        xdf1 = xdf[filter].sort_values('w_sharp', ascending=False)
        if len(xdf1) > 20:
            xdf1 = xdf1[:20]
        res = res.append(xdf1, ignore_index=True)
        xdf2 = xdf[~filter].sort_values('w_sharp', ascending=False)
        if len(xdf2) > 20:
            xdf2 = xdf2[:20]
        res = res.append(xdf2, ignore_index=True)

    out_cols = output_columns + ['param', 'std_unit', 'lot_size', 'volumes', 'freq']
    out = res[out_cols]
    out.to_csv('ma_ribbon_181123.csv')
    return out


inst_list = ['rb1901', 'hc1810', 'i1809', 'j1809', 'jm1809', 'ZC809', 'ni1809', 'ru1809', 'FG809',
                 'm1809', 'RM809', 'y1809', 'p1809', 'OI809', 'cs1809', 'c1809', 'jd1809', 'a1809',\
                 'pp1809', 'l1809', 'v1809', 'MA809', 'al1807', 'cu1807', 'ag1806', 'au1806', 'SM809', 'SF809', 'T1806']

def create_DT_strat():
    asset_keys = ['alloc_w', 'vol_ratio', 'lookbacks', 'ratios', 'trend_factor', \
                  'close_tday', 'channels', 'volumes', 'freq', 'price_mode', 'close_daily']
    common_keys = ['open_period']
    df = pd.read_excel(open('C:\\dev\\pyktlib\\DTsim_181123.xlsx', 'rb'), sheetname = 'DTvec')
    output = create_strat_json(df, inst_list, asset_keys, common_keys, capital = 1500.0, strat_class = "strat_dtsp_chan.DTSplitChan")
    for key in output:
        with open("C:\\dev\\data\\" + key + ".json", 'w') as outfile:
            json.dump(output[key], outfile)

def create_RSIATR_strat():
    asset_keys = ['alloc_w', 'rsi_th', 'rsi_win', 'atr_win', 'atrma_win', 'stoploss',\
                  'close_tday', 'volumes', 'freq']
    common_keys = []
    df = pd.read_excel(open('C:\\dev\\pyktlib\\RSI_ATR_181123.xlsx', 'rb'), sheetname = 'RSI_ATR_181123')
    output = create_strat_json(df, inst_list, asset_keys, common_keys, capital = 1500.0, strat_class = "strat_rsiatr.RsiAtrStrat")
    for key in output:
        with open("C:\\dev\\data\\" + key + ".json", 'w') as outfile:
            json.dump(output[key], outfile)

def create_MAChan_strat():
    asset_keys = ['alloc_w', 'ma_win', 'channels', 'close_tday', 'volumes', 'freq']
    common_keys = []
    df = pd.read_excel(open('C:\\dev\\pyktlib\\EMAChansim_181123.xlsx', 'rb'), sheetname = 'EMA3Chan_181123')
    output = create_strat_json(df, inst_list, asset_keys, common_keys, capital = 1500.0, strat_class = "strat_ma_system.MASystemTrader")
    for key in output:
        with open("C:\\dev\\data\\" + key + ".json", 'w') as outfile:
            json.dump(output[key], outfile)