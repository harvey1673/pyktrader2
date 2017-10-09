# -*- coding:utf-8 -*-
import json
import misc
import workdays
import datetime
from dateutil.relativedelta import relativedelta
COM_Curve_Map = {
    'SGXIRO': {'instID': 'fef', 'exch': 'SGX', 'calendar': 'PLIO',
                'parent_curve': '', 'spotID': 'tsi_io62', 'vol_index': 'SGXIRO',},
    'SHFERB': {'instID': 'rb', 'exch': 'SHFE', 'calendar': 'CHN',
                'parent_curve': '', 'spotID': 'rb', 'vol_index': 'SHFERB',},
    'SHFEHC': {'instID': 'hc', 'exch': 'SHFE', 'calendar': 'CHN',
                'parent_curve': '', 'spotID': 'hc', 'vol_index': 'SHFEHC',},
    'DCEIRO': {'instID': 'i', 'exch': 'DCE', 'calendar': 'CHN',
                'parent_curve': '', 'spotID': 'i', 'vol_index': 'DCEIRO',},
}

FX_Curve_Map = {
    'USDCNY': {'ccy': 'USD/CNY', 'src': 'PriceStore', 'calendar': 'USDCNY',
                'parent_curve': '', 'fx_spot': '', 'vol_index': 'USDCNY',},
}

IR_Curve_Map = {
    'usd_disc': {'ccy': 'USD', 'src': 'BBA-LIBOR', 'calendar': 'USD',
                 'ir_index': 'USD3M',
                'parent_curve': '', 'ir_spot': '', 'swn_curve': 'usd3m', },
}

Market_Input_Struct = ['COMFwd', 'COMFix', 'COMVolATM', 'COMVolV10', 'COMVolV25', 'COMVolV75', 'COMVolV90', \
                     'FXFwd', 'FXFix', 'FXVolATM', 'FXVolRR25', 'FXVolRR10', 'FXVolFLY25', 'FXVolFLY10', \
                     'IRCurve', 'IRFix', 'IRSWNVol']

COMVOL_fields = ['COMVolATM', 'COMVolV10', 'COMVolV25', 'COMVolV75', 'COMVolV90']
FXVOL_fields = ['FXVolATM', 'FXVolV10', 'FXVolV25', 'FXVolV75', 'FXVolV90']

def extract_vol_mark(vol_index, market_data, vol_fields = COMVOL_fields):
    volmark = dict([(field, []) for field in ['expiry'] + vol_fields])
    for idx, v_quote in enumerate(market_data[vol_fields[0]][vol_index]):
        volmark['expiry'].append(v_quote[1])
        for field in vol_fields:
            volmark[field].append(market_data[field][vol_index][idx][2])
    return volmark

def lookup_vol_mark(vol_index, market_data, vol_tenor, vol_fields = COMVOL_fields):
    volmark = dict([(field, 0.0) for field in ['expiry'] + vol_fields])
    for idx, v_quote in enumerate(market_data[vol_fields[0]][vol_index]):
        if v_quote[1] >= vol_tenor:
            volmark['expiry'] = v_quote[1]
            for field in vol_fields:
                volmark[field] = market_data[field][vol_index][idx][2]
            break
    return volmark

def tenor_expiry(exch, product, tenor, rolldays = 0, field = 'fwd'):
    expiry = tenor
    if exch == 'DCE' or exch == 'CZCE':
        while expiry.month not in [1, 5, 9]:
            expiry = expiry + relativedelta(months=1)
        expiry = workdays.workday(expiry - datetime.timedelta(days=1), 10 - rolldays, misc.CHN_Holidays)
    elif exch == 'CFFEX':
        while product in ['T', 'TF'] and expiry.month not in [3, 6, 9, 12]:
            expiry = expiry + relativedelta(months=1)
        wkday = expiry.weekday()
        expiry = expiry + datetime.timedelta(days=13 + (11 - wkday) % 7)
        expiry = workdays.workday(expiry, 1 - rolldays, misc.CHN_Holidays)
    elif exch == 'SHFE':
        if product in ['hc', 'rb']:
            while expiry.month not in [1, 5, 10]:
                expiry = expiry + relativedelta(months=1)
        else:
            while expiry.month not in [1, 5, 9]:
                expiry = expiry + relativedelta(months=1)
        expiry = expiry.replace(day=14)
        expiry = workdays.workday(expiry, 1 - rolldays, misc.CHN_Holidays)
    elif exch == 'SGX' or exch == 'OTC':
        expiry = expiry + relativedelta(months=1)
        expiry = workdays.workday(expiry, -1 - rolldays, misc.PLIO_Holidays)
    return expiry

def curve_expiry(exch, product, start_date, end_date, rolldays = 0, field = 'fwd'):
    cont_date = start_date.replace(day = 1)
    expiry = cont_date
    cont_list = []
    while expiry < end_date:
        expiry = tenor_expiry(exch, product, cont_date, rolldays, field)
        if expiry >= start_date:
            cont_list.append((cont_date, expiry))
        cont_date = cont_date + relativedelta(months = 1)
    return cont_list

if __name__ == '__main__':
    pass
