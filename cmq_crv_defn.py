# -*- coding:utf-8 -*-
import json
import misc
import workdays
import datetime
from dateutil.relativedelta import relativedelta
COM_Curve_Map = {
    'SGX_IO': {'instID': 'fef', 'exch': 'SGX', 'calendar': 'PLIO',
                'parent_curve': '', 'spotID': 'tsi62',},
    'SHFE_RB': {'instID': 'rb', 'exch': 'SHFE', 'calendar': 'CHN',
                'parent_curve': '', 'spotID': 'rb',},
    'SHFE_HRC': {'instID': 'hc', 'exch': 'SHFE', 'calendar': 'CHN',
                'parent_curve': '', 'spotID': 'hc',},
    'DCE_IO': {'instID': 'i', 'exch': 'DCE', 'calendar': 'CHN',
                'parent_curve': '', 'spotID': 'i',},
}

def curve_expiry(exch, product, start_date, end_date, rolldays = 0):
    cont_date = start_date.replace(day = 1)
    expiry = cont_date
    cont_list = []
    while expiry < end_date:
        if exch == 'DCE' or exch == 'CZCE':
            expiry = workdays.workday(cont_date - datetime.timedelta(days=1), 10 - rolldays, misc.CHN_Holidays)
        elif exch == 'CFFEX':
            wkday = cont_date.weekday()
            expiry = cont_date + datetime.timedelta(days=13 + (11 - wkday) % 7)
            expiry = workdays.workday(expiry, 1 - rolldays, misc.CHN_Holidays)
        elif exch == 'SHFE':
            expiry = cont_date.replace(day = 14)
            expiry = workdays.workday(expiry, 1 - rolldays, misc.CHN_Holidays)
        elif exch == 'SGX' or exch == 'OTC':
            expiry = cont_date + relativedelta( months = 1 )
            expiry = workdays.workday(expiry, -1-rolldays, misc.PLIO_Holidays)
        if expiry >= start_date:
            cont_list.append((cont_date, expiry))
        cont_date = cont_date + relativedelta(months = 1)
    return cont_list

