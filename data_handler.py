import datetime
import talib
import numpy as np
import pandas as pd
import scipy.stats as stats
import scipy.signal as signal

def conv_date(d):
    if type(d).__name__ == 'datetime64':
        d = pd.to_datetime(str(d)).date()
    return d

def date_datetime64(d):
    if type(d).__name__ == 'datetime64':
        return d
    dt = d
    if type(d).__name__ == 'date':
        dt = datetime.datetime.combine(d, datetime.time(0,0,0))
    return np.datetime64(dt)

class DynamicRecArray(object):
    def __init__(self, dtype = [], dataframe = None):
        if isinstance(dataframe, pd.DataFrame) and (len(dataframe) > 0):
            self.create_from_df(dataframe)
        else:
            self.dtype = np.dtype(dtype)
            self.length = 0
            self.size = 100
            self._data = np.empty(self.size, dtype=self.dtype)

    def __len__(self):
        return self.length

    def append(self, rec):
        if self.length == self.size:
            self.size = int(1.5*self.size)
            self._data = np.resize(self._data, self.size)        
        self._data[self.length] = rec
        self.length += 1

    def append_by_dict(self, data_dict):
        if self.length == self.size:
            self.size = int(1.5*self.size)
            self._data = np.resize(self._data, self.size)        
        for name in self.dtype.names:
            try:
                #data = data_dict[name]
                #if ('datetime64' in self.dtype[name].name) and type(data_dict[name]).__name__ in ['date', 'datetime']:
                #    data = date_datetime64(data)
                self._data[name][self.length] = data_dict[name]
            except:
                continue
        self.length += 1

    def remove_lastn(self, n):
        self.length -= n

    def extend(self, recs):
        for rec in recs:
            self.append(rec)
    
    def extend_from_df(self, df):
        df_len = len(df)
        if (self.size - self.length) <= df_len * 1.5:
            self.size = self.length + int(1.5 * df_len)
            self._data = np.resize(self._data, self.size)
        s_idx = self.length
        e_idx = self.length + df_len
        for name in self.dtype.names:
            if name in df.columns:
                self._data[name][s_idx:e_idx] = df[name].values

    def create_from_df(self, df, need_index = False):
        df_len = len(df)
        self.size = int(1.5 * df_len)
        self._data = np.resize(np.array(df.to_records(index = need_index)), self.size)
        self.dtype = self._data.dtype
        self.length = df_len
        
    @property
    def data(self):
        return self._data[:self.length]
        
def ohlcsum(df):
    return pd.Series([df.index[0], df['open'][0], df['high'].max(), df['low'].min(), df['close'][-1], df['volume'].sum()],
                  index = ['datetime', 'open','high','low','close','volume'])

def min_freq_group(mdf, freq = 5, index_col = 'datetime'):
    if index_col == None:
        mdf = mdf.set_index('datetime')
    min_cnt = (mdf['min_id']/100).astype(int)*60 + (mdf['min_id'] % 100)
    mdf['min_idx'] = (min_cnt/freq).astype(int)
    mdf['date_idx'] = mdf.index.date
    xdf = mdf.groupby([mdf['date_idx'], mdf['min_idx']]).apply(ohlcsum).reset_index()
    if index_col != None:
        xdf = xdf.set_index('datetime')
    return xdf

def day_split(mdf, minlist = [1500], index_col = 'datetime'):
    if index_col == None:
        mdf = mdf.set_index('datetime')
    mdf['min_idx'] = 0
    for idx, mid in enumerate(minlist):
        mdf.loc[mdf['min_id']>=mid, 'min_idx'] = idx + 1
    mdf['date_idx'] = mdf.index.date
    xdf = mdf.groupby([mdf['date_idx'], mdf['min_idx']]).apply(ohlcsum).reset_index()
    if index_col != None:
        xdf = xdf.set_index('datetime')
    return xdf

def array_split_by_bar(darr, split_list = [300, 1500, 2100], field = 'min_id'):
    s_idx = 0
    sparr = DynamicRecArray(dtype = darr.dtype)
    ind = np.zeros(len(darr))
    for i in range(1, len(split_list)-1):
        ind[(darr[field]>=split_list[i]) & (darr[field]<split_list[i+1])] = i
    for i in range(len(darr)):
        if (i == len(darr)-1) or (darr['date'][s_idx] != darr['date'][i+1]) or (ind[s_idx] != ind[i+1]):
            tmp = darr[s_idx:(i+1)]
            data_dict = {'datetime': tmp['datetime'][0], 'date': tmp['date'][0], 'open': tmp['open'][0], \
                         'high': tmp['high'].max(), 'low': tmp['low'].min(), 'close': tmp['close'][-1], \
                         'volume': tmp['volume'].sum(), 'openInterest': tmp['openInterest'][-1], 'min_id': tmp['min_id'][-1]}
            sparr.append_by_dict(data_dict)
            s_idx = i+1
    return sparr

def min2daily(df, extra_cols = []):
    ts = [df.index[0], df['min_id'][-1], df['open'][0], df['high'].max(), df['low'].min(), df['close'][-1], df['volume'].sum(), df['openInterest'][-1]]
    col_idx = ['datetime', 'min_id', 'open','high','low','close','volume', 'openInterest']
    for col in extra_cols:
        ts.append(df[col][-1])
        col_idx.append(col)
    return pd.Series(ts, index = col_idx)

def bar_conv_func(min_ts, bar_shift = []):
    if type(min_ts).__name__ == 'Series':
        bar_ts = (min_ts/100).astype('int') * 60 + min_ts % 100
        for pair in bar_shift:
            bar_ts[min_ts >= pair[0]] += pair[1]
        return bar_ts
    else:
        bar_id = int(min_ts/100)*60 + min_ts % 100
        for pair in bar_shift:
            if min_ts >= pair[0]:
                bar_id += pair[1]
        return bar_id

def bar_conv_func2(min_ts):
    if type(min_ts).__name__ == 'Series':
        bar_ts = (min_ts/100).astype('int') * 60 + min_ts % 100
        return bar_ts
    else:
        bar_id = int(min_ts/100) * 60 + min_ts % 100
        return bar_id

def conv_ohlc_freq(mdf, freq, index_col = 'datetime', bar_func = bar_conv_func2, extra_cols = []):
    df = mdf.copy(deep=True)
    min_func = lambda df: min2daily(df, extra_cols)
    if index_col == None:
        df = df.set_index('datetime')
    if freq in ['d', 'D']:
        res = df.groupby([df['date']]).apply(min_func).reset_index().set_index(['date'])
    else:
        if freq[-3:] in ['min', 'Min']:
            f = int(freq[:-3])
        elif freq[-1:] in ['m', 'M']:
            f = int(freq[:-1])
        df['grp_id'] = pd.Series((bar_func(df['min_id'])/f).astype('int'), name = 'grp_id')
        res = df.groupby([df['date'], df['grp_id']]).apply(min_func).reset_index()
        res.drop('grp_id', axis = 1, inplace=True)
        if index_col == 'datetime':
            res.set_index(index_col, inplace = True)
    return res

def conv_ohlc_freq2(df, freq, index_col = 'datetime'):
    if index_col == None:
        df = df.set_index('datetime')
    if freq in ['d', 'D']:
        res = df.groupby([df['date']]).apply(min2daily).reset_index().set_index(['date'])
    else:
        highcol = pd.DataFrame(df['high']).resample(freq, how ='max').dropna()
        lowcol  = pd.DataFrame(df['low']).resample(freq, how ='min').dropna()
        opencol = pd.DataFrame(df['open']).resample(freq, how ='first').dropna()
        closecol= pd.DataFrame(df['close']).resample(freq, how ='last').dropna()
        allcol = [opencol, highcol, lowcol, closecol]
        sort_cols = []
        if 'volume' in df.columns:
            volcol  = pd.DataFrame(df['volume']).resample(freq, how ='sum').dropna()
            allcol.append(volcol)
        if 'date' in df.columns:
            datecol  = pd.DataFrame(df['date']).resample(freq, how ='last').dropna()
            allcol.append(datecol)
            sort_cols.append('date')
        if 'min_id' in df.columns:
            mincol  = pd.DataFrame(df['min_id']).resample(freq, how ='last').dropna()
            allcol.append(mincol)
            sort_cols.append('min_id')
        if 'openInterest' in df.columns:
            volcol  = pd.DataFrame(df['openInterest']).resample(freq, how ='last').dropna()
            allcol.append(volcol)
        if 'contract' in df.columns:
            mincol  = pd.DataFrame(df['contract']).resample(freq, how ='first').dropna()
            allcol.append(mincol)
        res =  pd.concat(allcol, join='outer', axis =1)
        if len(sort_cols) > 0:
            res = res.sort_values(by = sort_cols)
        if index_col == None:
            res = res.reset_index()
    return res

def crossover(ts, value = 0, direction = 1):
    return ((ts[-1] - value)*direction>0) and ((ts[-2] - value)*direction<0)

def crossover2(ts1, ts2, value = 0, direction = 1):
    return ((ts1[-1] - ts2[-1] - value)*direction>0) and ((ts1[-2] - ts2[-2] - value)*direction<0)

def TR(df):
    tr_df = pd.concat([df['high'] - df['close'], abs(df['high'] - df['close'].shift(1)), abs(df['low'] - df['close'].shift(1))], join='outer', axis=1)
    ts_tr = pd.Series(tr_df.max(1), name='TR')
    return ts_tr

def tr(df):
    if np.isnan(df['TR'][-1]):
        df['TR'][-1] = max(df['high'][-1]-df['low'][-1], abs(df['high'][-1] - df['close'][-2]), abs(df['low'][-1] - df['close'][-2]))

def CMI(df, n):
    ts = pd.Series(abs(df['close'] - df['close'].shift(n))/(pd.rolling_max(df['high'], n) - pd.rolling_min(df['low'], n))*100, name='CMI'+str(n))
    return ts

def cmi(df, n):
    key = 'CMI'+str(n)
    if (len(df) >= n) and np.isnan(df[key][-1]):
        df[key][-1] = abs(df['close'][-1] - df['close'][-n])/(max(df['high'][-n:]) - min(df['low'][-n:]))*100

def ATR(df, n = 20):
    tr = TR(df)
    ts_atr = pd.ewma(tr, span=n,  min_periods = n-1, adjust = False)
    ts_atr.name = 'ATR'+str(n)
    return ts_atr

def atr(df, n = 20):
    
    new_tr = max(df['high'][-1]-df['low'][-1], abs(df['high'][-1] - df['close'][-2]), abs(df['low'][-1] - df['close'][-2]))
    alpha = 2.0/(n+1)
    df['ATR'+str(n)][-1] = df['ATR'+str(n)][-2] * (1-alpha) + alpha * new_tr

# talib matype: 0=SMA, 1=EMA, 2=WMA, 3=DEMA, 4=TEMA, 5=TRIMA, 6=KAMA, 7=MAMA, 8=T3
def MAEXT(df, n, field = 'close', ma_type = 0):
    return pd.Series(talib.MA(df[field].values, timeperiod = n, matype = ma_type), index = df.index, name = 'MA_' + field[0].upper() + str(n))

def maext(df, n, field = 'close', ma_type = 0):
    key = 'MA_' + field[0].upper() + str(n)
    ma_ts = talib.MA(df[field][-(n+1):].values, timeperiod = n, matype = ma_type)
    df[key][-1] = float(ma_ts[-1])
    
def MA(df, n, field = 'close'):
    return pd.Series(pd.rolling_mean(df[field], n), name = 'MA_' + field[0].upper() + str(n), index = df.index)

def ma(df, n, field = 'close'):
    key = 'MA_' + field[0].upper() + str(n)
    df[key][-1] = (df[key][-2]*n + df[field][-1] - df[field][-1-n])/n

def STDEV(df, n, field = 'close'):
    return pd.Series(pd.rolling_std(df[field], n), name = 'STDEV_' + field[0].upper() + str(n))

def stdev(df, n, field = 'close'):
    df['STDEV_' + field[0].upper() + str(n)][-1] = np.std(df[field][-n:])

#Exponential Moving Average
def EMA(df, n, field = 'close'):
    return pd.Series(talib.EMA(df[field].values, n), name = 'EMA_' + field[0].upper() + str(n), index = df.index)

def ema(df, n, field =  'close'):    
    key = 'EMA_' + field[0].upper() + str(n)
    if np.isnan(df[key][-1]):
        alpha = 2.0/(n+1)
        df[key][-1] = df[key][-2] * (1-alpha) + df[field][-1] * alpha

def KAMA(df, n, field = 'close'):
    return pd.Series(talib.KAMA(df[field].values, n), name = 'KAMA_' + field[0].upper() + str(n), index = df.index)

#Momentum
def MOM(df, n):
    return pd.Series(df['close'].diff(n), name = 'Momentum' + str(n))#Rate of Change

def ROC(df, n):
    M = df['close'].diff(n - 1)
    N = df['close'].shift(n - 1)
    return pd.Series(M / N, name = 'ROC' + str(n))

#Bollinger Bands
def BBANDS(df, n, k = 2):
    MA = pd.Series(pd.rolling_mean(df['close'], n))
    MSD = pd.Series(pd.rolling_std(df['close'], n))
    b1 = 2 * k * MSD / MA
    B1 = pd.Series(b1, name = 'BollingerB' + str(n))
    b2 = (df['close'] - MA + k * MSD) / (2 * k * MSD)
    B2 = pd.Series(b2, name = 'Bollingerb' + str(n))
    return pd.concat([B1,B2], join='outer', axis=1)

#Pivot Points, Supports and Resistances
def PPSR(df):
    PP = pd.Series((df['high'] + df['low'] + df['close']) / 3)
    R1 = pd.Series(2 * PP - df['low'])
    S1 = pd.Series(2 * PP - df['high'])
    R2 = pd.Series(PP + df['high'] - df['low'])
    S2 = pd.Series(PP - df['high'] + df['low'])
    R3 = pd.Series(df['high'] + 2 * (PP - df['low']))
    S3 = pd.Series(df['low'] - 2 * (df['high'] - PP))
    psr = {'PP':PP, 'R1':R1, 'S1':S1, 'R2':R2, 'S2':S2, 'R3':R3, 'S3':S3}
    PSR = pd.DataFrame(psr)
    return PSR

#Stochastic oscillator %K    
def STOCH(df, n = 14, slowk_period = 3, slowd_period = 3):
    fastk, fastd = talib.STOCHF(df['high'].values, df['low'].values, df['close'].values, fastk_period = n, fastd_period=slowk_period)
    slowk, slowd = talib.STOCH(df['high'].values, df['low'].values, df['close'].values, fastk_period = n, slowk_period=slowk_period, slowd_period=slowd_period)
    fk = pd.Series(fastk, index = df.index, name = "STOCHFK_%s_%s_%s" % (str(n), str(slowk_period), str(slowd_period)))
    sk = pd.Series(slowk, index = df.index, name = "STOCHSK_%s_%s_%s" % (str(n), str(slowk_period), str(slowd_period)))
    sd = pd.Series(slowd, index = df.index, name = "STOCHSD_%s_%s_%s" % (str(n), str(slowk_period), str(slowd_period)))
    return pd.concat([fk, sk, sd], join='outer', axis=1)
    
def STOCHF(df, n = 14, fastd_period = 3):
    fastk, fastd = talib.STOCHF(df['high'].values, df['low'].values, df['close'].values, fastk_period = n, fastd_period=fastd_period)
    fk = pd.Series(fastk, index = df.index, name = "STOCFK_%s_%s" % (str(n), str(fastd_period)))
    sk = pd.Series(fastd, index = df.index, name = "STOCSK_%s_%s" % (str(n), str(fastd_period)))
    return pd.concat([fk, sk], join='outer', axis=1)
    
def stoch(df, n = 14, slowk_period = 3, slowd_period = 3):    
    key1 = "STOCHFK_%s_%s_%s" % (str(n), str(slowk_period), str(slowd_period))
    df[key1][-1] = (df['close'][-1] - min(df['low'][-n:]))/(max(df['high'][-n:]) - min(df['low'][-n:]))*100
    alpha = 2.0/(slowk_period+1)
    key2 = "STOCHSK_%s_%s_%s" % (str(n), str(slowk_period), str(slowd_period))
    df[key2][-1] = df[key2][-2] * (1- alpha) + df[key1][-1] * alpha
    alpha = 2.0/(slowd_period+1)
    key3 = "STOCHSD_%s_%s_%s" % (str(n), str(slowk_period), str(slowd_period))    
    df[key3][-1] = df[key3][-2] * (1-alpha) + df[key2][-1] * alpha

def stochf(df, n = 14, fastd_period = 3):    
    key1 = "STOCHFK_%s_%s" % (str(n), str(fastd_period))
    df[key1][-1] = (df['close'][-1] - min(df['low'][-n:]))/(max(df['high'][-n:]) - min(df['low'][-n:]))*100
    alpha = 2.0/(fastd_period+1)
    key2 = "STOCHSK_%s_%s" % (str(n), str(fastd_period))
    df[key2][-1] = df[key2][-2] * (1- alpha) + df[key1][-1] * alpha
    
def STOCHRSI(df, n=14, fastk_period=5, fastd_period=3):
    fastk, fastd = STOCHRSI(df['close'].valkues, timeperiod = n, fastk_period= fastk_period, fastd_period=fastd_period)
    fk = pd.Series(fastk, index = df.index, name = "STOCRSI_FK_%s" % (str(n)))
    fd = pd.Series(fastd, index = df.index, name = "STOCRSI_FD_%s" % (str(n)))   
    return pd.concat([fk,fd], join='outer', axis=1)
    
    #Trix
def TRIX(df, n):
    EX1 = pd.ewma(df['close'], span = n, min_periods = n - 1, adjust = False)
    EX2 = pd.ewma(EX1, span = n, min_periods = n - 1, adjust = False)
    EX3 = pd.ewma(EX2, span = n, min_periods = n - 1, adjust = False)
    return pd.Series(EX3/EX3.shift(1) - 1, name = 'Trix' + str(n))

#Average Directional Movement Index
def ADX(df, n):
    return pd.Series(talib.ADX(df['high'].values, df['low'].values, df['close'].values, timeperiod = n), index = df.index, name = 'ADX_%s' % str(n))
    # UpMove = df['high'] - df['high'].shift(1)
    # DoMove = df['low'].shift(1) - df['low']
    # UpD = pd.Series(UpMove)
    # DoD = pd.Series(DoMove)
    # UpD[(UpMove<=DoMove)|(UpMove <= 0)] = 0
    # DoD[(DoMove<=UpMove)|(DoMove <= 0)] = 0
    # ATRs = ATR(df,span = n, min_periods = n)
    # PosDI = pd.Series(pd.ewma(UpD, span = n, min_periods = n - 1) / ATRs)
    # NegDI = pd.Series(pd.ewma(DoD, span = n, min_periods = n - 1) / ATRs)
    # ADX = pd.Series(pd.ewma(abs(PosDI - NegDI) / (PosDI + NegDI), span = n_ADX, min_periods = n_ADX - 1), name = 'ADX' + str(n) + '_' + str(n_ADX))
    # return ADX 

def ADXR(df, n):
    return pd.Series(talib.ADXR(df['high'].values, df['low'].values, df['close'].values, timeperiod = n), index = df.index, name = 'ADXR_%s' % str(n))
    
#MACD, MACD Signal and MACD difference
def MACD(df, n_fast, n_slow, n_signal):
    EMAfast = pd.Series(pd.ewma(df['close'], span = n_fast, min_periods = n_slow - 1))
    EMAslow = pd.Series(pd.ewma(df['close'], span = n_slow, min_periods = n_slow - 1))
    MACD = pd.Series(EMAfast - EMAslow, name = 'MACD' + str(n_fast) + '_' + str(n_slow) + '_' + str(n_signal))
    MACDsig = pd.Series(pd.ewma(MACD, span = n_signal, min_periods = n_signal - 1), name = 'MACDsig' + str(n_fast) + '_' + str(n_slow) + '_' + str(n_signal))
    MACDhist = pd.Series(MACD - MACDsig, name = 'MACDhist' + str(n_fast) + '_' + str(n_slow) + '_' + str(n_signal))
    return pd.concat([MACD, MACDsig, MACDhist], join='outer', axis=1)

def MACDEXT(df, n_fast, n_slow, n_signal, matype = 0):
    macd, macdsignal, macdhist = talib.MACDEXT(df['close'].values, fastperiod=n_fast, fastmatype=matype, slowperiod=n_slow, slowmatype=matype, signalperiod=n_signal, signalmatype=matype)
    MACD = pd.Series(macd, index = df.index, name = 'MACD' + str(n_fast) + '_' + str(n_slow) + '_' + str(n_signal))
    MACDsig = pd.Series(macdsignal, index = df.index, name = 'MACDsig' + str(n_fast) + '_' + str(n_slow) + '_' + str(n_signal))
    MACDhist = pd.Series(macdhist, index = df.index, name = 'MACDhist' + str(n_fast) + '_' + str(n_slow) + '_' + str(n_signal))
    return pd.concat([MACD, MACDsig, MACDhist], join='outer', axis=1)

#Mass Index
def MassI(df):
    Range = df['high'] - df['low']
    EX1 = pd.ewma(Range, span = 9, min_periods = 8)
    EX2 = pd.ewma(EX1, span = 9, min_periods = 8)
    Mass = EX1 / EX2
    MassI = pd.Series(pd.rolling_sum(Mass, 25), name = 'MassIndex')
    return MassI

#Vortex Indicator
def Vortex(df, n):
    tr = TR(df)
    vm = abs(df['high'] - df['low'].shift(1)) - abs(df['low']-df['high'].shift(1))
    VI = pd.Series(pd.rolling_sum(vm, n) / pd.rolling_sum(tr, n), name = 'Vortex' + str(n))
    return VI

#KST Oscillator
def KST(df, r1, r2, r3, r4, n1, n2, n3, n4):
    M = df['close'].diff(r1 - 1)
    N = df['close'].shift(r1 - 1)
    ROC1 = M / N
    M = df['close'].diff(r2 - 1)
    N = df['close'].shift(r2 - 1)
    ROC2 = M / N
    M = df['close'].diff(r3 - 1)
    N = df['close'].shift(r3 - 1)
    ROC3 = M / N
    M = df['close'].diff(r4 - 1)
    N = df['close'].shift(r4 - 1)
    ROC4 = M / N
    KST = pd.Series(pd.rolling_sum(ROC1, n1) + pd.rolling_sum(ROC2, n2) * 2 + pd.rolling_sum(ROC3, n3) * 3 + pd.rolling_sum(ROC4, n4) * 4, name = 'KST' + str(r1) + '_' + str(r2) + '_' + str(r3) + '_' + str(r4) + '_' + str(n1) + '_' + str(n2) + '_' + str(n3) + '_' + str(n4))
    return KST

#Relative Strength Index
def RSI(df, n, field='close'):
    return pd.Series(talib.RSI(df[field].values, n), index = df.index, name='RSI_%s' % str(n))
    #UpMove = df[field] - df[field].shift(1)
    #DoMove = df[field].shift(1) - df[field]
    #UpD = pd.Series(UpMove)
    #DoD = pd.Series(DoMove)
    #UpD[(UpMove<=DoMove)|(UpMove <= 0)] = 0
    #DoD[(DoMove<=UpMove)|(DoMove <= 0)] = 0
    #PosDI = pd.Series(pd.ewma(UpD, span = n, min_periods = n - 1))
    #NegDI = pd.Series(pd.ewma(DoD, span = n, min_periods = n - 1))
    #RSI = pd.Series(PosDI / (PosDI + NegDI) * 100, name = 'RSI' + str(n))
    #return RSI

def rsi(df, n, field = 'close'):
    RSI_key = 'RSI_%s' % str(n)
    df[RSI_key][-1] = talib.RSI(df[field][(-n-1):], n)[-1]
    
#True Strength Index
def TSI(df, r, s):
    M = pd.Series(df['close'].diff(1))
    aM = abs(M)
    EMA1 = pd.Series(pd.ewma(M, span = r, min_periods = r - 1))
    aEMA1 = pd.Series(pd.ewma(aM, span = r, min_periods = r - 1))
    EMA2 = pd.Series(pd.ewma(EMA1, span = s, min_periods = s - 1))
    aEMA2 = pd.Series(pd.ewma(aEMA1, span = s, min_periods = s - 1))
    TSI = pd.Series(EMA2 / aEMA2, name = 'TSI' + str(r) + '_' + str(s))
    return TSI

#Accumulation/Distribution
def ACCDIST(df, n):
    ad = (2 * df['close'] - df['high'] - df['low']) / (df['high'] - df['low']) * df['volume']
    M = ad.diff(n - 1)
    N = ad.shift(n - 1)
    ROC = M / N
    AD = pd.Series(ROC, name = 'Acc/Dist_ROC' + str(n))
    return AD

#Chaikin Oscillator
def Chaikin(df):
    ad = (2 * df['close'] - df['high'] - df['low']) / (df['high'] - df['low']) * df['volume']
    Chaikin = pd.Series(pd.ewma(ad, span = 3, min_periods = 2) - pd.ewma(ad, span = 10, min_periods = 9), name = 'Chaikin')
    return Chaikin

#Money Flow Index and Ratio
def MFI(df, n):
    PP = (df['high'] + df['low'] + df['close']) / 3
    PP = PP.shift(1)
    PosMF = pd.Series(PP)
    PosMF[PosMF <= PosMF.shift(1)] = 0
    PosMF = PosMF * df['volume']
    TotMF = PP * df['volume']
    MFR = pd.Series(PosMF / TotMF)
    MFI = pd.Series(pd.rolling_mean(MFR, n), name = 'MFI' + str(n))
    return MFI

#On-balance Volume
def OBV(df, n):
    PosVol = pd.Series(df['volume'])
    NegVol = pd.Series(-df['volume'])
    PosVol[df['close'] <= df['close'].shift(1)] = 0
    NegVol[df['close'] >= df['close'].shift(1)] = 0
    OBV = pd.Series(pd.rolling_mean(PosVol + NegVol, n), name = 'OBV' + str(n))
    return OBV

#Force Index
def FORCE(df, n):
    F = pd.Series(df['close'].diff(n) * df['volume'].diff(n), name = 'Force' + str(n))
    return F

#Ease of Movement
def EOM(df, n):
    EoM = (df['high'].diff(1) + df['low'].diff(1)) * (df['high'] - df['low']) / (2 * df['volume'])
    Eom_ma = pd.Series(pd.rolling_mean(EoM, n), name = 'EoM' + str(n))
    return Eom_ma

#Commodity Channel Index
def CCI(df, n):
    PP = (df['high'] + df['low'] + df['close']) / 3
    CCI = pd.Series((PP - pd.rolling_mean(PP, n)) / pd.rolling_std(PP, n) / 0.015, name = 'CCI' + str(n))
    return CCI

def cci(df, n):
    real = talib.CCI(df['high'][(-n-1):], df['low'][(-n-1):], df['close'][(-n-1):], timeperiod=n)
    df['CCI' + str(n)][-1] = real[-1]
    
#Coppock Curve
def COPP(df, n):
    M = df['close'].diff(int(n * 11 / 10) - 1)
    N = df['close'].shift(int(n * 11 / 10) - 1)
    ROC1 = M / N
    M = df['close'].diff(int(n * 14 / 10) - 1)
    N = df['close'].shift(int(n * 14 / 10) - 1)
    ROC2 = M / N
    Copp = pd.Series(pd.ewma(ROC1 + ROC2, span = n, min_periods = n), name = 'Copp' + str(n))
    return Copp

#Keltner Channel
def KELCH(df, n):
    KelChM = pd.Series(pd.rolling_mean((df['high'] + df['low'] + df['close']) / 3, n), name = 'KelChM' + str(n))
    KelChU = pd.Series(pd.rolling_mean((4 * df['high'] - 2 * df['low'] + df['close']) / 3, n), name = 'KelChU' + str(n))
    KelChD = pd.Series(pd.rolling_mean((-2 * df['high'] + 4 * df['low'] + df['close']) / 3, n), name = 'KelChD' + str(n))
    return pd.concat([KelChM, KelChU, KelChD], join='outer', axis=1)

#Ultimate Oscillator
def ULTOSC(df):
    TR_l = TR(df)
    BP_l = df['close'] - pd.concat([df['low'], df['close'].shift(1)], axis=1).min(axis=1)
    UltO = pd.Series((4 * pd.rolling_sum(BP_l, 7) / pd.rolling_sum(TR_l, 7)) + (2 * pd.rolling_sum(BP_l, 14) / pd.rolling_sum(TR_l, 14)) + (pd.rolling_sum(BP_l, 28) / pd.rolling_sum(TR_l, 28)), name = 'UltOsc')
    return UltO

def DONCH_IDX(df, n):
    high = pd.Series(pd.rolling_max(df['high'], n), name = 'DONCH_H'+ str(n))
    low  = pd.Series(pd.rolling_min(df['low'], n), name = 'DONCH_L'+ str(n))
    maxidx = pd.Series(index=df.index, name = 'DONIDX_H%s' % str(n))
    minidx = pd.Series(index=df.index, name = 'DONIDX_L%s' % str(n))
    for idx, dateidx in enumerate(high.index):
        if idx >= (n-1):
            highlist = list(df.iloc[(idx-n+1):(idx+1)]['high'])[::-1]
            maxidx[idx] = highlist.index(high[idx])
            lowlist = list(df.iloc[(idx-n+1):(idx+1)]['low'])[::-1]
            minidx[idx] = lowlist.index(low[idx])
    return pd.concat([high,low, maxidx, minidx], join='outer', axis=1)

def CHENOW_PLUNGER(df, n, atr_n = 40):
    atr = ATR(df, atr_n)
    high = pd.Series((pd.rolling_max(df['high'], n) - df['close'])/atr, name = 'CPLUNGER_H'+ str(n))
    low  = pd.Series((df['close'] - pd.rolling_min(df['low'], n))/atr, name = 'CPLUNGER_L'+ str(n))
    return pd.concat([high,low], join='outer', axis=1)

#Donchian Channel
def DONCH_H(df, n, field = 'high'):
    DC_H = pd.rolling_max(df[field],n)
    return pd.Series(DC_H, name = 'DONCH_H' + field[0].upper() + str(n))

def DONCH_L(df, n, field = 'low'):
    DC_L = pd.rolling_min(df[field], n)
    return pd.Series(DC_L, name = 'DONCH_L'+ field[0].upper() + str(n))

def donch_h(df, n, field = 'high'):
    key = 'DONCH_H'+ field[0].upper() + str(n)
    if np.isnan(df[key][-1]):
        df[key][-1] = max(df[field][-n:])
 
def donch_l(df, n, field = 'low'):
    key = 'DONCH_L'+ field[0].upper() + str(n)
    if np.isnan(df[key][-1]):    
        df[key][-1] = min(df[field][-n:])
    
#Standard Deviation
def HEIKEN_ASHI(df, period1):
    SM_O = pd.rolling_mean(df['open'], period1)
    SM_H = pd.rolling_mean(df['high'], period1)
    SM_L = pd.rolling_mean(df['low'], period1)
    SM_C = pd.rolling_mean(df['close'], period1)
    HA_C = pd.Series((SM_O + SM_H + SM_L + SM_C)/4.0, name = 'HAclose')
    HA_O = pd.Series(SM_O, name = 'HAopen')
    HA_H = pd.Series(SM_H, name = 'HAhigh')
    HA_L = pd.Series(SM_L, name = 'HAlow')
    for idx, dateidx in enumerate(HA_C.index):
        if idx >= (period1):
            HA_O[idx] = (HA_O[idx-1] + HA_C[idx-1])/2.0
        HA_H[idx] = max(SM_H[idx], HA_O[idx], HA_C[idx])
        HA_L[idx] = min(SM_L[idx], HA_O[idx], HA_C[idx])
    return pd.concat([HA_O, HA_H, HA_L, HA_C], join='outer', axis=1)
    
def heiken_ashi(df, period):
    ma_o = sum(df['open'][-period:])/float(period)
    ma_c = sum(df['close'][-period:])/float(period)
    ma_h = sum(df['high'][-period:])/float(period)
    ma_l = sum(df['low'][-period:])/float(period)
    df['HAclose'][-1] = (ma_o + ma_c + ma_h + ma_l)/4.0
    df['HAopen'][-1] = (df['HAopen'][-2] + df['HAclose'][-2])/2.0
    df['HAhigh'][-1] = max(ma_h, df['HAopen'][-1], df['HAclose'][-1])
    df['HAlow'][-1] = min(ma_l, df['HAopen'][-1], df['HAclose'][-1])

def BBANDS_STOP(df, n, nstd):
    MA = pd.Series(pd.rolling_mean(df['close'], n))
    MSD = pd.Series(pd.rolling_std(df['close'], n))
    Upper = pd.Series(MA + MSD * nstd, name = 'BBSTOP_upper')
    Lower = pd.Series(MA - MSD * nstd, name = 'BBSTOP_lower')
    Trend = pd.Series(0, index = Lower.index, name = 'BBSTOP_trend')
    for idx, dateidx in enumerate(Upper.index):
        if idx >= n:
            Trend[idx] = Trend[idx-1]
            if (df.close[idx] > Upper[idx-1]):
                Trend[idx] = 1
            if (df.close[idx] < Lower[idx-1]):
                Trend[idx] = -1                
            if (Trend[idx]==1) and (Lower[idx] < Lower[idx-1]):
                Lower[idx] = Lower[idx-1]
            elif (Trend[idx]==-1) and (Upper[idx] > Upper[idx-1]):
                Upper[idx] = Upper[idx-1]
    return pd.concat([Upper,Lower, Trend], join='outer', axis=1)

def bbands_stop(df, n, nstd):
    ma = df['close'][-n:].mean()
    msd = df['close'][-n:].std()
    df['BBSTOP_upper'][-1] = ma + nstd * msd
    df['BBSTOP_lower'][-1] = ma - nstd * msd
    df['BBSTOP_trend'][-1] = df['BBSTOP_trend'][-2]
    if df['close'][-1] > df['BBSTOP_upper'][-2]:
        df['BBSTOP_trend'][-1] = 1
    if df['close'][-1] < df['BBSTOP_lower'][-2]:
        df['BBSTOP_trend'][-1] = -1
    if (df['BBSTOP_trend'][-1] == 1) and (df['BBSTOP_lower'][-1] < df['BBSTOP_lower'][-2]):
        df['BBSTOP_lower'][-1] = df['BBSTOP_lower'][-2]
    if (df['BBSTOP_trend'][-1] == -1) and (df['BBSTOP_upper'][-1] > df['BBSTOP_upper'][-2]):
        df['BBSTOP_upper'][-1] = df['BBSTOP_upper'][-2]

def FISHER(df, n, smooth_p = 0.7, smooth_i = 0.7):
    roll_high = pd.rolling_max(df.high, n)
    roll_low  = pd.rolling_min(df.low, n)
    price_loc = (df.close - roll_low)/(roll_high - roll_low) * 2.0 - 1
    sm_price = pd.Series(pd.ewma(price_loc, com = 1.0/smooth_p - 1, adjust = False), name = 'FISHER_P')
    fisher_ind = 0.5 * np.log((1 + sm_price)/(1 - sm_price))
    sm_fisher = pd.Series(pd.ewma(fisher_ind, com = 1.0/smooth_i - 1, adjust = False), name = 'FISHER_I')
    return pd.concat([sm_price, sm_fisher], join='outer', axis=1)

def fisher(df, n, smooth_p = 0.7, smooth_i = 0.7):
    roll_high = max(df['high'][-n:])
    roll_low  = min(df['low'][-n:])
    price_loc = (df['close'][-1] - roll_low)*2.0/(roll_high - roll_low) - 1
    df['FISHER_P'][-1] = df['FISHER_P'][-2] * (1 - smooth_p) + smooth_p * price_loc
    fisher_ind = 0.5 * np.log((1 + df['FISHER_P'][-1])/(1 - df['FISHER_P'][-1]))
    df['FISHER_I'][-1] = df['FISHER_I'][-2] * (1 - smooth_i) + smooth_i * fisher_ind

def PCT_CHANNEL(df, n = 20, pct = 50, field = 'close'):
    out = pd.Series(index=df.index, name = 'PCT%sCH%s' % (pct, n))
    for idx, d in enumerate(df.index):
        if idx >= n:
            out[d] = np.percentile(df[field].iloc[max(idx-n,0):idx], pct)
    return out

def pct_channel(df, n = 20, pct = 50, field = 'close'):
    key =  'PCT%sCH%s' % (pct, n)
    if np.isnan(df[key][-1]):
        df[key][-1] = np.percentile(df[field][-n:], pct)

def COND_PCT_CHAN(df, n = 20, pct = 50, field = 'close', direction=1):
    out = pd.Series(index=df.index, name = 'C_CH%s_PCT%s' % (n, pct))
    for idx, d in enumerate(df.index):
        if idx >= n:
            ts = df[field].iloc[max(idx-n,0):idx]
            cutoff = np.percentile(ts, pct)
            ind = (ts*direction>=cutoff*direction)
            filtered = ts[ind]
            ranks = filtered.rank(ascending=False)
            tot_s = sum([filtered[dt] * ranks[dt] * (seq + 1) for seq, dt in enumerate(filtered.index)])
            tot_w = sum([ranks[dt] * (seq + 1) for seq, dt in enumerate(filtered.index)])    
            out[d] = tot_s/tot_w
    return out
   
def VCI(df, n, rng = 8):
    if n > 7:
        varA = pd.rolling_max(df.high, rng) - pd.rolling_min(df.low, rng)
        varB = varA.shift(rng)
        varC = varA.shift(rng*2)
        varD = varA.shift(rng*3)
        varE = varA.shift(rng*4)
        avg_tr = (varA+varB+varC+varD+varE)/25.0
    else:
        tr = pd.concat([df.high - df.low, abs(df.close - df.close.shift(1))], join='outer', axis=1).max(1)
        avg_tr = pd.rolling_mean(tr, n) * 0.16
    avg_pr = (pd.rolling_mean(df.high, n) + pd.rolling_mean(df.low, n))/2.0
    VO = pd.Series((df.open - avg_pr)/avg_tr, name = 'VCIO')
    VH = pd.Series((df.high - avg_pr)/avg_tr, name = 'VCIH')
    VL = pd.Series((df.low - avg_pr)/avg_tr, name = 'VCIL')
    VC = pd.Series((df.close - avg_pr)/avg_tr, name = 'VCIC')
    return pd.concat([VO, VH, VL, VC], join='outer', axis=1)

def TEMA(ts, n):
    n = int(n)
    ts_ema1 = pd.Series( pd.ewma(ts, span = n, adjust = False), name = 'EMA' + str(n) )
    ts_ema2 = pd.Series( pd.ewma(ts_ema1, span = n, adjust = False), name = 'EMA2' + str(n) )
    ts_ema3 = pd.Series( pd.ewma(ts_ema2, span = n, adjust = False), name = 'EMA3' + str(n) )
    ts_tema = pd.Series( 3 * ts_ema1 - 3 * ts_ema2 + ts_ema3, name = 'TEMA' + str(n) )
    return ts_tema
    
def SVAPO(df, period = 8, cutoff = 1, stdev_h = 1.5, stdev_l = 1.3, stdev_period = 100):
    HA = HEIKEN_ASHI(df, 1)
    haCl = (HA.HAopen + HA.HAclose + HA.HAhigh + HA.HAlow)/4.0
    haC = TEMA( haCl, 0.625 * period )
    vave = MA(df, 5 * period, field = 'volume').shift(1)
    vc = pd.concat([df['volume'], vave*2], axis=1).min(axis=1)
    vtrend = TEMA(LINEAR_REG_SLOPE(df.volume, period), period)
    UpD = pd.Series(vc)
    DoD = pd.Series(-vc)
    UpD[(haC<=haC.shift(1)*(1+cutoff/1000.0))|(vtrend < vtrend.shift(1))] = 0
    DoD[(haC>=haC.shift(1)*(1-cutoff/1000.0))|(vtrend > vtrend.shift(1))] = 0
    delta_sum = pd.rolling_sum(UpD + DoD, period)/(vave+1)
    svapo = pd.Series(TEMA(delta_sum, period), name = 'SVAPO_%s' % period)
    svapo_std = pd.rolling_std(svapo, stdev_period)
    svapo_ub = pd.Series(svapo_std * stdev_h, name = 'SVAPO_UB%s' % period)
    svapo_lb = pd.Series(-svapo_std * stdev_l, name = 'SVAPO_LB%s' % period)
    return pd.concat([svapo, svapo_ub, svapo_lb], join='outer', axis=1)

def LINEAR_REG_SLOPE(ts, n):
    sumbars = n*(n-1)*0.5
    sumsqrbars = (n-1)*n*(2*n-1)/6.0
    lrs = pd.Series(index = ts.index, name = 'LINREGSLOPE_%s' % n)
    for idx, d in enumerate(ts.index):
        if idx >= n-1:
            y_array = ts[idx-n+1:idx+1].values
            x_array = np.arange(n-1,-1,-1)
            lrs[idx] = (n * np.dot(x_array, y_array) - sumbars * y_array.sum())/(sumbars*sumbars-n*sumsqrbars)
    return lrs

def DVO(df, w = [0.5, 0.5, 0, 0], N = 2, s = [0.5, 0.5], M = 252):
    ratio = df.close/(df.high * w[0] + df.low * w[1] + df.open * w[2] + df.close * w[3])
    theta = pd.Series(index = df.index)
    dvo = pd.Series(index = df.index, name='DV%s_%s' % (N, M))
    ss = np.array(list(reversed(s)))
    for idx, d in enumerate(ratio.index):
        if idx >= N-1:
            y = ratio[idx-N+1:idx+1].values
            theta[idx] = np.dot(y, ss)
        if idx >= M+N-2:
            ts = theta[idx-(M-1):idx+1]
            dvo[idx] = stats.percentileofscore(ts.values, theta[idx])
    return dvo

def PSAR(df, iaf = 0.02, maxaf = 0.2, incr = 0):
    if incr == 0:
        incr = iaf
    psar = pd.Series(index = df.index, name='PSAR_VAL')
    direction = pd.Series(index = df.index, name='PSAR_DIR')
    bull = True
    ep = df.low[0]
    hp = df.high[0]
    lp = df.low[0]
    af = iaf
    for idx, d in enumerate(df.index):
        if idx == 0:
            continue
        if bull:
            psar[idx] = psar[idx - 1] + af * (hp - psar[idx - 1])
        else:
            psar[idx] = psar[idx - 1] + af * (lp - psar[idx - 1])
        reverse = False
        if bull:
            if df.low[idx] < psar[idx]:
                bull = False
                reverse = True
                psar[idx] = hp
                lp = df.low[idx]
                af = iaf
        else:
            if df.high[idx] > psar[idx]:
                bull = True
                reverse = True
                psar[idx] = lp
                hp = df.high[idx]
                af = iaf
        if not reverse:
            if bull:
                if df.high[idx] > hp:
                    hp = df.high[idx]
                    af = min(af + incr, maxaf)
                psar[idx] = min(psar[idx], df.low[idx - 1], df.low[idx - 2])

            else:
                if df.low[idx] < lp:
                    lp = df.low[idx]
                    af = min(af + incr, maxaf)
                psar[idx] = max(psar[idx], df.high[idx - 1], df.high[idx - 2])
                direction[idx] = -1
        if bull:
            direction[idx] = 1
        else:
            direction[idx] = -1
    return pd.concat([psar, direction], join='outer', axis=1)

def SAR(df, incr = 0.005, maxaf = 0.02):                                           
    sar = talib.SAR(df['high'].values, df['low'].values, acceleration=incr, maximum=maxaf)
    return pd.Series(sar, index = df.index, name = "SAR")

def sar(df, incr = 0.005, maxaf = 0.02, lookback = 100):                          
    sar_val = talib.SAR(df['high'][-lookback:], df['low'][-lookback:], acceleration=incr, maximum=maxaf)
    df['SAR'][-1] = sar_val[-1]
    
def SPBFILTER(df, n1 = 40, n2 = 60, n3 = 0, field = 'close'):
    if n3 == 0:
        n3 = int((n1 + n2)/2)
    a1 = 5.0/n1
    a2 = 5.0/n2
    B = [a1-a2, a2-a1]
    A = [1, (1-a1)+(1-a2), -(1-a1)*(1-a2)]
    PB = pd.Series(signal.lfilter(B, A, df[field]), name = 'SPB_%s_%s' % (n1, n2))
    RMS = pd.Series(pd.rolling_mean(PB*PB, n3)**0.5, name = 'SPBRMS__%s_%s' % (n1, n2))
    return pd.concat([PB, RMS], join='outer', axis=1)

def spbfilter(df, n1 = 40, n2 = 60, n3 = 0, field = 'close'):
    if n3 == 0:
        n3 = int((n1 + n2)/2)
    a1 = 5.0/n1
    a2 = 5.0/n2
    SPB_key = 'SPB_%s_%s' % (n1, n2)
    RMS_key = 'SPBRMS_%s_%s' % (n1, n2)
    df[SPB_key][-1] = df[field][-1]*(a1-a2) + df[field][-2]*(a2-a1) \
                    + df[SPB_key][-2]*(2-a1-a2) - df[SPB_key][-2]*(1-a1)*(1-a2)
    df[RMS_key][-1] = np.sqrt((df[SPB_key][(-n3):]**2).mean())

def WPR(df, n):
    res = pd.Series((df['close'] - pd.rolling_min(df['low'], n))/(pd.rolling_max(df['high'], n) - pd.rolling_min(df['low'], n))*100, name = "WPR_%s" % str(n))    
    return res

def wpr(df, n):
    ll = min(df['low'][-n:])
    hh = max(df['high'][-n:])
    df['WPR_%s' % str(n)][-1] = (df['close'][-1] - ll)/(hh - ll) * 100
    
def PRICE_CHANNEL(df, n, risk = 0.3):
    hh = pd.rolling_max(df['high'], n)
    ll = pd.rolling_min(df['low'], n)
    bsmax = pd.Series(hh-(hh - ll)*(33.0-risk)/100.0, name = "PCHUP_%s" % str(risk))
    bsmin = pd.Series(ll+(hh - ll)*(33.0-risk)/100.0, name = "PCHDN_%s" % str(risk))    
    return pd.concat([bsmax, bsmin], join='outer', axis=1)

def ASCTREND(df, n, risk = 3, stop_ratio = 0.5, atr_mode = 0):
    wpr = WPR(df, n)
    uplevel = 67 + risk
    dnlevel = 33 - risk
    signal = pd.Series(0, index = df.index, name = "ASCSIG_%s" % str(n))
    trend = pd.Series(index = df.index, name = "ASCTRD_%s" % str(n))
    stop = pd.Series(index = df.index, name = "ASCSTOP_%s" % str(n))
    ind = (wpr >= uplevel) & (wpr.shift(1) < uplevel)
    signal[ind] = 1
    trend[ind] = 1
    ind = (wpr <= dnlevel) & (wpr.shift(1) > dnlevel)
    signal[ind] = -1
    trend[ind] = -1
    trend = trend.fillna(method='ffill')
    if atr_mode == 0:
        atr = ATR(df, n + 1)
    else:
        atr = pd.rolling_mean(df['high'] - df['low'], n + 1)
    stop[trend > 0] = df['low'] - stop_ratio * atr
    stop[trend < 0] = df['high'] + stop_ratio * atr
    return pd.concat([signal, trend, stop], join='outer', axis=1)
    
def MA_RIBBON(df, ma_series):
    ma_array = np.zeros([len(df), len(ma_series)])
    ema_list = []
    for idx, ma_len in enumerate(ma_series):
        ema_i = EMA(df, n = ma_len, field = 'close')
        ma_array[:, idx] = ema_i
        ema_list.append(ema_i)
    corr = np.empty([len(df)])
    pval = np.empty([len(df)])
    dist = np.empty([len(df)])
    corr[:] = np.NAN
    pval[:] = np.NAN
    dist[:] = np.NAN
    max_n = max(ma_series)
    for idy in range(len(df)):
        if idy >= max_n - 1:
            corr[idy], pval[idy] = stats.spearmanr(ma_array[idy,:], range(len(ma_series), 0, -1))
            dist[idy] = max(ma_array[idy,:]) - min(ma_array[idy,:])
    corr_ts = pd.Series(corr*100, index = df.index, name = "MARIBBON_CORR")
    pval_ts = pd.Series(pval*100, index = df.index, name = "MARIBBON_PVAL")
    dist_ts = pd.Series(dist, index = df.index, name = "MARIBBON_DIST")
    return pd.concat([corr_ts, pval_ts, dist_ts] + ema_i, join='outer', axis=1)
    
def ma_ribbon(df, ma_series):
    ma_array = np.zeros([len(df)])
    for idx, ma_len in enumerate(ma_series):
        key = 'EMA_C' + str(ma_len)
        if np.isnan(df[key][-1]):
            ema(df, ma_len, field = 'close')
        ma_array[idx] = df[key][-1]
    corr, pval = stats.spearmanr(ma_array, range(len(ma_series), 0, -1))
    dist = max(ma_array) - min(ma_array)
    df["MARIBBON_CORR"][-1] = corr * 100
    df["MARIBBON_PVAL"][-1] = pval * 100
    df["MARIBBON_DIST"][-1] = dist
    
def AROON(df, n):
    aroondown, aroonup = talib.AROON(df['high'].values, df['low'].values, timeperiod= n)
    aroon_dn = pd.Series(aroondown, index = df.index, name = "AROONDN_%s" % str(n))
    aroon_up = pd.Series(aroonup, index = df.index, name = "AROONUP_%s" % str(n))
    return pd.concat([aroon_up, aroon_dn], join='outer', axis=1)
    
def aroon(df, n):
    aroondown, aroonup = AROON(df['high'][-(n+1):], df['low'][-(n+1):], timeperiod= n)
    df["AROOONDN_%s" % str(n)][-1] = aroondown[-1]
    df["AROOONUP_%s" % str(n)][-1] = aroonup[-1]

def DT_RNG(df, win = 2, ratio = 0.7):
    if win == 0:
        tr_ts = pd.concat([(pd.rolling_max(df['high'], 2) - pd.rolling_min(df['close'], 2))*0.5,
                        (pd.rolling_max(df['close'], 2) - pd.rolling_min(df['low'], 2))*0.5,
                        df['high'] - df['close'],
                        df['close'] - df['low']],
                        join='outer', axis=1).max(axis=1)
    else:
        tr_ts = pd.concat([pd.rolling_max(df['high'], win) - pd.rolling_min(df['close'], win),
                       pd.rolling_max(df['close'], win) - pd.rolling_min(df['low'], win)],
                       join='outer', axis=1).max(axis=1)
    return pd.Series(tr_ts, name = 'DTRNG%s_%s' % (win, ratio))

def dt_rng(df, win = 2, ratio = 0.7):
    key = 'DTRNG%s_%s' % (win, ratio)
    if win > 0:
        df[key][-1] = max(max(df['high'][-win:]) - min(df['close'][-win:]),
                                max(df['close'][-win:]) - min(df['low'][-win:]))
    elif win == 0:
        df[key][-1] = max(max(df['high'][-2:]) - min(df['close'][-2:]),
                                max(df['close'][-2:]) - min(df['low'][-2:]))
        df[key][-1] = max(df[key][-1] * 0.5, df['high'][-1] - df['close'][-1],
                                df['close'][-1] - df['low'][-1])