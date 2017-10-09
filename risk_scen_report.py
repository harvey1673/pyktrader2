import cmq_book
import cmq_market_data
import datetime
import cmq_inst_risk
import cmq_inst
import copy
import pandas as pd
import cmq_risk_engine

def run_book_report(value_date, book_name, fwd_idx = 'SGXIRO'):
    book = cmq_book.get_book_from_db(book_name, status=[2])
    mkt_data = cmq_market_data.load_market_data(book.mkt_deps, value_date = value_date)
    req_greeks = ['pv','cmdelta','cmgamma','cmvega','theta']
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
        for greek in ['cmdelta', 'cmvega', 'cmgamma']:
            deal_results[deal_id][greek] = deal_results[deal_id][greek][fwd_idx]
    df = pd.DataFrame.from_dict(deal_results, orient='index')
    vol_tbl = df.pivot_table(columns = ['otype','strike'], index = ['end'], values = ['volume'], aggfunc = 'sum')
    delta_tbl = df.pivot_table(columns=['otype', 'strike'], index = ['end'], values = ['cmdelta'], aggfunc = 'sum')
    gamma_tbl = df.pivot_table(columns=['otype', 'strike'], index=['end'], values=['cmgamma'], aggfunc = 'sum')
    vega_tbl = df.pivot_table(columns=['otype', 'strike'], index=['end'], values=['cmvega'], aggfunc = 'sum')
    theta_tbl = df.pivot_table(columns=['otype', 'strike'], index=['end'], values=['theta'], aggfunc = 'sum')
    return re, df

def ladder_greek_report(value_date, book_name, scens = ['COMFwd', 'SGXIRO', \
                    [- 5.0, -4.0, -3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0], cmq_inst.CurveShiftType.Abs]):
    book = cmq_book.get_book_from_db(book_name, status=[2])
    base_mkt = cmq_market_data.load_market_data(book.mkt_deps, value_date=value_date)
    req_greeks = ['pv', 'cmdelta', 'cmgamma', 'cmvega', 'theta']
    output = {}
    for shift in scens[2]:
        mkt_data = cmq_inst_risk.generate_scen(base_mkt, scens[0], scens[1], curve_tenor = 'ALL', shift_size = shift, shift_type = scens[3])
        re = cmq_risk_engine.CMQRiskEngine(book, mkt_data, req_greeks)
        re.run_risk()
        output[shift] = copy.deepcopy(re.book_risks)
        for greek in ['cmdelta', 'cmvega', 'cmgamma']:
            output[shift][greek] = output[shift][greek][scens[1]]
    df = pd.DataFrame.from_dict(output, orient='index')
    return df

