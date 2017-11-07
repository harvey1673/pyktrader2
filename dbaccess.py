# -*- coding: utf-8 -*-
import datetime
import numpy
import sqlite3 as sqlconn
import copy
import csv
import os.path
import misc
import pandas as pd

#MKT_DB = 'mkt_data'
#dbconfig = {'user': 'harvey',
#            'password': 'h464717',
#            'host': 'localhost',
#            'database': MKT_DB,
#            }

#hist_dbconfig = {'user': 'harvey',
#            'password': 'h464717',
#            'host': 'localhost',
#            'database': MKT_DB,
#            }
dbconfig = {'database': "market_data.db"}
#dbconfig = {'database': "database.db", 'detect_types': sqlconn.PARSE_DECLTYPES|sqlconn.PARSE_COLNAMES}
hist_dbconfig = {'database': "market_data.db"}
#hist_dbconfig = {'database': "database.db", 'detect_types': sqlconn.PARSE_DECLTYPES|sqlconn.PARSE_COLNAMES}

trade_dbconfig = {'database': 'deal_data.db'}

fut_tick_columns = ['instID', 'date', 'tick_id', 'hour', 'min', 'sec', 'msec', 'openInterest', 'volume', 'price',
                    'high', 'low', 'bidPrice1', 'bidVol1', 'askPrice1', 'askVol1']
ss_tick_columns = ['instID', 'date', 'tick_id', 'hour', 'min', 'sec', 'msec', 'openInterest', 'volume', 'price', 'high',
                   'low', 'bidPrice1', 'bidVol1', 'askPrice1', 'askVol1']
min_columns = ['datetime', 'date', 'open', 'high', 'low', 'close', 'volume', 'openInterest', 'min_id']
daily_columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'openInterest']
fx_columns = ['date', 'tenor', 'rate']
ir_columns = ['date', 'tenor', 'rate']
spot_columns = ['date', 'close']
vol_columns = ['date', 'expiry', 'atm', 'v90', 'v75', 'v25', 'v10']
cmvol_columns = ['date', 'tenor_label', 'expiry_date', 'delta', 'vol', 'price', 'run_avg']
cmdv_columns = ['date', 'expiry', 'vol']
price_fields = { 'instID': daily_columns, 'spotID': spot_columns, 'vol_index': vol_columns, 'cmvol': cmvol_columns, \
                 'cmdv': cmdv_columns, 'ccy': fx_columns, 'ir_index': ir_columns, }
deal_columns = ['id', 'status', 'internal_id', 'external_id', 'cpty', 'positions', \
                'strategy', 'book', 'external_src', 'last_updated', \
                'trader', 'sales', 'desk', 'business', 'portfolio', \
                'enter_date', 'last_date', 'commission', 'day1_comments']

def connect(**args):
    return sqlconn.connect(**args)

def tick2dict(tick, tick_columns):
    tick_dict = dict(
        [tuple([col, getattr(tick, col)]) for col in tick_columns if col not in ['date', 'hour', 'min', 'sec', 'msec']])
    tick_dict['hour'] = tick.timestamp.hour
    tick_dict['min'] = tick.timestamp.minute
    tick_dict['sec'] = tick.timestamp.second
    tick_dict['msec'] = tick.timestamp.microsecond / 1000
    tick_dict['date'] = tick.date.strftime('%Y%m%d')
    return tick_dict

def insert_tick_data(cnx, inst, tick, dbtable='fut_tick'):
    tick_columns = fut_tick_columns
    if inst.isdigit():
        tick_columns = ss_tick_columns
    cursor = cnx.cursor()
    stmt = "INSERT IGNORE INTO {table} ({variables}) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)".format(
        table=dbtable, variables=','.join(tick_columns))
    tick_dict = tick2dict(tick, tick_columns)
    args = tuple([tick_dict[col] for col in tick_columns])
    cursor.execute(stmt, args)
    cnx.commit()

def bulkinsert_tick_data(cnx, inst, ticks, dbtable='fut_tick'):
    if len(ticks) == 0:
        return
    tick_columns = fut_tick_columns
    if inst.isdigit():
        tick_columns = ss_tick_columns
    cursor = cnx.cursor()
    stmt = "INSERT IGNORE INTO {table} ({variables}) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)".format(
        table=dbtable, variables=','.join(tick_columns))
    args = []
    for tick in ticks:
        tick_dict = tick2dict(tick, tick_columns)
        args.append(tuple([tick_dict[col] for col in tick_columns]))
    # args = [tuple([getattr(tick,col) for col in tick_columns]) for tick in ticks]
    cursor.executemany(stmt, args)
    cnx.commit()

def insert_min_data(cnx, inst, min_data, dbtable='fut_min', option='IGNORE'):
    cursor = cnx.cursor()
    exch = misc.inst2exch(inst)
    min_data['date'] = min_data['datetime'].date()
    stmt = "INSERT {opt} INTO {table} (instID,exch,{variables}) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)".format(
        opt=option, table=dbtable, variables=','.join(min_columns))
    args = tuple([inst, exch] + [min_data[col] for col in min_columns])
    cursor.execute(stmt, args)
    cnx.commit()

def bulkinsert_min_data(cnx, inst, mindata_list, dbtable='fut_min', is_replace=False):
    if len(mindata_list) == 0:
        return
    cursor = cnx.cursor()
    exch = misc.inst2exch(inst)
    if is_replace:
        cmd = "REPLACE"
    else:
        cmd = "INSERT IGNORE"
    stmt = "{cmd} INTO {table} (instID,exch,{variables}) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)".format(\
                            cmd=cmd, table=dbtable, variables=','.join(min_columns))
    args = []
    for min_data in mindata_list:
        args.append(tuple([inst, exch] + [min_data[col] for col in min_columns]))
    cursor.executemany(stmt, args)
    cnx.commit()

def insert_daily_data(cnx, inst, daily_data, is_replace=False, dbtable='fut_daily'):
    cursor = cnx.cursor()
    col_list = daily_data.keys()
    exch = misc.inst2exch(inst)
    if is_replace:
        cmd = "REPLACE"
    else:
        cmd = "INSERT IGNORE"
    stmt = "{commd} INTO {table} (instID,exch,{variables}) VALUES (%s,%s,{formats})".format(\
                    commd=cmd, table=dbtable, variables=','.join(col_list), \
                    formats=','.join(['%s'] * len(col_list)))
    args = tuple([inst, exch] + [daily_data[col] for col in col_list])
    cursor.execute(stmt, args)
    cnx.commit()

def import_tick_from_file(dbtable, cnx = None):
    if cnx == None:
        cnx = connect(**dbconfig)
    inst_list = ['IF1406', 'IO1406-C-2300', 'IO1406-P-2300', 'IO1406-C-2250',
                 'IO1406-P-2250', 'IO1406-C-2200', 'IO1406-P-2200', 'IO1406-C-2150',
                 'IO1406-P-2150', 'IO1406-C-2100', 'IO1406-P-2100', 'IO1406-C-2050',
                 'IO1406-P-2050', 'IO1406-C-2000', 'IO1406-P-2000', 'IO1407-C-2300',
                 'IO1407-P-2300', 'IO1407-C-2250', 'IO1407-P-2250', 'IO1407-C-2200',
                 'IO1407-P-2200', 'IO1407-C-2150', 'IO1407-P-2150', 'IO1407-C-2100',
                 'IO1407-P-2100', 'IO1407-C-2050', 'IO1407-P-2050', 'IO1407-C-2000',
                 'IO1407-P-2000', 'IF1406']
    date_list = ['20140603', '20140604', '20140605', '20140606']
    main_path = 'C:/dev/data/'
    cursor = cnx.cursor()
    for inst in inst_list:
        for date in date_list:
            path = main_path + inst + '/' + date + '_tick.txt'
            if os.path.isfile(path):
                stmt = "load data infile '{path}' replace into table {table} fields terminated by ',' lines terminated by '\n' (instID, date, @var1, sec, msec, openInterest, volume, price, high, low, bidPrice1, bidVol1, askPrice1, askVol1) set hour=(@var1 div 100), min=(@var1 % 100)".format(
                    path=path, table=dbtable)
                cursor.execute(stmt)
                cnx.commit()

def insert_cont_data(cont, cnx = None):
    if cnx == None:
        cnx = connect(**dbconfig)
    cursor = cnx.cursor()
    col_list = cont.keys()
    stmt = "REPLACE INTO {table} ({variables}) VALUES (%s,%s,%s,%s,%s,%s) ".format(table='contract_list',
                                                                                   variables=','.join(col_list))
    args = tuple([cont[col] for col in col_list])
    cursor.execute(stmt, args)
    cnx.commit()
    cnx.close()

def prod_main_cont_exch(prodcode, cnx = None):
    if cnx == None:
        cnx = connect(**dbconfig)
    cursor = cnx.cursor()
    stmt = "select exchange, contract from trade_products where product_code='{prod}' ".format(prod=prodcode)
    cursor.execute(stmt)
    out = [(exchange, contract) for (exchange, contract) in cursor]
    exch = str(out[0][0])
    cont = str(out[0][1])
    cont_mth = [misc.month_code_map[c] for c in cont]
    cnx.close()
    return cont_mth, exch

def load_product_info(prod, cnx = None):
    if cnx == None:
        cnx = connect(**dbconfig)
    cursor = cnx.cursor()
    stmt = "select exchange, lot_size, tick_size, start_min, end_min, broker_fee from trade_products where product_code='{product}' ".format(
        product=prod)
    cursor.execute(stmt)
    cnx.close()
    out = {}
    for (exchange, lot_size, tick_size, start_min, end_min, broker_fee) in cursor:
        out = {'exch': str(exchange),
               'lot_size': lot_size,
               'tick_size': float(tick_size),
               'start_min': start_min,
               'end_min': end_min,
               'broker_fee': float(broker_fee)
               }
    return out

def load_stockopt_info(inst, cnx = None):
    if cnx == None:
        cnx = connect(**dbconfig)
    cursor = cnx.cursor()
    stmt = "select underlying, opt_mth, otype, exchange, strike, strike_scale, lot_size, tick_base from stock_opt_map where instID='{product}' ".format(
        product=inst)
    cursor.execute(stmt)
    cnx.close()
    out = {}
    for (underlying, opt_mth, otype, exchange, strike, strike_scale, lot_size, tick_size) in cursor:
        out = {'exch': str(exchange),
               'lot_size': int(lot_size),
               'tick_size': float(tick_size),
               'strike': float(strike) / float(strike_scale),
               'cont_mth': opt_mth,
               'otype': str(otype),
               'underlying': str(underlying)
               }
    return out

def get_stockopt_map(underlying, cont_mths, strikes, cnx = None):
    if cnx == None:
        cnx = connect(**dbconfig)
    cursor = cnx.cursor()
    stmt = "select underlying, opt_mth, otype, strike, strike_scale, instID from stock_opt_map where underlying='{under}' and opt_mth in ({opt_mth_str}) and strike in ({strikes}) ".format(
        under=underlying,
        opt_mth_str=','.join([str(mth) for mth in cont_mths]), strikes=','.join([str(s) for s in strikes]))
    cursor.execute(stmt)
    cnx.close()
    out = {}
    for (underlying, opt_mth, otype, strike, strike_scale, instID) in cursor:
        key = (str(underlying), int(opt_mth), str(otype), float(strike) / float(strike_scale))
        out[key] = instID
    return out

def load_alive_cont(sdate, cnx = None):
    if cnx == None:
        cnx = connect(**dbconfig)
    cursor = cnx.cursor()
    stmt = "select instID, product_code from contract_list where expiry>=%s"
    args = tuple([sdate])
    cursor.execute(stmt, args)
    cnx.close()
    cont = []
    pc = []
    for line in cursor:
        cont.append(str(line[0]))
        prod = str(line[1])
        if prod not in pc:
            pc.append(prod)
    return cont, pc

def load_inst_marginrate(instID, cnx = None):
    if cnx == None:
        cnx = connect(**dbconfig)
    cursor = cnx.cursor()
    stmt = "select margin_l, margin_s from contract_list where instID='{inst}' ".format(inst=instID)
    cursor.execute(stmt)
    cnx.close()
    out = (0, 0)
    for (margin_l, margin_s) in cursor:
        out = (float(margin_l), float(margin_s))
    return out

def load_min_data_to_df(cnx, dbtable, inst, d_start, d_end, minid_start=1500, minid_end=2114, index_col='datetime'):
    stmt = "select {variables} from {table} where instID='{instID}' ".format(variables=','.join(min_columns),
                                                                             table=dbtable, instID=inst)
    stmt = stmt + "and min_id >= %s " % minid_start
    stmt = stmt + "and min_id <= %s " % minid_end
    stmt = stmt + "and date >= '%s' " % d_start.strftime('%Y-%m-%d')
    stmt = stmt + "and date <= '%s' " % d_end.strftime('%Y-%m-%d')
    stmt = stmt + "order by date, min_id"
    df = pd.io.sql.read_sql(stmt, cnx, index_col=index_col)
    return df

def load_daily_data_to_df(cnx, dbtable, inst, d_start, d_end, index_col='date', field = 'instID'):
    stmt = "select {variables} from {table} where {field} like '{instID}' ".format( \
                                    variables=','.join(price_fields[field]),
                                    table=dbtable, field = field, instID=inst)
    stmt = stmt + "and date >= '%s' " % d_start.strftime('%Y-%m-%d')
    stmt = stmt + "and date <= '%s' " % d_end.strftime('%Y-%m-%d')
    stmt = stmt + "order by date"
    df = pd.io.sql.read_sql(stmt, cnx, index_col=index_col)
    return df

def load_fut_curve(cnx, prod_code, ref_date, dbtable = 'fut_daily', field = 'instID'):
    stmt = "select {variables} from {table} where {field} like '{prod}%' ".format( \
                                    variables=','.join([field] + price_fields[field]),
                                    table=dbtable, field = field, prod = prod_code)
    stmt = stmt + "and date like '{refdate}%' ".format( refdate = ref_date.strftime('%Y-%m-%d'))
    stmt = stmt + "order by {field}".format(field = field)
    df = pd.io.sql.read_sql(stmt, cnx)
    return df

def load_deal_data(cnx, dbtable = 'deal', book = 'BOF', deal_status = [2]):
    stmt = "select {variables} from {table} where book = '{book}' ".format(table=dbtable, \
                                    variables=','.join(deal_columns), book = book)
    if len(deal_status) == 1:
        stmt = stmt + "and status = {deal_status} ".format(deal_status = deal_status[0])
    else:
        stmt = stmt + "and status in {deal_status} ".format(deal_status = tuple(deal_status))
    stmt = stmt + "order by id"
    df = pd.io.sql.read_sql(stmt, cnx)
    return df

def load_cmvol_curve(cnx, prod_code, ref_date, dbtable = 'cmvol_daily', field = 'cmvol'):
    stmt = "select {variables} from {table} where product_code like '{prod}%' ".format( \
                                    variables=','.join(price_fields[field]),
                                    table = dbtable, prod = prod_code)
    stmt = stmt + "and date like '{refdate}%' ".format( refdate = ref_date.strftime('%Y-%m-%d'))
    stmt = stmt + "order by expiry_date".format(field = field)
    df = pd.io.sql.read_sql(stmt, cnx)
    df['delta'] = ((df['delta']+1)*100).astype(int) % 100
    vol_tbl = df.pivot_table(columns = ['delta'], index = ['tenor_label'], values = ['vol'], aggfunc = numpy.mean)
    return vol_tbl

def load_cmdv_curve(cnx, fwd_index, spd_key, ref_date, dbtable = 'cmspdvol_daily', field = 'cmdv'):
    stmt = "select {variables} from {table} where fwd_index like '{fwd_index}%' and spd_key='{spd_key}' ".format( \
                                    variables=','.join(price_fields[field]), spd_key = spd_key, \
                                    table = dbtable, fwd_index = fwd_index)
    stmt = stmt + "and date like '{refdate}%' order by expiry".format( refdate = ref_date.strftime('%Y-%m-%d'))
    df = pd.io.sql.read_sql(stmt, cnx)
    return df

def load_tick_to_df(cnx, dbtable, inst, d_start, d_end, start_tick=1500000, end_tick=2115000):
    tick_columns = fut_tick_columns
    if dbtable == 'stock_tick':
        tick_columns = ss_tick_columns
    stmt = "select {variables} from {table} where instID='{instID}' ".format(variables=','.join(tick_columns),
                                                                             table=dbtable, instID=inst)
    stmt = stmt + "and tick_id >= %s " % start_tick
    stmt = stmt + "and tick_id <= %s " % end_tick
    stmt = stmt + "and date >='%s' " % d_start.strftime('%Y-%m-%d')
    stmt = stmt + "and date <='%s' " % d_end.strftime('%Y-%m-%d')
    stmt = stmt + "order by date, tick_id"
    df = pd.io.sql.read_sql(stmt, cnx)
    return df

def load_tick_data(cnx, dbtable, insts, d_start, d_end):
    cursor = cnx.cursor()
    tick_columns = fut_tick_columns
    if dbtable == 'stock_tick':
        tick_columns = ss_tick_columns
    stmt = "select {variables} from {table} where instID in ('{instIDs}') ".format(variables=','.join(tick_columns),
                                                                                   table=dbtable,
                                                                                   instIDs="','".join(insts))
    stmt = stmt + "and date >= '%s' " % d_start.strftime('%Y-%m-%d')
    stmt = stmt + "and date <= '%s' " % d_end.strftime('%Y-%m-%d')
    stmt = stmt + "order by date, tick_id"
    cursor.execute(stmt)
    all_ticks = []
    for line in cursor:
        tick = dict([(key, val) for (key, val) in zip(tick_columns, line)])
        tick['timestamp'] = datetime.datetime.combine(tick['date'], datetime.time(hour=tick['hour'], minute=tick['min'],
                                                                                  second=tick['sec'],
                                                                                  microsecond=tick['msec'] * 1000))
        all_ticks.append(tick)
    return all_ticks

def insert_min_data_to_df(df, min_data):
    new_data = {key: min_data[key] for key in min_columns[1:]}
    df.loc[min_data['datetime']] = pd.Series(new_data)

def insert_new_min_to_df(df, idx, min_data):
    need_update = True
    col_list = min_columns + ['bar_id']
    new_min = {key: min_data[key] for key in col_list}
    if idx > 0:
        idy = idx - 1
        if min_data['datetime'] < df.at[idy, 'datetime']:
            need_update = False
        elif min_data['datetime'] > df.at[idy, 'datetime']:
            idy = idx
    else:
        idy = 0
    if need_update:
        df.loc[idy] = pd.Series(new_min)
    return idy + 1

def insert_daily_data_to_df(df, daily_data):
    if (daily_data['date'] not in df.index):
        new_data = {key: daily_data[key] for key in daily_columns[1:]}
        df.loc[daily_data['date']] = pd.Series(new_data)

def get_daily_by_tick(inst, cur_date, start_tick=1500000, end_tick=2100000):
    df = load_tick_to_df('fut_tick', inst, cur_date, cur_date, start_tick, end_tick)
    ddata = {}
    ddata['date'] = cur_date
    if len(df) > 0:
        ddata['open'] = float(df.iloc[0].price)
        ddata['close'] = float(df.iloc[-1].price)
        ddata['high'] = float(df.iloc[-1].high)
        ddata['low'] = float(df.iloc[-1].low)
        ddata['volume'] = int(df.iloc[-1].volume)
        ddata['openInterest'] = int(df.iloc[-1].openInterest)
    else:
        ddata['open'] = 0.0
        ddata['close'] = 0.0
        ddata['high'] = 0.0
        ddata['low'] = 0.0
        ddata['volume'] = 0
        ddata['openInterest'] = 0
    return ddata
