import datetime
import cmq_market_data
import cmq_book
from dateutil.relativedelta import relativedelta

def generate_ee_strip():
    market_date = datetime.date(2017,10, 13)
    value_date = datetime.date(2017, 10, 18)
    otype = 'C'
    strike = 75.0
    fwd_index = 'SGXIRO'
    accrual =  'act252'
    need_disc = True
    start_cont = datetime.date(2018,3,1)
    market_data = {'value_date': value_date, 'market_date': market_date, 'COMFwd': {}, \
                   'COMVolATM': {}, 'COMVolV10': {}, 'COMVolV25': {}, 'COMVolV75': {}, 'COMVolV90': {}, \
                   'IRCurve': {}, }
    market_data['COMFwd'][fwd_index] = cmq_market_data.comfwd_db_loader(market_data, fwd_index)
    vol_dict = cmq_market_data.comvol_db_loader(market_data, fwd_index)
    back_vol = {'COMVolATM': 0.30, 'COMVolV10': 0.0,  'COMVolV25': 0.0, 'COMVolV75': 0.0, 'COMVolV90': 0.0}
    for vol_field in ['COMVolATM', 'COMVolV10', 'COMVolV25', 'COMVolV75', 'COMVolV90']:
        market_data[vol_field][fwd_index] = vol_dict[vol_field]
        last_q = market_data[vol_field][fwd_index][-1]
        for i in range(12):
            cont_mth = last_q[0] + relativedelta(months = i)
            cont_exp = cont_mth + relativedelta(months = 1) - datetime.timedelta(days = 1)
            market_data[vol_field][fwd_index].append([cont_mth, cont_exp, back_vol[vol_field]])
    market_data['IRCurve']['usd_disc'] = cmq_market_data.ircurve_db_loader(market_data, 'usd_disc')
    model_settings = {'alpha': 1.8, 'beta': 1.2}
    deal = cmq_book.CMQDeal({'positions': []})
    for mth in range(12):
        contract = start_cont + relativedelta(months=mth)
        expiry = contract - relativedelta(months=3)
        trade_data = {'inst_type': "ComEuroOption",
                    'strike': strike,
                    'fwd_index': fwd_index,
                    'contract': contract,
                    'accrual': accrual,
                    'otype': otype,
                    'end': expiry,
                    'need_disc': need_disc}
        deal.add_instrument(trade_data, 1)
    for inst, pos in deal.positions:
        inst.set_model_settings(model_settings)
    test_book = cmq_book.CMQBook({})
    test_book.book_deal(deal)
    return test_book, market_data
