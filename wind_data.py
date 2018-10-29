# -*- coding:gbk -*-

import pandas as pd
from WindPy import w
import misc
from wind_data_config import *
import dbaccess
import csv
from test_data import process_min_id
from sqlalchemy import create_engine
import datetime,time
import os

wind_exch_map = {'SHF': 'SHFE', 'CZC': 'CZCE', 'DCE': 'DCE', 'CFE': 'CFFEX'}
w.start()

def load_symbol(symbol, field_list, start_date, end_date, freq = 'd',
                  data_struct = {'oi': 'openInterest'}):
    df = pd.DataFrame()
    if freq == 'd':
        func = w.wsd
        data_struct['Times'] ='date'
    elif freq == 'm':
        func = w.wsi
        data_struct['Times'] = 'datetime'
    else:
        print "unsupported freq, d or m"
        return df
    out = func(symbol, ','.join(field_list), start_date, end_date)
    if out.ErrorCode < 0:
        return df
    df['Times'] = out.Times
    for f, data in zip(field_list, out.Data):
        df[f] = data
    df.rename(columns = data_struct, inplace = True)
    df = df.dropna()
    return df

def save_hist_data(start_date, end_date,
                   index_list = [],
                   product_codes=[],
                   spot_list = [],
                   min_bar = False):
    conn = dbaccess.connect(**dbaccess.dbconfig)
    tday = datetime.date.today()
    for symbol, cmd_idx, desc in index_list:
        df = load_symbol(symbol, ['open', 'high', 'low', 'close', 'volume'], start_date, end_date)
        if len(df)> 0:
            df['instID'] = cmd_idx
            exch = symbol.split('.')[-1]
            df['exch'] = exch
            print "saving daily data for instID = %s with number of data pts = %s" % (cmd_idx, len(df))
            df.to_sql('fut_daily', conn, 'sqlite', if_exists='append', index=False)
    for prodcode in product_codes:
        cont_mth, exch = dbaccess.prod_main_cont_exch(prodcode)
        cont_list, _ = misc.contract_range(prodcode, exch, cont_mth, start_date, end_date)
        exp_dates = [misc.contract_expiry(cont) for cont in cont_list]
        exch2wind_dict = dict([ (v, k) for k, v in wind_exch_map.iteritems( )])
        for cont, exp in zip(cont_list, exp_dates):
            if exp >= start_date:
                ex = exch2wind_dict[exch]
                symbol = cont + '.' + ex
                ddf = load_symbol(symbol, ['open', 'high', 'low', 'close', 'volume', 'oi'], max(exp - datetime.timedelta(days = 400), start_date), min(exp, tday), freq = 'd')
                if len(ddf) > 0:
                    print "saving daily data for instID = %s with number of data pts = %s" % (cont, len(ddf))
                    ddf['instID'] = cont
                    ddf['exch'] = exch
                    ddf.to_sql('fut_daily', conn, 'sqlite', if_exists='append', index=False)
                if min_bar:
                    mdf = load_symbol(symbol, ['open', 'high', 'low', 'close', 'volume', 'oi'], max(exp - datetime.timedelta(days = 400),start_date), min(exp, tday), freq='m')
                    if len(mdf) > 0:
                        print "saving min data for instID = %s with number of data pts = %s" % (cont, len(mdf))
                        mdf['instID'] = cont
                        mdf['exch'] = exch
                        mdf = process_min_id(mdf)
                        mdf.to_sql('fut_min', conn, 'sqlite', if_exists='append', index=False)
    for symbol, spotID, desc in spot_list:
        df = load_symbol(symbol, ['close'], start_date, end_date)
        if len(df)> 0:
            df['spotID'] = spotID
            print "saving daily data for spotID = %s with number of data pts = %s" % (spotID, len(df))
            df.to_sql('spot_daily', conn, 'sqlite', if_exists='append', index=False)

class WindStock():

    def getCurrentTime(self):
        # 获取当前时间
        return time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(time.time()))

    def AStockHisData(self,symbols,start_date,end_date,step=0):
        '''
        逐个股票代码查询行情数据
        wsd代码可以借助 WindNavigator自动生成copy即可使用;时间参数不设，默认取当前日期，可能是非交易日没数据;
        只有一个时间参数时，默认作为为起始时间，结束时间默认为当前日期；如设置两个时间参数则依次为起止时间
        '''
        print(self.getCurrentTime(),": Download A Stock Starting:")
        for symbol in symbols:
             w.start()
             try:
                 #stock=w.wsd(symbol,'trade_code,open,high,low,close,volume,amt',start_date,end_date)
                 '''
                 wsd代码可以借助 WindNavigator自动生成copy即可使用;
                 时间参数不设，默认取当前日期，可能是非交易日没数据;
                 只有一个时间参数，默认为起始时间到最新；如设置两个时间参数则依次为起止时间
                '''
                 stock=w.wsd(symbol, "trade_code,open,high,low,close,pre_close,volume,amt,dealnum,chg,pct_chg,vwap, adjfactor,close2,turn,free_turn,oi,oi_chg,pre_settle,settle,chg_settlement,pct_chg_settlement, lastradeday_s,last_trade_day,rel_ipo_chg,rel_ipo_pct_chg,susp_reason,close3, pe_ttm,val_pe_deducted_ttm,pe_lyr,pb_lf,ps_ttm,ps_lyr,dividendyield2,ev,mkt_cap_ard,pb_mrq,pcf_ocf_ttm,pcf_ncf_ttm,pcf_ocflyr,pcf_nflyr,trade_status", start_date,end_date)
                 index_data = pd.DataFrame()
                 index_data['trade_date']=stock.Times
                 stock.Data[0]=symbol
                 index_data['stock_code']=stock.Data[0]
                 #index_data['stock_code'] =symbol
                 index_data['open'] =stock.Data[1]
                 index_data['high'] =stock.Data[2]
                 index_data['low']  =stock.Data[3]
                 index_data['close']=stock.Data[4]
                 index_data['pre_close']=stock.Data[5]
                 index_data['volume']=stock.Data[6]
                 index_data['amt']=stock.Data[7]
                 index_data['dealnum']=stock.Data[8]
                 index_data['chg']=stock.Data[9]
                 index_data['pct_chg']=stock.Data[10]
                 #index_data['pct_chg']=index_data['pct_chg']/100
                 index_data['vwap']=stock.Data[11]
                 index_data['adj_factor']=stock.Data[12]
                 index_data['close2']=stock.Data[13]
                 index_data['turn']=stock.Data[14]
                 index_data['free_turn']=stock.Data[15]
                 index_data['oi']=stock.Data[16]
                 index_data['oi_chg']=stock.Data[17]
                 index_data['pre_settle']=stock.Data[18]
                 index_data['settle']=stock.Data[19]
                 index_data['chg_settlement']=stock.Data[20]
                 index_data['pct_chg_settlement']=stock.Data[21]
                 index_data['lastradeday_s']=stock.Data[22]
                 index_data['last_trade_day']=stock.Data[23]
                 index_data['rel_ipo_chg']=stock.Data[24]
                 index_data['rel_ipo_pct_chg']=stock.Data[25]
                 index_data['susp_reason']=stock.Data[26]
                 index_data['close3']=stock.Data[27]
                 index_data['pe_ttm']=stock.Data[28]
                 index_data['val_pe_deducted_ttm']=stock.Data[29]
                 index_data['pe_lyr']=stock.Data[30]
                 index_data['pb_lf']=stock.Data[31]
                 index_data['ps_ttm']=stock.Data[32]
                 index_data['ps_lyr']=stock.Data[33]
                 index_data['dividendyield2']=stock.Data[34]
                 index_data['ev']=stock.Data[35]
                 index_data['mkt_cap_ard']=stock.Data[36]
                 index_data['pb_mrq']=stock.Data[37]
                 index_data['pcf_ocf_ttm']=stock.Data[38]
                 index_data['pcf_ncf_ttm']=stock.Data[39]
                 index_data['pcf_ocflyr']=stock.Data[40]
                 index_data['pcf_ncflyr']=stock.Data[41]
                 index_data['trade_status']=stock.Data[42]
                 index_data['data_source']='Wind'
                 index_data['created_date']=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                 index_data['updated_date']=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                 index_data = index_data[index_data['open'] > 0]
                 #index_data.fillna(0)
                 try:
                    index_data.to_sql('stock_daily_data',engine,if_exists='append');
                 except Exception as e:
                     #如果写入数据库失败，写入日志表，便于后续分析处理
                     error_log=pd.DataFrame()
                     error_log['trade_date']=stock.Times
                     error_log['stock_code']=stock.Data[0]
                     error_log['start_date']=start_date
                     error_log['end_date']=end_date
                     error_log['status']=None
                     error_log['table']='stock_daily_data'
                     error_log['args']='Symbol: '+symbol+' From '+start_date+' To '+end_date
                     error_log['error_info']=e
                     error_log['created_date']=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                     error_log.to_sql('stock_error_log',engine,if_exists='append')
                     print ( self.getCurrentTime(),": SQL Exception :%s" % (e) )
                     continue
                 w.start()
             except Exception as e:
                     #如果读取处理失败，可能是网络中断、频繁访问被限、历史数据缺失等原因。写入相关信息到日志表，便于后续补充处理
                     error_log=pd.DataFrame()
                     error_log['trade_date']=stock.Times
                     error_log['stock_code']=stock.Data[0]
                     error_log['start_date']=start_date
                     error_log['end_date']=end_date
                     error_log['status']=None
                     error_log['table']='stock_daily_data'
                     error_log['args']='Symbol: '+symbol+' From '+start_date+' To '+end_date
                     error_log['error_info']=e
                     error_log['created_date']=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                     error_log.to_sql('stock_error_log',engine,if_exists='append')
                     print ( self.getCurrentTime(),":index_data %s : Exception :%s" % (symbol,e) )
                     time.sleep(sleep_time)
                     w.start()
                     continue
             print(self.getCurrentTime(),": Downloading [",symbol,"] From "+start_date+" to "+end_date)
        print(self.getCurrentTime(),": Download A Stock Has Finished .")

    def getAStockCodesFromCsv(self):
        '''
        获取股票代码清单，链接数据库
        '''
        file_path=os.path.join(os.getcwd(),'Stock.csv')
        stock_code = pd.read_csv(filepath_or_buffer=file_path, encoding='gbk')
        Code=stock_code.code
        return Code

    def getAStockCodesWind(end_date=time.strftime('%Y%m%d',time.localtime(time.time()))):
        '''
        通过wset数据集获取所有A股股票代码，深市代码为股票代码+SZ后缀，沪市代码为股票代码+SH后缀。
        如设定日期参数，则获取参数指定日期所有A股代码，不指定日期参数则默认为当前日期
        :return: 指定日期所有A股代码，不指定日期默认为最新日期
        '''
        w.start()
        #加日期参数取最指定日期股票代码
        #stockCodes=w.wset("sectorconstituent","date="+end_date+";sectorid=a001010100000000;field=wind_code")
        #不加日期参数取最新股票代码
        stockCodes=w.wset("sectorconstituent","sectorid=a001010100000000;field=wind_code")
        return stockCodes.Data[0]
        #return stockCodes

def main():
    '''
    主调函数，可以通过参数调整实现分批下载
    '''
    global engine,sleep_time,symbols
    sleep_time=5
    windStock=WindStock()
    engine = create_engine('mysql://root:root@localhost/invest?charset=utf8')
    #start_date='20100101'
    #end_date='20131231'
    #symbols=windStock.getAStockCodesFromCsv()#通过文件获取股票代码
    #symbols=windStock.getAStockCodesWind()
    #通过Wind API获取股票代码,默认取最新的，可以指定取历史某一日所有A股代码
    #symbols=['000001.SZ', '000002.SZ', '000004.SZ']#通过直接赋值获取股票代码用于测试
    #print (symbols)
    #windStock.AStockHisData(symbols,start_date,end_date)
    for i in range(2013,1990,-1):
         start_date=str(i)+'0101'
         end_date=str(i)+'1231'
         print (start_date,end_date,'Starting')
         symbols=windStock.getAStockCodesWind()
         windStock.AStockHisData(symbols,start_date,end_date)
         print (start_date,end_date,'Finished')



def test():
    '''
    测试脚本，新增和优化功能时使用
    '''
    symbol='000001.SZ'
    start_date='20170101'
    end_date='20170109'
    #w.start();
    #stock=w.wsd(symbol,'trade_code,open,high,low,close')
    #stock=w.wsd(symbol, "trade_status,open,high,low,close,pre_close,volume,amt,dealnum,chg,pct_chg,vwap, adjfactor,close2,turn,free_turn,oi,oi_chg,pre_settle,settle,chg_settlement,pct_chg_settlement, lastradeday_s,last_trade_day,rel_ipo_chg,rel_ipo_pct_chg,susp_reason,close3, pe_ttm,val_pe_deducted_ttm,pe_lyr,pb_lf,ps_ttm,ps_lyr,dividendyield2,ev,mkt_cap_ard,pb_mrq,pcf_ocf_ttm,pcf_ncf_ttm,pcf_ocflyr,pcf_nflyr", start_date,end_date)
    #stock=w.wsd("000001.SZ", "pre_close,open,high,low,close,volume,amt,dealnum,chg,pct_chg,vwap,adjfactor,close2,turn,free_turn,oi,oi_chg,pre_settle,settle,chg_settlement,pct_chg_settlement,lastradeday_s,last_trade_day,rel_ipo_chg,rel_ipo_pct_chg,trade_status,susp_reason,close3", "2016-12-09", "2017-01-07", "adjDate=0")
    #print (stock)

    for i in range(2014,1990,-1):
         start_date=str(i)+'0101'
         end_date=str(i)+'1231'
         print (start_date,end_date)

if __name__ == "__main__":
    main()
