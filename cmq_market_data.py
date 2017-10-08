# -*- coding:utf-8 -*-
import cmq_crv_defn
import dbaccess
import datetime
import misc

IR_Exclusion_Tenors = ['2W', '4M', '5M', '7M', '8M', '9M', '10M', '11M']

def comfwd_db_loader(market_data, fwd_index, dep_tenors = []):
    curve_info = cmq_crv_defn.COM_Curve_Map[fwd_index]
    prod_code = curve_info['instID']
    vdate = market_data['value_date']
    cnx = dbaccess.connect(**dbaccess.dbconfig)
    df = dbaccess.load_fut_curve(cnx, prod_code, vdate)
    df['date'] = df['instID'].apply(lambda x: misc.inst2cont(x))
    df['expiry'] = df['instID'].apply(lambda x: misc.contract_expiry(x, []))
    return df[['date', 'expiry', 'close']].values.tolist()

def comvol_db_loader(market_data, fwd_index, dep_tenors = []):
    curve_info = cmq_crv_defn.COM_Curve_Map[fwd_index]
    vol_index = curve_info['vol_index']
    exch = curve_info['exch']
    prod_code = curve_info['instID']
    vdate = market_data['value_date']
    #cnx = dbaccess.connect(**dbaccess.dbconfig)
    #df = dbaccess.load_vol_curve(cnx, prod_code, vdate)
    #for field in ['ATM', 'V90', 'V75', 'V25', 'V10']:
    #    market_data['COMVol'+field][vol_index] = df[['expiry', field.lower(), 'instID']].values.tolist()
    expiries = [cmq_crv_defn.tenor_expiry(exch, prod_code, tenor, field = 'vol') for tenor in dep_tenors]
    output = {}
    for field in ['ATM', 'V90', 'V75', 'V25', 'V10']:
        if field == 'ATM':
            output['COMVol' + field] = [[tenor, expiry, 0.42] for tenor, expiry in zip(dep_tenors, expiries)]
        else:
            output['COMVol' + field] = [[tenor, expiry, 0.0] for tenor, expiry in zip(dep_tenors, expiries)]
    return output

def comfix_db_loader(market_data, spotID, dep_tenors = []):
    cnx = dbaccess.connect(**dbaccess.dbconfig)
    df = dbaccess.load_daily_data_to_df(cnx, 'spot_daily', spotID, min(dep_tenors), max(dep_tenors), index_col = None, field='spotID')
    if len(df) > 0 and isinstance(df['date'][0], basestring):
        df['date'] = df['date'].apply(lambda x: datetime.datetime.strptime(x,"%Y-%m-%d %H:%M:%S").date())
    return df[['date', 'close']].values.tolist()

def fxfwd_db_loader(market_data, fwd_index, dep_tenors = []):
    curve_info = cmq_crv_defn.FX_Curve_Map[fwd_index]
    vdate = market_data['value_date']
    cnx = dbaccess.connect(**dbaccess.dbconfig)
    df = dbaccess.load_fut_curve(cnx, fwd_index, vdate, dbtable = 'fx_daily', field = 'ccy')
    df['expiry'] = df['tenor'].apply(lambda x: misc.day_shift(vdate, x.lower()))
    return df[['tenor', 'expiry', 'rate']].values.tolist()

def fxvol_db_loader(market_data, fwd_index, dep_tenors = []):
    pass

def fxfix_db_loader(market_data, fwd_index, dep_tenors = []):
    pass

def ircurve_db_loader(market_data, fwd_index, dep_tenors = []):
    curve_info = cmq_crv_defn.IR_Curve_Map[fwd_index]
    ir_idx = curve_info['ir_index']
    vdate = market_data['value_date']
    cnx = dbaccess.connect(**dbaccess.dbconfig)
    df = dbaccess.load_fut_curve(cnx, ir_idx, vdate, dbtable='ir_daily', field='ir_index')
    df = df[~df['tenor'].isin(IR_Exclusion_Tenors)]
    df['expiry'] = df['tenor'].apply(lambda x: misc.day_shift(vdate, x.lower()))
    df['rate'] = df['rate']/100.0
    return df[['tenor', 'expiry', 'rate']].values.tolist()

def load_market_data(mkt_deps, value_date = datetime.date.today(), region = 'AP'):
    market_data = {'value_date': value_date, 'region': region}
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
        else:
            continue
        market_data[field] = {}
        for crv_idx in mkt_deps[field]:
            if field == 'COMVolATM':
                output = mkt_loader(market_data, crv_idx, mkt_deps[field][crv_idx])
                for vol_field in cmq_crv_defn.COMVOL_fields:
                    market_data[vol_field][crv_idx] = output[vol_field]
            else:
                market_data[field][crv_idx] = mkt_loader(market_data, crv_idx, mkt_deps[field][crv_idx])
    return market_data


if __name__ == '__main__':
    pass
