import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

import json
import pandas as pd
import dbaccess
import misc

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

def create_strat_json(df, inst_list, asset_keys, capital = 4000.0):
    xdf = df.dropna(subset = ['name'])
    inst_dict = dict([(misc.inst2product(instID), instID) for instID in inst_list])
    xdf['instID'] = xdf['asset'].apply(lambda x: inst_dict[x])
    output = {}
    sim_names = xdf['sim_name'].unique()
    sim_dict = load_sim_config(sim_names, config_folder = sim_config_folder)
    for i in range(len(xdf)):
        if str(df['name']) not in output:
            output[str(df['name'])]  = {'config': {'name': str(df['name']), 'num_tick': 1, 'daily_close_buffer': 5, \
                                                   'trade_valid_time': 600, 'open_period': [300, 2115], 'assets':[]},
                                        'class': 'strat_dtchan_addon.DTSplitChanAddon', }
        conf_dict = {"underliers": [xdf['instID'][i]], }
        for key in asset_keys:
            if key == 'alloc_w':
                conf_dict[key] = capital/xdf['std_unit'][i]*xdf['w_sharp'][i]
            elif key in xdf:
                if isinstance(xdf[key][i], basestring) and '[' in xdf[key][i]:
                    conf_dict[key] = json.loads(xdf[key][i])
                else:
                    conf_dict[key] = xdf[key][i]
            elif key in sim_dict[xdf['sim_name'][i]]:
                conf_dict[key] = sim_dict[xdf['sim_name'][i]][key]
            elif key in sim_dict[xdf['sim_name'][i]]['config']:
                conf_dict[key] = sim_dict[xdf['sim_name'][i]]['config'][key]
        output[str(df['name'])]['config']['assets'].append(conf_dict)
    return output

def process_DTsim():
    sim_names = ['DTvec_180214', 'DTasym_180214', 'DTvec_dchan_180214', \
                 'DTvec_pct10_180214', 'DTvec_pct25_180214', 'DTvec_pct45_180214']
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
    filter = (df.sim_name == 'DTvec_180214') | (df.sim_name == 'DTasym_180214')
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
        xdf2 = xdf[(xdf.sim_name != 'DTvec_180214') & (xdf.sim_name != 'DTasym_180214')].sort_values('w_sharp', ascending=False)
        if len(xdf2) > 20:
            xdf2 = xdf2[:20]
        res = res.append(xdf2, ignore_index=True)
    out_cols = output_columns + ['freq', 'channels', 'ma_chan', 'price_mode', 'lookbacks', 'ratios', 'trend_factor', 'lot_size', 'min_rng', 'vol_ratio']
    out = res[out_cols]
    out.to_csv('DTvec.csv')
    return out

def process_RSIATRsim():
    sim_names = ['rsi_atr_1m', 'rsi_atr_5m', \
                 'rsi_atr_3m', 'rsi_atr_15m', 'rsi_atr_2m']
    df = load_btest_res(sim_names)
    weight = {'6m': 0.5/2.5, '1y': 1.0/2.5, '2y': 1.0/2.5}
    df['w_sharp'] = calc_w_col(df, key = 'sharp_ratio', weight = weight)
    df['price_mode'] = df['par_value2']
    df['chan'] = df['par_value1']
    df['lookbacks'] = extract_element(df, 'par_value0', 1)
    df['ratios'] = extract_element(df, 'par_value0', 0)
    df['trend_factor'] = extract_element(df, 'par_value0', 2)
    df['lot_size'] = df['asset'].apply(lambda x: misc.product_lotsize[x])
    df['std_unit'] = df['std_pnl_1y'] * df['lot_size']
    assets = asset_list
    res = pd.DataFrame()
    for asset in assets:
        xdf = df[(df.asset==asset) & (df.w_sharp > 0.8)]
        xdf1 = xdf[((xdf.sim_name == 'DTvec_180214') | (xdf.sim_name == 'DTasyn_180214')) \
                   & (df.par_value1 == '0')].sort_values('w_sharp', ascending=False)
        if len(xdf1) > 10:
            xdf1 = xdf1[:10]
        res = res.append(xdf1, ignore_index=True)
        xdf2 = xdf[xdf.sim_name != 'DTvec_180214'].sort_values('w_sharp', ascending=False)
        if len(xdf2) > 10:
            xdf2 = xdf2[:10]
        res = res.append(xdf2, ignore_index=True)

    out_cols = output_columns + ['chan', 'price_mode', 'lookbacks', 'ratios', 'trend_factor', 'lot_size']
    out = res[out_cols]
    out.to_csv('RSI_ATR.csv')
    return out










