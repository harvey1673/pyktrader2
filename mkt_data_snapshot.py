# -*- coding: utf-8 -*-
import web_sina_api
import openpyxl
import os.path
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
MKT_LATEST_XLFILE = "P:\\data\\market_data_latest.xlsx"

def snap_curr_market():
    cont_list = {}
    all_conts = []
    tday = datetime.date.today()
    for asset, exch, cont_mth in live_asset_list:
        conts, _ = misc.contract_range(asset, exch, cont_mth, tday, tday)
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

def save_xlmkt_to_db(tag, xlfile = MKT_LATEST_XLFILE, snap_live = False, input_data = {}):
    comm_curves = 9
    fx_curves = 1
    ir_curves = 1
    if snap_live:
        cont_dict, quotes = snap_curr_market()
        if 'SGX_DCE_spd' in input_data:
            quotes['SGX_DCE_spd'] = input_data['SGX_DCE_spd']
        else:
            try:
                wbook = openpyxl.load_workbook(xlfile, data_only=True, read_only=True)
                quotes['SGX_DCE_spd'] = float(wbook['COMM']['F1'].value)
            except:
                pass
        if 'FX' in input_data:
            quotes['FX'] = input_data['FX']
    else:
        cont_dict = {}
        quotes  = {}
    conn = dbaccess.connect(**dbaccess.mktsnap_dbconfig)

    fx_df = pd.DataFrame()
    for idx in range(fx_curves):
        df = pd.read_excel(xlfile, sheetname="FX", header=1, index_col=None, parse_cols=range(idx * 5, idx * 5 + 4)).dropna()
        if snap_live and ('FX' not in quotes):
            quotes['FX'] = float(df['rate'][0])
        df['date'] = tag
        df['src'] = xlfile
        cdf = df[['date', 'ccy', 'tenor', 'rate', 'src']]
        fx_df = fx_df.append(cdf)

    ir_df = pd.DataFrame()
    for idx in range(ir_curves):
        df = pd.read_excel(xlfile, sheetname="IR", header=1, index_col=None, parse_cols=range(idx * 4, idx * 4 + 3)).dropna()
        df['date'] = tag
        df['src'] = xlfile
        rdf = df[['date', 'tenor', 'rate', 'ir_index', 'src']]
        ir_df = ir_df.append(rdf)

    # loading commod curves
    opt_df = pd.DataFrame()
    fut_df = pd.DataFrame()
    for idx in range(comm_curves):
        df = pd.read_excel(xlfile, sheetname="COMM", header = 1, index_col = None, parse_cols = range(idx * 13, idx * 13 + 12)).dropna()
        if snap_live:
            if df['product_code'][0] == 'fef':
                tday = datetime.date.today()
                tenor = str((tday.year - 2000) + tday.month)
                if cont_dict['i'][0][-4:] == tenor:
                    dce_instID = cont_dict['i'][1]
                else:
                    dce_instID = cont_dict['i'][0]
                dce_quote = (quotes[dce_instID]['bidPrice1'] + quotes[dce_instID]['askPrice1'])/2.0
                fef_quote = quotes['SGX_DCE_spd'] + (dce_quote - 30/0.92)/1.16/quotes['FX']
                fef_tenor = 'fef'+ dce_instID[-4:]
                diff = fef_quote - float(df.loc[df['instID'] == fef_tenor, 'COMFwd'])
                df.loc[1:, 'COMFwd'] = (df.loc[1:, 'COMFwd'] + diff).round(2)
            elif df['product_code'][0] in cont_dict:
                for instID in cont_dict[df['product_code'][0]]:
                    df.loc[df['instID'] == instID, 'COMFwd'] = (quotes[instID]['askPrice1'] + quotes[instID]['bidPrice1'])/2.0
        df['date'] = tag
        fdf = df[['instID', 'exch', 'date', 'COMFwd']]
        fdf.rename(columns={'COMFwd': 'close'}, inplace = True)
        fut_df = fut_df.append(fdf)
        if df['product_code'][0] in option_markets:
            for delta, col_name in zip([0.5, 0.1, 0.25, -0.25, -0.1], ['COMVolATM', 'COMVolV10', 'COMVolV25', 'COMVolV75', 'COMVolV90']):
                xdf = df[['date', 'tenor_label', col_name, 'expiry_date', 'exch', 'product_code']]
                xdf['tenor_label'] = xdf['tenor_label'].apply(lambda x: x.date())
                xdf['expiry_date'] = xdf['expiry_date'].apply(lambda x: x.date())
                xdf.rename(columns={col_name: 'vol'}, inplace = True)
                if (delta != 0.5):
                    xdf.loc[:, 'vol'] = xdf.loc[:, 'vol'] + df.loc[:, 'COMVolATM']
                xdf.loc[:, 'delta'] = delta
                opt_df = opt_df.append(xdf)
    fut_df.to_sql('fut_daily', conn, flavor='sqlite', if_exists='append', index=False)
    opt_df.to_sql('cmvol_daily', conn, flavor='sqlite', if_exists='append', index=False)
    fx_df.to_sql('fx_daily', conn, flavor='sqlite', if_exists='append', index=False)
    ir_df.to_sql('ir_daily', conn, flavor='sqlite', if_exists='append', index=False)
    return quotes

def load_db_to_xlmkt(tag, xlfile = MKT_LATEST_XLFILE):
    if os.path.isfile(xlfile):
        book = openpyxl.load_workbook(xlfile)
        writer = pd.ExcelWriter(xlfile, engine='openpyxl')
        writer.book = book
        writer.sheets = dict((ws.title, ws) for ws in book.worksheets)
    else:
        writer = pd.ExcelWriter(xlfile)
    cnx = dbaccess.connect(**dbaccess.mktsnap_dbconfig)
    req_data = {'i':None, 'fef':None, 'USD/CNY':None}
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
            if prod_code in req_data:
                req_data[prod_code] = df
    #do the SGX-DCE spread calc
    try:
        tday =  datetime.date.today()
        if tday >= req_data['i']['tenor_label'][0]:
            dce_prompt =  req_data['i']['instID'][1]
        else:
            dce_prompt = req_data['i']['instID'][0]
        sgx_prompt = 'fef' + dce_prompt[-4:]
        sgx_price = float(req_data['fef'].loc[req_data['fef']['instID'] == sgx_prompt, 'COMFwd'])
        dce_price = float(req_data['i'].loc[req_data['i']['instID'] == dce_prompt, 'COMFwd'])
        fx = float(req_data['USD/CNY']['rate'][0])
        sgx_dce_spd =  sgx_price - (dce_price - 30.0/0.92)/1.16/fx
        wb = writer.book
        wb['COMM']['F1'] = sgx_dce_spd
    except:
        print "failed to update SGX-DCE spread"
    writer.save()
