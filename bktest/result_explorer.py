import json
import pandas as pd
import dbaccess
import misc

sim_config_folder = "C:/dev/pyktlib/pyktrader2/btest_setup/"

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

def test_run():
    sim_names = ['DTvec_180214', 'DTvec_dchan_180214', \
                 'DTvec_pct10_180214', 'DTvec_pct25_180214', 'DTvec_pct45_180214']
    df = load_btest_res(sim_names)
    weight = {'6m': 0.5/2.5, '1y': 1.0/2.5, '2y': 1.0/2.5}
    df['weighted_SR'] = calc_w_col(df, key = 'sharp_ratio', weight = weight)
    