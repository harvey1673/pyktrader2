# -*- coding: utf-8 -*-

import urllib
import json
import datetime
import misc
import sec_bits
import pandas as pd

PROXIES = {'http':'http://%s:%s@10.252.22.102:4200' % (sec_bits.PROXY_CREDENTIALS['user'], sec_bits.PROXY_CREDENTIALS['passwd']),
           'https':'https://%s:%s@10.252.22.102:4200' % (sec_bits.PROXY_CREDENTIALS['user'], sec_bits.PROXY_CREDENTIALS['passwd'])}

def get_fut_quotes(inst_list, proxies = PROXIES):
    index_list = []
    exch_list = []
    for idx in inst_list:
        inst = idx
        exch = misc.inst2exch(idx)
        if exch in ['DCE', 'SHFE']:
            inst = idx.upper()
        elif exch in ['CZCE']:
            year = idx[-3]
            if int(year) < 8:
                year = '2' + year
            else:
                year = '1' + year
            month = idx[-2:]
            inst = idx[-3] + year + month
        elif exch in ['CFFEX',]:
            inst = "CFF_RE_" + idx
        index_list.append(inst)
        exch_list.append(exch)
    url = "http://hq.sinajs.cn/list=%s" % ','.join(index_list)
    raw = urllib.urlopen(url, proxies = proxies).read()
    raw = raw.split('\n')
    result = dict()
    for instID, exch, raw_data in zip(inst_list, exch_list, raw):
        if len(raw_data) == 0:
            continue
        quotes = raw_data.split(',')
        if exch in ['CFFEX',]:
            tick_time = quotes[37].split(':')
            tick_id = ((int(tick_time[0]) + 6) % 24) * 10000 + int(tick_time[1])*100 + int(tick_time[2])
            data = {
                'tick_id': tick_id * 10,
                'open': float(quotes[0]),
                'high': float(quotes[1]),
                'low': float(quotes[2]),
                'close': float(quotes[3]),
                'bidPrice1': float(quotes[7]),
                'askPrice1': float(quotes[7]),
                'price': float(quotes[7]),
                'settlement': float(quotes[8]),
                'bidVol1': 0,
                'askVol1': 0,
                'openInterest': int(quotes[6]),
                'volume': int(quotes[4]),
                'date': quotes[36],
            }
        else:
            tick_id = int(quotes[1])
            tick_id = ((int(tick_id/10000) + 6) % 24) * 10000 + (tick_id % 10000)
            data = {
                        'tick_id': tick_id * 10,
                        'open': float(quotes[2]),
                        'high': float(quotes[3]),
                        'low': float(quotes[4]),
                        'prev_close': float(quotes[5]),
                        'bidPrice1': float(quotes[6]),
                        'askPrice1': float(quotes[7]),
                        'price': float(quotes[8]),
                        'prev_settlement': float(quotes[9]),
                        'bidVol1': int(quotes[11]),
                        'askVol1': int(quotes[12]),
                        'openInterest': int(quotes[13]),
                        'volume': int(quotes[14]),
                        'date': quotes[17],
                        }
        result[instID] = data
    return result

def get_fut_hist(instID, freq = 'd', proxies = PROXIES):
    exch = misc.inst2exch(instID)
    if exch in ['DCE', 'SHFE']:
        ticker = instID.upper()
    elif exch in ['CZCE']:
        year = instID[-3]
        if int(year) < 8:
            year = '2' + year
        else:
            year = '1' + year
        month = instID[-2:]
        ticker = instID[-3] + year + month
    elif exch in ['CFFEX', ]:
        ticker = "CFF_RE_" + instID
    # choose daily or 5 mins historical data
    if freq[-1] == 'd':
        url = 'http://stock2.finance.sina.com.cn/futures/api/json.php/IndexService.getInnerFuturesDailyKLine?symbol=%s' % ticker
        date_col = 'date'
    elif freq[-1] == 'm':
        if int(freq[:-1]) in [5, 15, 30, 60]:
            url = 'http://stock2.finance.sina.com.cn/futures/api/json.php/IndexService.getInnerFuturesMiniKLine%s?symbol=%s' % (freq, ticker)
            date_col = 'datetime'
        else:
            return
    else:
        return []
    raw = urllib.urlopen(url, proxies = proxies).read()
    result = json.loads(raw)
    df = pd.DataFrame(result, columns=['datetime','open', 'high','low','close','volume'])
    if date_col == 'date':
        df[date_col] = df[date_col].apply(lambda x: datetime.datetime.strptime(x, "%Y-%m-%d").date())
    else:
        df[date_col] = df[date_col].apply(lambda x: datetime.datetime.strptime(x, "%Y-%m-%d %H:%M:%S").date())
    for col in ['open', 'high','low','close']:
        df[col] = df[col].apply(lambda x: float(x))
    df['volume'] = df['volume'].apply(lambda x: int(x))
    df['exch'] = exch
    df = df.set_index([date_col])
    return df