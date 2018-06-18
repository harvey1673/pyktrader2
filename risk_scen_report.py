import cmq_book
import cmq_market_data
import datetime
import cmq_inst_risk
import cmq_inst
import copy
import pandas as pd
import numpy as np
import cmq_risk_engine
import multiprocessing as mp

def run_book_report(value_date, book, req_greeks = ['cmdelta', 'cmgamma', 'cmvega_atm', 'theta'], \
                    base_mkt = {}):
    if len(base_mkt) == 0:
        mkt_data = cmq_market_data.load_market_data(book.mkt_deps, value_date = value_date)
    else:
        mkt_data = base_mkt
    re = cmq_risk_engine.CMQRiskEngine(book, mkt_data, req_greeks)
    re.run_risk()
    # assume only one instrument for one deal
    deal_results = {}
    for deal in book.deal_list:
        if deal.positions[0][0].inst_type in ["ComEuroOption", 'ComMthAsian']:
            deal_id = deal.id
            deal_results[deal_id] = {}
            deal_results[deal_id]['strike'] = deal.positions[0][0].strike
            deal_results[deal_id]['otype'] = deal.positions[0][0].otype
            deal_results[deal_id]['end'] = deal.positions[0][0].end
            deal_results[deal_id]['volume'] = deal.positions[0][1] * deal.positions[0][0].volume
            deal_results[deal_id]['fwd_idx'] = deal.positions[0][0].fwd_index
            for greek in req_greeks:
                if greek in ['cmdelta', 'cmvega_atm', 'cmvega_v90', 'cmvega_v75', 'cmvega_v25', 'cmvega_v10', 'cmgamma']:
                    for fwd_idx in re.deal_risks[deal_id][greek]:
                        deal_results[deal_id][greek] = re.deal_risks[deal_id][greek][fwd_idx]
                else:
                    deal_results[deal_id][greek] = re.deal_risks[deal_id][greek]

    df = pd.DataFrame.from_dict(deal_results, orient='index')
    volume = pd.pivot_table(df, values='volume', index=['fwd_idx', 'end'], columns=['otype', 'strike']).fillna(0)
    delta = pd.pivot_table(df, values = 'cmdelta', index=['fwd_idx', 'end'], columns=['otype', 'strike']).fillna(0)
    gamma = pd.pivot_table(df, values='cmgamma', index=['fwd_idx', 'end'], columns=['otype', 'strike']).fillna(0)
    vega = pd.pivot_table(df, values='cmvega_atm', index=['fwd_idx', 'end'], columns=['otype', 'strike']).fillna(0)
    theta = pd.pivot_table(df, values='theta', index=['end'], columns=['otype', 'strike']).fillna(0)
    return volume, delta, gamma, vega, theta, df

def run_book(value_date, book, req_greeks = ['cmdelta', 'cmgamma', 'cmvega_atm', 'theta'], \
                    base_mkt = {}):
    book_obj = get_book(book)
    if len(base_mkt) == 0:
        mkt_data = cmq_market_data.load_market_data(book_obj.mkt_deps, value_date = value_date)
    else:
        mkt_data = base_mkt
    re = cmq_risk_engine.CMQRiskEngine(book_obj, mkt_data, req_greeks)
    re.run_risk()
    return re, book_obj, mkt_data

def book_greek_scen_report(value_date, book, \
                    req_greeks = ['pv', 'theta', 'cmdelta', 'cmgamma', 'cmvega_atm'], \
                    scens = ['COMFwd', [- 5.0, -3.0, -1.0, 0.0, 1.0, 3.0, 5.0], 0], \
                    base_mkt = {}, use_pool = False):
    if len(base_mkt) == 0:
        base_mkt = cmq_market_data.load_market_data(book.mkt_deps, value_date=value_date)
    output = {}
    if use_pool:
        num_cpus = mp.cpu_count() - 1
        pool = mp.Pool(num_cpus)
    else:
        pool = None
    re = {}
    fwd_list = book.mkt_deps[scens[0]].keys()
    for fwd_idx in fwd_list:
        for shift in scens[1]:
            mkt_data = cmq_inst_risk.generate_scen(base_mkt, scens[0], fwd_idx, curve_tenor = 'ALL', shift_size = shift, shift_type = scens[2])
            key = (fwd_idx, shift)
            re[key] = cmq_risk_engine.CMQRiskEngine(book, mkt_data, req_greeks, pool)
            re[key].run_scenarios()
    for fwd_idx in fwd_list:
        for shift in scens[1]:
            key = (fwd_idx, shift)
            re[key].summerize_risks()
            output[key] = copy.deepcopy(re[key].book_risks)
            for greek in req_greeks:
                if greek in ['cmdelta', 'cmvega_atm', 'cmgamma', 'cmvega_v90', 'cmvega_v75', 'cmvega_v25', 'cmvega_v10']:
                    if fwd_idx in output[key][greek]:
                        output[key][greek] = output[key][greek][fwd_idx]
                    else:
                        output[key][greek] = 0.0
    df = pd.DataFrame.from_dict(output, orient='index')
    return df

def greek_ladder_report(value_date, book, \
                        req_greeks = ['cmdeltas', 'cmgammas', 'cmvegas_atm'], \
                        scens = ['COMFwd', [-0.05, -0.03, -0.02, -0.01, 0.0, 0.01, 0.02, 0.03, 0.05], 1],\
                        base_mkt = {}, use_pool = False):
    if len(base_mkt) == 0:
        base_mkt = cmq_market_data.load_market_data(book.mkt_deps, value_date=value_date)
    output = dict([(greek, {}) for greek in req_greeks])
    if use_pool:
        num_cpus = mp.cpu_count() - 1
        pool = mp.Pool(num_cpus)
    else:
        pool = None
    re = {}
    fwd_list = book.mkt_deps[scens[0]].keys()
    for fwd_idx in fwd_list:
        for shift in scens[1]:
            key = (fwd_idx, shift)
            mkt_data = cmq_inst_risk.generate_scen(base_mkt, scens[0], fwd_idx, curve_tenor = 'ALL', shift_size = shift, shift_type = scens[2])
            re[key] = cmq_risk_engine.CMQRiskEngine(book, mkt_data, req_greeks, pool)
            re[key].run_scenarios()
    for fwd_idx in fwd_list:
        output[greek][fwd_idx] = {}
        for shift in scens[1]:
            key = (fwd_idx, shift)
            re[key].summerize_risks()
            if fwd_idx in re[key].book_risks[greek]:
                for greek in req_greeks:
                    output[greek][fwd_idx][shift] = copy.deepcopy(re[key].book_risks[greek][fwd_idx])
    res = dict([(greek, pd.DataFrame()) for greek in req_greeks])
    for greek in req_greeks:
        for fwd_idx in fwd_list:
            df = pd.DataFrame.from_dict(output[greek][fwd_idx], orient='columns')
            df.loc['Total', :] = df.sum()
            df = df.reset_index()
            df.rename(columns = {'index': 'tenor'}, inplace=True)
            cols = list(df.columns)
            df['fwd_idx'] = fwd_idx
            df = df[['fwd_idx'] + cols]
            res[greek] = res[greek].append(df)
        res[greek] = res[greek].set_index(['fwd_idx', 'tenor'])
    return res

def scenario_2d_report(value_date, book, greeks, \
        scens = [['COMFwd', 'SGXIRO', [-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0], 0], \
                ['COMVolATM', 'SGXIRO', [-0.02, -0.01, 0.0, 0.01, 0.02], 0]],\
                base_mkt = {}):
    if len(base_mkt) == 0:
        base_mkt = cmq_market_data.load_market_data(book.mkt_deps, value_date=value_date)
    res = {}
    for greek in greeks:
        output = {}
        for shift_x in scens[0][2]:
            mkt_data_x = cmq_inst_risk.generate_scen(base_mkt, scens[0][0], scens[0][1], 'ALL', \
                                                shift_size=shift_x, shift_type=scens[0][3])
            x_key = scens[0][0] + '_' + str(shift_x)
            output[x_key] = {}
            for shift_y in scens[1][2]:
                mkt_data_y = cmq_inst_risk.generate_scen(mkt_data_x, scens[1][0], scens[1][1], 'ALL', \
                                                shift_size = shift_y, shift_type = scens[1][3])
                re = cmq_risk_engine.CMQRiskEngine(book, mkt_data_y, [greek])
                re.run_risk()
                y_key = scens[1][0] + '_' + str(shift_y)
                output[x_key][y_key] = re.book_risks[greek]
                if greek in ['cmdelta', 'cmvega_atm', 'cmvega_v90', 'cmvega_v75', \
                             'cmvega_v25', 'cmvega_v10', 'cmgamma']:
                    output[x_key][y_key] = sum(output[x_key][y_key].values())
        res[greek] = pd.DataFrame.from_dict(output, orient='index')
    return res

def get_book(book_name, strategy = '', trade_dbtable = 'trade_data'):
    return cmq_book.get_book_from_db(book_name, strategy, [2,], trade_dbtable)

def get_market(book, today):
    return cmq_market_data.load_market_data(book.mkt_deps, value_date = today, is_eod = True)

def get_engine(book, mkt, greeks):
    return cmq_risk_engine.CMQRiskEngine(book, mkt, greeks)
