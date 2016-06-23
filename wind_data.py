import datetime
import csv
import os.path
import mysql.connector
import mysqlaccess as db
import math
import pandas as pd
import misc
from WindPy import w
w.start()
    
wind_exch_map = {'SHF': 'SHFE', 'CZC': 'CZCE', 'DCE': 'DCE', 'CFE': 'CFFEX'}     

def get_min_id(dt):
    return ((dt.hour+6)%24)*100+dt.minute

def get_wind_data(inst_list, start_date, end_date, save_loc = 'C:\\dev\\data\\', freq = 'm'):
    exch_map = {v: k for k, v in wind_exch_map.items()}
    for instID in inst_list:
        exch = misc.inst2exch(instID)
        ex = exch_map[exch]
        ticker = instID + '.' + ex
        product = misc.inst2product(instID)
        sdate = start_date
        edate = end_date
        stime = datetime.time( 8, 59, 0)
        etime = datetime.time(15, 0, 0)
        if product in ['T', 'TF']:
            stime = datetime.time(9, 14, 0)
            etime = datetime.time(15, 15, 0)
        elif product in misc.night_session_markets:
            stime = datetime.time(20, 59, 0)
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

def load_csv_to_db( edate, save_loc = 'C:\\dev\\data\\', freq = 'm', is_replace = False):
    cont_list = misc.filter_main_cont(edate, False)
    if freq not in ['m', 'd']:
        return False
    for cont in cont_list:
        if freq == 'm':
            filename = save_loc + cont + '_min.csv'
        else:
            filename = save_loc + cont + '_daily.csv'
        if not os.path.isfile(filename):
            continue
        data_reader = csv.reader(file(filename, 'rb'))
        mindata_list = []
        for idx, line in enumerate(data_reader):
            if idx > 0:
                if 'nan' in [line[0],line[2],line[3],line[4], line[6]]:
                    continue
                min_data = {}
                min_data['volume']   = int(float(line[0]))
                if min_data['volume'] <= 0: continue
                dtime = datetime.datetime.strptime(line[1], '%Y-%m-%d %H:%M:%S.%f')
                if freq == 'm':
                    min_data['datetime'] = dtime.replace(microsecond=0)
                else:
                    min_data['date'] = dtime.date()
                min_data['high']  = float(line[2])
                min_data['low']   = float(line[3])
                min_data['close'] = float(line[4])
                if line[5] == 'nan':
                    oi = 0
                else:
                    oi = int(float(line[5]))
                min_data['openInterest'] = oi
                min_data['open']  = float(line[6])
                if freq == 'm':
                    min_data['min_id'] = get_min_id(dtime)
                    trading_date = dtime.date()
                    if min_data['min_id'] < 600:
                        trading_date = misc.day_shift(trading_date, '1b')
                    min_data['date'] = trading_date
                    mindata_list.append(min_data)
                else:
                    print cont
                    db.insert_daily_data(cont, min_data, is_replace = is_replace, dbtable = 'fut_daily')
        if freq == 'm':
            print cont
            db.bulkinsert_min_data(cont, mindata_list, is_replace = is_replace)
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
