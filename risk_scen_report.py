import cmq_book
import cmq_market_data
import datetime
import cmq_inst_risk
import cmq_inst
import copy
import pandas as pd
import cmq_risk_engine

def run_book_report(value_date, book, fwd_idx = 'SGXIRO'):
    mkt_data = cmq_market_data.load_market_data(book.mkt_deps, value_date = value_date)
    req_greeks = ['pv','cmdelta','cmgamma','cmvega_atm', 'theta']
    re = cmq_risk_engine.CMQRiskEngine(book, mkt_data, req_greeks)
    re.run_risk()

    # assume only one instrument for one deal
    deal_results = copy.deepcopy(re.deal_risks)
    for deal in book.deal_list:
        deal_id = deal.id
        deal_results[deal_id]['strike'] = deal.positions[0][0].strike
        deal_results[deal_id]['otype'] = deal.positions[0][0].otype
        deal_results[deal_id]['end'] = deal.positions[0][0].end
        deal_results[deal_id]['volume'] = deal.positions[0][1]
        for greek in req_greeks:
            if greek in ['cmdelta', 'cmvega_atm', 'cmvega_v90', 'cmvega_v75', 'cmvega_v25', 'cmvega_v10', 'cmgamma']:
                deal_results[deal_id][greek] = deal_results[deal_id][greek][fwd_idx]
    df = pd.DataFrame.from_dict(deal_results, orient='index')
    vol_tbl = df.pivot_table(columns = ['otype','strike'], index = ['end'], values = ['volume'], aggfunc = 'sum')/1000.0
    delta_tbl = df.pivot_table(columns=['otype', 'strike'], index = ['end'], values = ['cmdelta'], aggfunc = 'sum')/1000.0
    gamma_tbl = df.pivot_table(columns=['otype', 'strike'], index=['end'], values=['cmgamma'], aggfunc = 'sum')/1000.0
    vega_tbl = df.pivot_table(columns=['otype', 'strike'], index=['end'], values=['cmvega_atm'], aggfunc = 'sum')/1000.0
    theta_tbl = df.pivot_table(columns=['otype', 'strike'], index=['end'], values=['theta'], aggfunc = 'sum')/1000.0
    return re, df

def book_greek_scen_report(value_date, book, \
                    req_greeks = ['pv', 'theta', 'cmdelta', 'cmgamma', 'cmvega_atm'], \
                    scens = ['COMFwd', 'SGXIRO',  [- 5.0, -3.0, -1.0, 0.0, 1.0, 3.0, 5.0], 0], \
                    base_mkt = {}):
    if len(base_mkt) == 0:
        base_mkt = cmq_market_data.load_market_data(book.mkt_deps, value_date=value_date)
    output = {}
    for shift in scens[2]:
        mkt_data = cmq_inst_risk.generate_scen(base_mkt, scens[0], scens[1], curve_tenor = 'ALL', shift_size = shift, shift_type = scens[3])
        re = cmq_risk_engine.CMQRiskEngine(book, mkt_data, req_greeks)
        re.run_risk()
        output[shift] = copy.deepcopy(re.book_risks)
        for greek in req_greeks:
            if greek in ['cmdelta', 'cmvega_atm', 'cmgamma', 'cmvega_v90', 'cmvega_v75', 'cmvega_v25', 'cmvega_v10']:
                output[shift][greek] = sum(output[shift][greek].values())
    df = pd.DataFrame.from_dict(output, orient='index')
    return df

def greeks_ladder_report(value_date, book, \
                        req_greeks = ['cmdeltas', 'cmgammas', 'cmvegas_atm'], \
                        scens = ['COMFwd', 'SGXIRO', [-5.0, -4.0, -3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0], 0],\
                        base_mkt = {}):
    if len(base_mkt) == 0:
        base_mkt = cmq_market_data.load_market_data(book.mkt_deps, value_date=value_date)
    output = dict([(greek, {}) for greek in req_greeks])
    for shift in scens[2]:
        mkt_data = cmq_inst_risk.generate_scen(base_mkt, scens[0], scens[1], curve_tenor = 'ALL', shift_size = shift, shift_type = scens[3])
        re = cmq_risk_engine.CMQRiskEngine(book, mkt_data, req_greeks)
        re.run_risk()
        for greek in req_greeks:
            for idx in re.book_risks[greek]:
                if idx not in output[greek]:
                    output[greek][idx] = {}
                output[greek][idx][shift] = copy.deepcopy(re.book_risks[greek][idx])
    res = dict([(greek, {}) for greek in req_greeks])
    for greek in req_greeks:
        for idx in output[greek]:
            if idx not in res[greek]:
                res[greek][idx] = {}
            res[greek][idx] = pd.DataFrame.from_dict(output[greek][idx], orient='columns')
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
