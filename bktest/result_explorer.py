import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

import json
import pandas as pd
import dbaccess
import misc
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
              "IF", "IH", "IC", "TF", "T", "sn"]
def load_btest_res(sim_names, dbtable = 'bktest_output'):
    cnx = dbaccess.connect(**dbaccess.bktest_dbconfig)
    stmt = "select * from {dbtable} where sim_name in ('{qlist}')".format( \
        dbtable=dbtable, qlist="','".join(sim_names))
    df = pd.read_sql(stmt, cnx)
    cnx.close()
    return df

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

def create_strat_json(df, inst_list, asset_keys, common_keys, capital = 4000.0):
    xdf = df.dropna(subset = ['name'])
    inst_dict = dict([(misc.inst2product(instID), instID) for instID in inst_list])
    xdf['instID'] = xdf['asset'].apply(lambda x: inst_dict[x])
    output = OrderedDict()
    sim_names = xdf['sim_name'].unique()
    sim_dict = load_sim_config(sim_names, config_folder = sim_config_folder)
    for idx, row in xdf.iterrows():
        if row['name'] not in output:
            output[row['name']]  = {'class': 'strat_dtchan_addon.DTSplitChanAddon',
                                    'config': OrderedDict([('name', row['name']), ('num_tick', 1), ('daily_close_buffer', 5), \
                                                           ('pos_scaler', 1.0), ('trade_valid_time', 600), ]),}
            for key in common_keys:
                if key in xdf:
                    if isinstance(row[key], basestring) and ('[' in row[key] and ']' in row[key]):
                        conf_dict[key] = json.loads(row[key])
                    else:
                        conf_dict[key] = row[key]
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

def process_DTsim():
    sim_names = ['DTvec_180214', 'DTasym_180214', 'DTvec_dchan_180214', \
                 'DTvec_pct10_180214', 'DTvec_pct25_180214', 'DTvec_pct45_180214',\
                 'DTsplit_180214', 'DT3sp_180214', 'DT4sp_180214']
    df = load_btest_res(sim_names)
    weight = {'6m': 0.5/2.5, '1y': 1.0/2.5, '2y': 1.0/2.5}
    df['w_sharp'] = calc_w_col(df, key = 'sharp_ratio', weight = weight)
    df['price_mode'] = df['par_value2']
    df['ma_chan'] = 0
    df['channels'] = 0
    df['min_rng'] = 0.0035
    df['freq'] = 1
    df['volumes'] = '[1]'
    df['vol_ratio'] = '[1.0, 0.0]'
    df['open_period'] = '[300, 2115]'
    df.ix[df.sim_name == 'DTsplit_180214', 'open_period'] = '[300, 1500, 2115]'
    df.ix[df.sim_name == 'DT3sp_180214', 'open_period'] = '[300, 1500, 1900, 2115]'
    df.ix[df.sim_name == 'DT4sp_180214', 'open_period'] = '[300, 1500, 1630, 1900, 2115]'
    filter = (df.sim_name == 'DTvec_180214') | (df.sim_name == 'DTasym_180214') \
             | (df.sim_name == 'DT3sp_180214') | (df.sim_name == 'DT4sp_180214') | (df.sim_name == 'DTsplit_180214')
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
        xdf1 = xdf[((xdf.sim_name == 'DTvec_180214') | (xdf.sim_name == 'DTasym_180214'))].sort_values('w_sharp', ascending=False)
        if len(xdf1) > 20:
            xdf1 = xdf1[:20]
        res = res.append(xdf1, ignore_index=True)
        xdf1 = xdf[((xdf.sim_name == 'DTsplit_180214') | (xdf.sim_name == 'DT3sp_180214') | (xdf.sim_name == 'DT4sp_180214'))].sort_values('w_sharp', ascending=False)
        if len(xdf1) > 20:
            xdf1 = xdf1[:20]
        res = res.append(xdf1, ignore_index=True)
        xdf1 = xdf[(xdf.sim_name != 'DTvec_180214') & (xdf.sim_name != 'DTasym_180214') & (xdf.sim_name != 'DTsplit_180214')\
            & (xdf.sim_name != 'DT3sp_180214') & (xdf.sim_name != 'DT4sp_180214')].sort_values('w_sharp', ascending=False)
        if len(xdf1) > 20:
            xdf1 = xdf1[:20]
        res = res.append(xdf1, ignore_index=True)
    out_cols = output_columns + ['freq', 'channels', 'ma_chan', 'price_mode', 'lookbacks', 'ratios', 'trend_factor', 'lot_size', 'min_rng', 'vol_ratio', 'volumes']
    out = res[out_cols]
    out.to_csv('DTvec.csv')
    return out

def process_RSIATRsim():
    sim_names = ['rsi_atr_1m', 'rsi_atr_5m', \
                 'rsi_atr_3m', 'rsi_atr_15m', 'rsi_atr_1m']
    df = load_btest_res(sim_names)
    weight = {'6m': 0.5/2.5, '1y': 1.0/2.5, '2y': 1.0/2.5}
    df['w_sharp'] = calc_w_col(df, key = 'sharp_ratio', weight = weight)
    df['close_daily'] = df['par_value1']
    df['atr_len'] = extract_element(df, 'par_value0', 1)
    df['atrma_len'] = extract_element(df, 'par_value0', 0)
    df['rsi_trigger'] = extract_element(df, 'par_value0', 2)
    df['rsi_len'] = extract_element(df, 'par_value0', 2)
    df['lot_size'] = df['asset'].apply(lambda x: misc.product_lotsize[x])
    df['std_unit'] = df['std_pnl_1y'] * df['lot_size']
    assets = asset_list
    res = pd.DataFrame()
    for asset in assets:
        xdf = df[(df.asset==asset) & (df.w_sharp > 0.8)]
        xdf1 = xdf[(xdf.sim_name == 'rsi_atr_1m') | (xdf.sim_name == 'rsi_atr_2m') | (xdf.sim_name == 'rsi_atr_3m')].sort_values('w_sharp', ascending=False)
        if len(xdf1) > 20:
            xdf1 = xdf1[:20]
        res = res.append(xdf1, ignore_index=True)
        xdf2 = xdf[(xdf.sim_name == 'rsi_atr_15m') | (xdf.sim_name == 'rsi_atr_5m')].sort_values('w_sharp', ascending=False)
        if len(xdf2) > 20:
            xdf2 = xdf2[:20]
        res = res.append(xdf2, ignore_index=True)

    out_cols = output_columns + ['chan', 'atr_len', 'atrma_len', 'rsi_len', 'rsi_trigger', 'close_daily', \
                                 'std_unit', 'w_sharp', 'lot_size']
    out = res[out_cols]
    out.to_csv('RSI_ATR.csv')
    return out

def create_DT_strat():
    inst_list = ['rb1805', 'hc1805', 'i1805', 'j1805', 'jm1805', 'ZC805', 'ni1805', 'ru1805', 'FG805',
                 'm1805', 'RM805', 'y1805', 'p1805', 'OI805', 'cs1805', 'c1805', 'jd1805', \
                 'pp1805', 'l1805', 'v1805', 'MA805', 'ag1806', 'au1806', 'cu1805', 'SM805', 'SF805', 'T1806']

    asset_keys = ['alloc_w', 'vol_ratio', 'lookbacks', 'ratios', 'trend_factor', \
                  'close_tday', 'channels', 'volumes', 'freq', 'price_mode', 'close_daily']
    common_keys = ['open_period']
    df = pd.read_excel(open('C:\\dev\\pyktlib\\DTvec.xlsx', 'rb'), sheetname = 'DTvec')
    output = create_strat_json(df, inst_list, asset_keys, common_keys, capital = 1700.0)
    for key in output:
        with open("C:\\dev\\data\\" + key + ".json", 'w') as outfile:
            json.dump(output[key], outfile)

