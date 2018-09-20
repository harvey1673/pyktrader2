# -*- coding:utf-8 -*-
import json
import misc
import workdays
import datetime
from dateutil.relativedelta import relativedelta
COM_Curve_Map = {
    'SGXIRO': {'instID': 'fef', 'exch': 'SGX', 'calendar': 'PLIO', 'ccy': 'USD', \
                'active_mths': range(1, 13), 'roll_rule': '-0d',\
                'parent_curve': '', 'spotID': 'plt_io62', 'vol_index': 'SGXIRO',\
                '': '', },
    'PLATTS62': {'instID': 'fef', 'exch': 'SGX', 'calendar': 'PLIO', 'ccy': 'USD', \
                'active_mths': range(1, 13), 'roll_rule': '-0d',\
                'parent_curve': '', 'spotID': 'plt_io62', 'vol_index': 'SGXIRO',\
                '': '', },
    'SGXIOLP': {'instID': 'iolp', 'exch': 'SGX', 'calendar': 'PLIO', 'ccy': 'USD', \
               'active_mths': range(1, 13), 'roll_rule': '-0d',\
               'parent_curve': '', 'spotID': 'plt_lp', 'vol_index': 'SGXIROLP', \
               '': '', },
    'SHFERB': {'instID': 'rb', 'exch': 'SHFE', 'calendar': 'CHN', 'ccy': 'CNY', \
                'active_mths': [1, 5, 10], 'roll_rule': '-35b',\
                'parent_curve': '', 'spotID': 'rb', 'vol_index': 'SHFERB',},
    'SHFEHRC': {'instID': 'hc', 'exch': 'SHFE', 'calendar': 'CHN', 'ccy': 'CNY', \
                'active_mths': [1, 5, 10], 'roll_rule': '-35b',\
                'parent_curve': '', 'spotID': 'hc', 'vol_index': 'SHFEHRC',},
    'DCEIOE': {'instID': 'i', 'exch': 'DCE', 'calendar': 'CHN','ccy': 'CNY', \
                'active_mths': [1, 5, 9], 'roll_rule': '-35b',
                'parent_curve': '', 'spotID': 'i', 'vol_index': 'DCEIOE',},
    'DCECOK': {'instID': 'j', 'exch': 'DCE', 'calendar': 'CHN', 'ccy': 'CNY', \
                'active_mths': [1, 5, 9], 'roll_rule': '-35b',
                'parent_curve': '', 'spotID': 'j', 'vol_index': 'DCECOK',},
    'LMESCR': {'instID': 'lsc', 'exch': 'LME', 'calendar': 'PLIO', 'ccy': 'USD', \
                'active_mths': range(1,13), 'roll_rule': '-0d',
                'parent_curve': '', 'spotID': 'tsi_scrap', 'vol_index': 'LMESCR',},
    'SGXIAC': {'instID': 'iac', 'exch': 'SGX', 'calendar': 'PLIO', 'ccy': 'USD', \
                'active_mths': range(1, 13), 'roll_rule': '-0d',\
                'parent_curve': '', 'spotID': 'PLSQ1032 Index', 'vol_index': 'SGXIRO',\
                '': '', },
}

FX_Curve_Map = {
    'USD/CNY': {'ccy': 'USD/CNY', 'src': 'PriceStore', 'calendar': 'USDCNY',
                'parent_curve': '', 'fx_spot': '', 'vol_index': 'USDCNY',},
}

IR_Curve_Map = {
    'usd_disc': {'ccy': 'USD', 'src': 'BBA-LIBOR', 'calendar': 'USD',
                 'ir_index': 'USD3M',
                'parent_curve': '', 'ir_spot': '', 'swn_curve': 'usd3m', },
    'cny_disc': {'ccy': 'CNY', 'src': 'PBOC', 'calendar': 'CHN',
                 'ir_index': 'SHIBOR3M',
                'parent_curve': '', 'ir_spot': '', 'swn_curve': 'shibor3m', },
}

Market_Input_Struct = ['COMFwd', 'COMFix', 'COMVolATM', 'COMVolV10', 'COMVolV25', 'COMVolV75', 'COMVolV90', \
                     'FXFwd', 'FXFix', 'FXVolATM', 'FXVolRR25', 'FXVolRR10', 'FXVolFLY25', 'FXVolFLY10', \
                     'IRCurve', 'IRFix', 'IRSWNVol']

COMVOL_fields = ['COMVolATM', 'COMVolV10', 'COMVolV25', 'COMVolV75', 'COMVolV90']
FXVOL_fields = ['FXVolATM', 'FXVolV10', 'FXVolV25', 'FXVolV75', 'FXVolV90']
COMDV_fields = ['COMDV1', 'COMDV2', 'COMDV3', 'COMDV4']

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

def lookup_fix_mark(spot_id, market_data, fix_date):
    fix_quotes = market_data['COMFix'][spot_id]
    out = None
    for q in fix_quotes:
        out = q[1]
        if q[0] == fix_date:
            break
    return out

if __name__ == '__main__':
    pass