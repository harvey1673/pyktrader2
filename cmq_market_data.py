# -*- coding:utf-8 -*-
import cmq_crv_defn
import pandas as pd
import dbaccess
import misc
import workdays
import datetime
from dateutil.relativedelta import relativedelta

IR_Exclusion_Tenors = ['2W', '4M', '5M', '7M', '8M', '9M', '10M', '11M']

def comfwd_db_loader(market_data, fwd_index, dep_tenors = []):
    curve_info = cmq_crv_defn.COM_Curve_Map[fwd_index]
    prod_code = curve_info['instID']
    mkt_db = market_data['market_db']
    mdate = market_data['market_date']
    mkey = market_data['market_key']
    cnx = dbaccess.connect(**mkt_db)
    df = dbaccess.load_fut_curve(cnx, prod_code, mkey)
    if len(df) == 0:
        print "COMFwd data is not available for %s on %s" % (fwd_index, mkey)
    df['date'] = df['instID'].apply(lambda x: misc.inst2cont(x))
    df['expiry'] = df['instID'].apply(lambda x: misc.contract_expiry(x, []))
    df = df[pd.to_datetime(df.date).dt.month.isin(curve_info['active_mths'])]
    return df[['date', 'expiry', 'close']].values.tolist()

def comvol_db_loader(market_data, fwd_index, dep_tenors = []):
    curve_info = cmq_crv_defn.COM_Curve_Map[fwd_index]
    prod_code = curve_info['instID']
    mkt_db = market_data['market_db']
    mkey = market_data['market_key']
    cnx = dbaccess.connect(**mkt_db)
    vol_tbl = dbaccess.load_cmvol_curve(cnx, prod_code, mkey)
    if len(vol_tbl) == 0:
        print "COMVol data is not available for %s on %s" % (prod_code, mkey)
        return {}
    vol_tbl = vol_tbl.reset_index()
    vol_dict = {}
    for field in ['COMVolATM', 'COMVolV10', 'COMVolV25', 'COMVolV75', 'COMVolV90']:
        vol_dict[field] = [[x, y, z] for x, y, z \
                               in zip(vol_tbl['tenor_label'], vol_tbl['expiry_date'], vol_tbl[field])]
    return vol_dict

def comdv_db_loader(market_data, fwd_index, dep_tenors = [], spd_key = 'DV1'):
    mkt_db = market_data['market_db']
    mdate = market_data['market_date']
    mkey = market_data['market_key']
    cnx = dbaccess.connect(**mkt_db)
    df = dbaccess.load_cmdv_curve(cnx, fwd_index, spd_key, mkey)
    if len(df) > 0 and isinstance(df['date'][0], basestring):
        df['date'] = df['date'].apply(lambda x: datetime.datetime.strptime(x,"%Y-%m-%d").date())
        df['expiry'] = df['expiry'].apply(lambda x: datetime.datetime.strptime(x, "%Y-%m-%d").date())
    return df[['date', 'expiry', 'vol']].values.tolist()

def comfix_db_loader(market_data, spotID, dep_tenors = []):
    cnx = dbaccess.connect(**dbaccess.dbconfig)
    df = dbaccess.load_daily_data_to_df(cnx, 'spot_daily', spotID, min(dep_tenors), max(dep_tenors), index_col = None, field='spotID')
    if len(df) > 0 and isinstance(df['date'][0], basestring):
        df['date'] = df['date'].apply(lambda x: datetime.datetime.strptime(x,"%Y-%m-%d %H:%M:%S").date())
    return df[['date', 'close']].values.tolist()

def fxfwd_db_loader(market_data, fwd_index, dep_tenors = []):
    curve_info = cmq_crv_defn.FX_Curve_Map[fwd_index]
    mkey = market_data['market_key']
    mdate = market_data['market_date']
    mkt_db = market_data['market_db']
    cnx = dbaccess.connect(**mkt_db)
    df = dbaccess.load_fut_curve(cnx, fwd_index, mkey, dbtable = 'fx_daily', field = 'ccy')
    if len(df) == 0:
        print "FXFwd data is not available for %s on %s" % (fwd_index, mdate)
    df['expiry'] = df['tenor'].apply(lambda x: misc.day_shift(mdate, x.lower()))
    return df[['tenor', 'expiry', 'rate']].values.tolist()

def fxvol_db_loader(market_data, fwd_index, dep_tenors = []):
    pass

def fxfix_db_loader(market_data, fwd_index, dep_tenors = []):
    pass

def ircurve_db_loader(market_data, fwd_index, dep_tenors = []):
    curve_info = cmq_crv_defn.IR_Curve_Map[fwd_index]
    ir_idx = curve_info['ir_index']
    mdate = market_data['market_date']
    mkey = market_data['market_key']
    mkt_db = market_data['market_db']
    cnx = dbaccess.connect(**mkt_db)
    df = dbaccess.load_fut_curve(cnx, ir_idx, mkey, dbtable='ir_daily', field='ir_index')
    if len(df) == 0:
        print "IRCurve data is not available for %s on %s" % (ir_idx, mkey)
    df = df[~df['tenor'].isin(IR_Exclusion_Tenors)]
    df['expiry'] = df['tenor'].apply(lambda x: misc.day_shift(mdate, x.lower()))
    df['rate'] = df['rate']/100.0
    return df[['tenor', 'expiry', 'rate']].values.tolist()

def process_BOM(market_data, mkt_deps):
    mdate = market_data['market_date']
    if 'COMFwd' not in market_data:
        return
    for fwd_idx in market_data['COMFwd']:
        crv_info = cmq_crv_defn.COM_Curve_Map[fwd_idx]
        if crv_info['exch'] in ['SGX', 'LME', 'NYM']:
            fwd_quotes = market_data['COMFwd'][fwd_idx]
            if (fwd_quotes[0][0] < mdate):
                spotID = crv_info['spotID']
                if spotID not in mkt_deps['COMFix']:
                    continue
                hols = getattr(misc, crv_info['calendar'] + '_Holidays')
                bzdays = workdays.networkdays(fwd_quotes[0][0], fwd_quotes[0][1], hols)
                spotID = crv_info['spotID']
                past_fix = [ quote[1] for quote in market_data['COMFix'][spotID] if quote[0] <= mdate]
                if bzdays > len(past_fix):
                    fwd_quotes[0][2] = (fwd_quotes[0][2] * bzdays - sum(past_fix))/(bzdays - len(past_fix))
                else:
                    fwd_quotes[0][2] = 0

def load_market_data(mkt_deps, value_date = datetime.date.today(), region = 'EOD', is_eod = True):
    if region == 'EOD':
        mkt_db = dbaccess.dbconfig
        if is_eod:
            market_date = value_date
        else:
            market_date = workdays.workday(value_date, -1)
        market_key = market_date.strftime('%Y-%m-%d')
    else:
        mkt_db = dbaccess.mktsnap_dbconfig
        market_date = value_date
        market_key = market_date.strftime('%Y-%m-%d') + '_' + region
    market_data = {'value_date': value_date, 'market_date': market_date, 'market_key': market_key, 'market_db': mkt_db,}
    for field in mkt_deps:
        if field == 'COMFwd':
            mkt_loader = comfwd_db_loader
        elif field == 'COMVolATM':
            for f in cmq_crv_defn.COMVOL_fields[1:]:
                market_data[f] = {}
            mkt_loader = comvol_db_loader
        elif field == 'COMFix':
            mkt_loader = comfix_db_loader
        elif field == 'FXFwd':
            mkt_loader = fxfwd_db_loader
        elif field == 'FXVolATM':
            for f in cmq_crv_defn.FXVOL_fields[1:]:
                market_data[f] = {}
            mkt_loader = fxvol_db_loader
        elif field == 'FXFix':
            mkt_loader = fxfix_db_loader
        elif field == 'IRCurve':
            mkt_loader = ircurve_db_loader
        elif field[:5] == 'COMDV':
            mkt_loader = comdv_db_loader
        else:
            continue
        market_data[field] = {}
        for crv_idx in mkt_deps[field]:
            if field == 'IRCurve':
                if crv_idx == 'cny_disc':
                    flat_rate = 0.045
                    market_data[field][crv_idx] = flat_ir_curve(market_date, flat_rate)
                    continue
            if field == 'COMVolATM':
                output = mkt_loader(market_data, crv_idx, mkt_deps[field][crv_idx])
                for vol_field in cmq_crv_defn.COMVOL_fields:
                    if len(output) == 0:
                        market_data[vol_field][crv_idx] = {}
                    else:
                        market_data[vol_field][crv_idx] = output[vol_field]
            elif field[:5] == 'COMDV':
                market_data[field][crv_idx] = mkt_loader(market_data, crv_idx, mkt_deps[field][crv_idx], field[3:])
            else:
                market_data[field][crv_idx] = mkt_loader(market_data, crv_idx, mkt_deps[field][crv_idx])
    process_BOM(market_data, mkt_deps)
    return market_data

def flat_ir_curve(tday, rate):
    tenors = ['1W', '2W', '1M', '3M', '6M', '9M', '1Y', '3Y']
    output = []
    for ten in tenors:
        data = [ten, misc.day_shift(tday, ten.lower()), rate]
        output.append(data)
    return output

if __name__ == '__main__':
    pass