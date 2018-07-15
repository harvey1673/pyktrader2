# -*- coding: utf-8 -*-
import web_sina_api
import openpyxl
import datetime
import pandas as pd
import misc
import dbaccess

live_asset_list = [('i', 'DCE', [1, 5, 9]), ('j', 'DCE', [1, 5, 9]), ('jm', 'DCE', [1, 5, 9]), ('rb',"SHFE", [1, 5, 10]), ('hc', "SHFE", [1, 5, 10])]

all_asset_list = {  'fut_daily': ['fef', 'i', 'rb', 'hc', 'j',  'lsc',  'iolp', 'iac', 'jm', ], \
                    'fx_daily': ['USD/CNY',], \
                    'ir_daily': ['USD3M'],\
                    'cmvol_daily': ['fef', 'i', 'rb', 'hc'],\
                    }

option_markets = ['rb', 'hc', 'i', 'fef']

def snap_curr_market():
    cont_list = {}
    all_conts = []
    tday = datetime.date.today()
    for asset, exch, cont_mth in live_asset_list:
        conts = misc.contract_range(asset, exch, cont_mth, tday, tday)
        cont_list[asset] = [ c for c in conts if misc.contract_expiry(c) >= tday ]
        all_conts += cont_list[asset]
    res = web_sina_api.get_fut_quotes(all_conts)
    return cont_list, res

def copy_eod_market(tday, tag, src_db = dbaccess.dbconfig, dst_db = dbaccess.mktsnap_dbconfig):
    for table_name in all_asset_list:
        src_conn = dbaccess.connect(**src_db)
        stmt = "select * from {table} where date like'{date}%'".format(table = table_name,date = tday.strftime('%Y-%m-%d'))
        df = pd.read_sql(stmt, src_conn)
        src_conn.close()
        df['date'] = tag
        dst_conn = dbaccess.connect(**dst_db)
        df.to_sql(table_name, dst_conn, flavor='sqlite', if_exists='append', index = False)
        dst_conn.close()

def save_xlmkt_to_db(xlfile, tag):
    comm_curves = 9
    fx_curves = 2
    ir_curves = 1
    conn = dbaccess.connect(**dbaccess.mktsnap_dbconfig)
    # loading commod curves
    opt_df = pd.DataFrame()
    fut_df = pd.DataFrame()
    for idx in range(comm_curves):
        df = pd.read_excel(xlfile, sheetname="COMM", header = 1, index_col = None, parse_cols = range(idx * 13, idx * 13 + 12)).dropna()
        df['date'] = tag
        fdf = df[['instID', 'exch', 'date', 'COMFwd']]
        fdf.rename(columns={'COMFwd': 'close'}, inplace = True)
        fut_df = fut_df.append(fdf)
        if df['product_code'][0] in option_markets:
            for delta, col_name in zip([0.5, 0.1, 0.25, -0.25, -0.1], ['COMVolATM', 'COMVolV10', 'COMVolV25', 'COMVolV75', 'COMVolV90']):
                xdf = df[['date', 'tenor_label', col_name, 'expiry_date', 'exch', 'product_code']]
                xdf.rename(columns={col_name: 'vol'}, inplace = True)
                if (delta != 0.5):
                    xdf['vol'] = xdf['vol'] + df['COMVolATM']
                xdf['delta'] = delta
                opt_df = opt_df.append(xdf)
    fut_df.to_sql('fut_daily', conn, flavor='sqlite', if_exists='append', index=False)
    opt_df.to_sql('cmvol_daily', conn, flavor='sqlite', if_exists='append', index=False)

    fx_df = pd.DataFrame()
    for idx in range(fx_curves):
        df = pd.read_excel(xlfile, sheetname="FX", header=1, index_col=None, parse_cols=range(idx * 5, idx * 5 + 4)).dropna()
        df['date'] = tag
        df['src'] = xlfile
        cdf = df[['date', 'ccy', 'tenor', 'rate', 'src']]
        fx_df = fx_df.append(cdf)
    fx_df.to_sql('fx_daily', conn, flavor='sqlite', if_exists='append', index=False)

    ir_df = pd.DataFrame()
    for idx in range(ir_curves):
        df = pd.read_excel(xlfile, sheetname="IR", header=1, index_col=None, parse_cols=range(idx * 4, idx * 4 + 3)).dropna()
        df['date'] = tag
        df['src'] = xlfile
        rdf = df[['date', 'tenor', 'rate', 'ir_index', 'src']]
        ir_df = ir_df.append(rdf)
    ir_df.to_sql('ir_daily', conn, flavor='sqlite', if_exists='append', index=False)

def load_db_to_xlmkt(tag, xlfile):
    writer = pd.ExcelWriter(xlfile)
    cnx = dbaccess.connect(**dbaccess.mktsnap_dbconfig)
    prod_map = dict([(prod, cont) for (prod, exch, cont) in live_asset_list])
    xl_structure = {"fut_daily": "COMM", "fx_daily": "FX", "ir_daily": "IR"}
    for tab_key in ['fut_daily', 'fx_daily', 'ir_daily']:
        for idx, prod_code in enumerate(all_asset_list[tab_key]):
            if tab_key == 'fut_daily':
                df = dbaccess.load_fut_curve(cnx, prod_code, tag)
                df['product_code'] = prod_code
                df['tenor_label'] = df['instID'].apply(lambda x: misc.inst2cont(x))
                df['expiry_date'] = df['instID'].apply(lambda x: misc.contract_expiry(x, []))
                df['exch'] = misc.prod2exch(prod_code)
                df.rename(columns = {'close': 'COMFwd'}, inplace = True)
                if prod_code in prod_map:
                    df = df[pd.to_datetime(df['tenor_label']).dt.month.isin(prod_map[prod_code])]
                if prod_code in option_markets:
                    vol_tbl = dbaccess.load_cmvol_curve(cnx, prod_code, tag)
                    vol_tbl = vol_tbl.set_index('tenor_label')
                    vol_tbl.drop(['expiry_date'], axis = 1,inplace = True)
                    df = df.set_index('tenor_label')
                    df = pd.concat([df, vol_tbl], axis = 1)
                    df = df.reset_index()
                    df.rename(columns = {'index': 'tenor_label'}, inplace = True)
                else:
                    for key in ['COMVolATM', 'COMVolV90', 'COMVolV75', 'COMVolV25', 'COMVolV10']:
                        if key == 'COMVolATM':
                            df[key] = 0.2
                        else:
                            df[key] = 0.0
                df = df[['product_code', 'instID', 'exch', 'tenor_label', 'expiry_date', 'COMFwd', \
                         'COMVolATM', 'COMVolV90', 'COMVolV75', 'COMVolV25', 'COMVolV10']].fillna(method = 'ffill')
                df['CalSpread'] = (df['COMFwd'] - df['COMFwd'].shift(-1)).fillna(method = 'ffill')
                multi = 13
            elif tab_key == 'fx_daily':
                df = dbaccess.load_fut_curve(cnx, prod_code, tag, dbtable='fx_daily', field='ccy')
                df = df[df['rate']>0]
                df['fwd_points'] = df['rate'] - df['rate'][0]
                df = df[['ccy', 'tenor', 'rate', 'fwd_points']]
                multi = 5
            elif tab_key == 'ir_daily':
                df = dbaccess.load_fut_curve(cnx, prod_code, tag, dbtable='ir_daily', field='ir_index')
                df = df[['ir_index', 'tenor', 'rate']]
                multi = 4
            df.to_excel(writer, xl_structure[tab_key], index = False, startcol = idx * multi, startrow = 1)
    writer.save()
