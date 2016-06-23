import datetime
import csv
import os.path
import mysql.connector
import math
import pandas as pd
import misc
from WindPy import w
w.start()
    
def import_csv_data(filename):
    reader = csv.reader(file(filename, 'rb'))
    contList = []
    datapath = 'C:\\dev\\src\\ktlib\\data2\\'
    
    for line in reader:
        contList.append(line[0])

    cnx = mysql.connector.connect(**dbconfig)
    cursor = cnx.cursor()

    for cont in contList:
        
        if cont[1].isalpha(): key = cont[:2]
        elif cont[0].isalpha(): key = cont[:1]
        else: key = cont

        ex = 'SH'
        for exch in product_code.keys():
            if key in product_code[exch]:
                ex = exch
        
        if ex == 'SHF':
            ex = 'SHFE'
        elif ex == 'CZC':
            ex = 'CZCE'
        elif ex == 'CFE':
            ex = 'CFFEX'
        minfile = datapath + cont + '_min.csv'
        if os.path.isfile(minfile):
            dbtable = 'fut_min'
            data_reader = csv.reader(file(minfile, 'rb'))
            fields = ['instID', 'exch', 'datetime', 'min_id', 'open', 'close', 'high', 'low', 'volume', 'openInterest']
            data = []
            for idx, line in enumerate(data_reader):
                if idx > 0:
                    if 'nan' in [line[0],line[2],line[3],line[4], line[6]]: continue
                    vol   = int(float(line[0]))
                    if vol <= 0: continue
                    dtime = datetime.datetime.strptime(line[1], '%Y-%m-%d %H:%M:%S.%f')
                    dtime_str = dtime.strftime('%Y-%m-%d %H:%M:%S')
                    high  = float(line[2])
                    low   = float(line[3])
                    close = float(line[4])
                    if line[5] == 'nan':
                        oi = 0
                    else:
                        oi = int(float(line[5]))
                    open  = float(line[6])
                    min_id = get_min_id(dtime)
                    data.append((cont, ex, dtime_str, min_id, open, close, high, low, vol, oi))
            
            if len(data)>0:
                print "inserting minute data for contract %s with total rows %s" % (cont, len(data))
                stmt = "REPLACE INTO {table} ({variables}) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)".format(table=dbtable,variables=','.join(fields))   
                cursor.executemany(stmt, data)
                cnx.commit()
            else:
                print "no minute data for contract %s" % (cont)
        else:
            print "no minute csv file for contract %s" % (cont)
            
        dayfile = datapath + cont + '_daily.csv'
        if os.path.isfile(dayfile):
            dbtable = 'fut_daily'
            data_reader = csv.reader(file(dayfile, 'rb'))
            fields = ['instID', 'exch', 'date', 'open', 'close', 'high', 'low', 'volume', 'openInterest']
            data = []
            for idx, line in enumerate(data_reader):
                if idx > 0 :
                    if 'nan' in [line[0],line[2],line[3],line[4], line[6]]: continue
                    vol   = int(float(line[0]))
                    if vol <= 0: continue
                    dtime = datetime.datetime.strptime(line[1], '%Y-%m-%d %H:%M:%S.%f')
                    dtime_str = dtime.strftime('%Y-%m-%d')
                    high  = float(line[2])
                    low   = float(line[3])
                    close = float(line[4])
                    if line[5] == 'nan':
                        oi = 0
                    else:
                        oi = int(float(line[5]))
                    open  = float(line[6])
                    data.append((cont, ex, dtime_str, open, close, high, low, vol, oi))
            
            if len(data)>0:
                print "inserting daily data for contract %s with total rows %s" % (cont, len(data))
                stmt = "REPLACE INTO {table} ({variables}) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)".format(table=dbtable,variables=','.join(fields))   
                cursor.executemany(stmt, data)
                cnx.commit()
            else:
                print "no daily data for contract %s" % (cont)
        else:
            print "no daily csv file for contract %s" % (cont)
                                
    cursor.close()
    cnx.close()
    return True
    
wind_exch_map = {'SHF': 'SHFE', 'CZC': 'CZCE', 'DCE': 'DCE', 'CFE': 'CFFEX'}     

def get_wind_data(inst_list, start_date, end_date, save_loc = 'C:\\dev\\data\\', freq = 'm'):
    exch_map = {v: k for k, v in win_exch_map.items()}
    for instID in inst_list:
        exch = misc.inst2exch(instID)
        ex = exch_map[exch]
        ticker = instID + '.' + ex
        product = inst2product(instID)
        sdate = start_date
        edate = end_date
        stime = datetime.time( 9, 0, 0)
        etime = datetime.time(15, 0, 0)
        if product in ['T', 'TF']:
            stime = datetime.time(9, 14, 0)
            etime = datetime.time(15, 15, 0)
        elif product in misc.night_session_markets:
            stime = datetime.time(21, 0, 0)
            sdate = misc.day_shift(sdate, '-1b')
        smin = datetime.datetime.combine(sdate, stime)
        emin = datetime.datetime.combine(edate, etime)
        fields = 'open,high,low,close,volume,oi'
        try:
            if freq == 'm':
                raw_data = w.wsi(ticker,fields,smin,emin)
                if len(raw_data.Data)>1:
                    outfile = save_loc + instID +'_min.csv'
                    output={'datetime':raw_data.Times, 
                            'open':raw_data.Data[0],
                            'high':raw_data.Data[1],
                            'low':raw_data.Data[2],
                            'close':raw_data.Data[3],
                            'volume':raw_data.Data[4],
                            'openInterest':raw_data.Data[5]}
                    dump2csvfile(output,outfile)
                else:
                    print "no min data obtained for ticker=%s" % ticker
            elif freq == 'd':
                raw_data = w.wsd(ticker, fields, start_date, end_date)
                if len(raw_data.Data)>1:
                    outfile = save_loc + instID + '_daily.csv'
                    output={'datetime':raw_data.Times, 
                            'open':raw_data.Data[0],                            
                            'high':raw_data.Data[1],
                            'low':raw_data.Data[2],
                            'close':raw_data.Data[3],
                            'volume':raw_data.Data[4],
                            'openInterest':raw_data.Data[5]}
                    dump2csvfile(output,outfile)
            else:
                print "no daily data obtained for ticker=%s" % ticker
        except ValueError:
            pass
    w.stop()
    return True

def load_csv_to_db( sdate, edate, save_loc = 'C:\\dev\\data\\'):
    df = load_live_cont(d_start, d_end)
    inst_list = misc.filter_main_cont(edate, False)
    cnx = mysql.connector.connect(**misc.dbconfig)
    cursor = cnx.cursor()
    for cont in contList:
        minfile = save_loc + cont + '_min.csv'
        if not os.path.isfile(minfile):
            continue
        data_reader = csv.reader(file(minfile, 'rb'))
        for idx, line in enumerate(data_reader):
            if idx > 0:
                if 'nan' in [line[0],line[2],line[3],line[4], line[6]]: continue
                #min_data = 
                vol   = int(float(line[0]))
                if vol <= 0: continue
                dtime = datetime.datetime.strptime(line[1], '%Y-%m-%d %H:%M:%S.%f')
                dtime_str = dtime.strftime('%Y-%m-%d %H:%M:%S')
                high  = float(line[2])
                low   = float(line[3])
                close = float(line[4])
                if line[5] == 'nan':
                    oi = 0
                else:
                    oi = int(float(line[5]))
                open  = float(line[6])
                min_id = get_min_id(dtime)
                tdate = dtime.date()
                data.append((cont, ex, dtime_str, min_id, open, close, high, low, vol, oi))
        if cont[1].isalpha(): key = cont[:2]
        elif cont[0].isalpha(): key = cont[:1]
        else: key = cont
        ex = 'SH'
        for exch in product_code.keys():
            if key in product_code[exch]:
                ex = exch
        if ex == 'SHF':
            ex = 'SHFE'
        elif ex == 'CZC':
            ex = 'CZCE'
        elif ex == 'CFE':
            ex = 'CFFEX'
            
        mth = int(cont[-2:])
        if (key not in contMonth):
            continue
        if mth not in contMonth[key]:
            continue
        minfile = datapath + cont + '_min.csv'
        if os.path.isfile(minfile):
            dbtable = 'fut_min'
            
            fields = ['instID', 'exch', 'datetime', 'min_id', 'open', 'close', 'high', 'low', 'volume', 'openInterest']
            data = []
            for idx, line in enumerate(data_reader):
                if idx > 0:
                    if 'nan' in [line[0],line[2],line[3],line[4], line[6]]: continue
                    vol   = int(float(line[0]))
                    if vol <= 0: continue
                    dtime = datetime.datetime.strptime(line[1], '%Y-%m-%d %H:%M:%S.%f')
                    dtime_str = dtime.strftime('%Y-%m-%d %H:%M:%S')
                    high  = float(line[2])
                    low   = float(line[3])
                    close = float(line[4])
                    if line[5] == 'nan':
                        oi = 0
                    else:
                        oi = int(float(line[5]))
                    open  = float(line[6])
                    min_id = get_min_id(dtime)
                    data.append((cont, ex, dtime_str, min_id, open, close, high, low, vol, oi))
            
            if len(data)>0:
                print "inserting minute data for contract %s with total rows %s" % (cont, len(data))
                stmt = "REPLACE INTO {table} ({variables}) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)".format(table=dbtable,variables=','.join(fields))   
                cursor.executemany(stmt, data)
                cnx.commit()
            else:
                print "no minute data for contract %s" % (cont)
        else:
            print "no minute csv file for contract %s" % (cont)
            
        dayfile = datapath + cont + '_daily.csv'
        if os.path.isfile(dayfile):
            dbtable = 'fut_daily'
            data_reader = csv.reader(file(dayfile, 'rb'))
            fields = ['instID', 'exch', 'date', 'open', 'close', 'high', 'low', 'volume', 'openInterest']
            data = []
            for idx, line in enumerate(data_reader):
                if idx > 0 :
                    if 'nan' in [line[0],line[2],line[3],line[4], line[6]]: continue
                    vol   = int(float(line[0]))
                    if vol <= 0: continue
                    dtime = datetime.datetime.strptime(line[1], '%Y-%m-%d %H:%M:%S.%f')
                    dtime_str = dtime.strftime('%Y-%m-%d')
                    high  = float(line[2])
                    low   = float(line[3])
                    close = float(line[4])
                    if line[5] == 'nan':
                        oi = 0
                    else:
                        oi = int(float(line[5]))
                    open  = float(line[6])
                    data.append((cont, ex, dtime_str, open, close, high, low, vol, oi))
            
            if len(data)>0:
                print "inserting daily data for contract %s with total rows %s" % (cont, len(data))
                stmt = "REPLACE INTO {table} ({variables}) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)".format(table=dbtable,variables=','.join(fields))   
                cursor.executemany(stmt, data)
                cnx.commit()
            else:
                print "no daily data for contract %s" % (cont)
        else:
            print "no daily csv file for contract %s" % (cont)
                                
    cursor.close()
    cnx.close()
    return True

def dump2csvfile(data, outfile):
    output = [];    
    for key in data.keys():
        x = [key] + data[key];
        output.append(x);             
    item_len = len(output[0]);    
    with open(outfile,'wb') as test_file:
        file_writer = csv.writer(test_file, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL);
        for i in range(item_len):
            file_writer.writerow([x[i] for x in output])
    return 0 

if __name__=="__main__":
    pass
