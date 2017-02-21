#-*- coding:utf-8 -*-
import workdays
import json
import datetime
import logging
import bisect
import mysqlaccess
import trade
import trade_manager
import os
import instrument
import ctp
from gateway import *
import pandas as pd
from base import *
from misc import *
import data_handler
import backtest
from eventType import *
from eventEngine import *

min_data_list = ['datetime', 'date', 'min_id', 'bar_id', 'open', 'high','low', 'close', 'volume', 'openInterest', 'tick_min']
day_data_list = ['date', 'open', 'high','low', 'close', 'volume', 'openInterest']
dtype_map = {'date': 'datetime64[D]', 
             'datetime': 'datetime64[ms]',
             'open': 'float',
             'close': 'float',
             'high': 'float',
             'low': 'float',
             'volume': 'int',
             'openInterest': 'int',
             'min_id': 'int',
             'bar_id': 'int',
             'tick_min': 'int',            
             }

def get_tick_num(dt):
    return ((dt.hour+6)%24)*36000+dt.minute*600+dt.second*10+dt.microsecond/100000

def get_min_id(dt):
    return ((dt.hour+6)%24)*100+dt.minute

class MktDataMixin(object):
    def __init__(self, config):
        self.tick_data  = {}
        self.day_data  = {}
        self.min_data  = {}
        self.cur_min = {}
        self.cur_day = {}  		
        self.day_data_func = {}
        self.min_data_func = {}
        self.daily_data_days = config.get('daily_data_days', 25)
        self.min_data_days = config.get('min_data_days', 1)
        if 'min_func' in config:
            self.get_min_id = eval(config['min_func'])
        else:
            self.get_min_id = lambda x: int(x/1000)
        if 'bar_func' in config:
            self.conv_bar_id = eval(config['bar_func'])
        else:
            self.conv_bar_id = data_handler.bar_conv_func2            
        self.tick_db_table = config.get('tick_db_table', 'fut_tick')
        self.min_db_table  = config.get('min_db_table', 'fut_min')
        self.daily_db_table = config.get('daily_db_table', 'fut_daily')
        self.calc_func_dict = {}

    def add_instrument(self, name):
        self.tick_data[name] = []        
        dtypes = [(field, dtype_map[field]) for field in day_data_list]
        self.day_data[name]  = data_handler.DynamicRecArray(dtype = dtypes)
        dtypes = [(field, dtype_map[field]) for field in min_data_list]
        self.min_data[name]  = {1: data_handler.DynamicRecArray(dtype = dtypes)}
        self.cur_day[name]   = dict([(item, 0) for item in day_data_list])
        self.cur_min[name]   = dict([(item, 0) for item in min_data_list])
        self.day_data_func[name] = []
        self.min_data_func[name] = {}
        self.cur_min[name]['datetime'] = datetime.datetime.fromordinal(self.scur_day.toordinal())
        self.cur_min[name]['date'] = self.scur_day
        self.cur_day[name]['date'] = self.scur_day

    def register_data_func(self, inst, freq, fobj):
        if inst not in self.day_data_func:
            self.day_data_func[inst] = []
            self.min_data_func[inst] = {}
        if (fobj != None) and (fobj.name not in self.calc_func_dict):
            self.calc_func_dict[fobj.name] = fobj
        if 'd' in freq:
            for func in self.day_data_func[inst]:
                if fobj.name == func.name:
                    return False
            self.day_data_func[inst].append(self.calc_func_dict[fobj.name])
        else:
            mins = int(freq[:-1])
            if mins not in self.min_data_func[inst]:
                self.min_data_func[inst][mins] = []
            for func in self.min_data_func[inst][mins]:
                if fobj.name == func.name:
                    return False            
            if fobj != None:
                self.min_data_func[inst][mins].append(self.calc_func_dict[fobj.name])
            
    def update_min_bar(self, tick):
        inst = tick.instID
        tick_dt = tick.timestamp
        tick_id = tick.tick_id
        tick_min = self.get_min_id(tick_id)
        self.cur_min[inst]['tick_min'] = tick_min
        if (self.cur_min[inst]['min_id'] > tick_min):
            return False
        if (self.cur_day[inst]['open'] == 0.0):
            self.cur_day[inst]['open'] = tick.price
        self.cur_day[inst]['close'] = tick.price
        self.cur_day[inst]['high']  = tick.high
        self.cur_day[inst]['low']   = tick.low
        self.cur_day[inst]['openInterest'] = tick.openInterest
        self.cur_day[inst]['volume'] = tick.volume
        self.cur_day[inst]['date'] = tick_dt.date()
        for strat_name in self.inst2strat[inst]:
            self.strategies[strat_name].run_tick(tick)
        if (tick_min == self.cur_min[inst]['min_id']):
            self.tick_data[inst].append(tick)
            self.cur_min[inst]['close'] = tick.price
            if self.cur_min[inst]['high'] < tick.price:
                self.cur_min[inst]['high'] = tick.price
            if self.cur_min[inst]['low'] > tick.price:
                self.cur_min[inst]['low'] = tick.price
        else:
            last_vol = self.cur_min[inst]['volume']
            if (len(self.tick_data[inst]) > 0):
                last_tick = self.tick_data[inst][-1]
                self.cur_min[inst]['volume'] = last_tick.volume - self.cur_min[inst]['volume']
                self.cur_min[inst]['openInterest'] = last_tick.openInterest
                last_vol = last_tick.volume
            bar_id = self.min_switch(inst, False)
            self.run_min(inst, bar_id)
            self.tick_data[inst] = []
            self.cur_min[inst] = {}
            self.cur_min[inst]['open']  = self.cur_min[inst]['close'] = self.cur_min[inst]['high'] = self.cur_min[inst]['low'] = tick.price
            self.cur_min[inst]['min_id']  = self.cur_min[inst]['tick_min'] = tick_min
            self.cur_min[inst]['bar_id'] = bar_id
            self.cur_min[inst]['volume']  = last_vol
            self.cur_min[inst]['openInterest'] = tick.openInterest
            self.cur_min[inst]['datetime'] = tick_dt.replace(second=0, microsecond=0)
            self.cur_min[inst]['date'] = self.scur_day
            if tick_min>0:
                self.tick_data[inst].append(tick)
        return True
    
    def min_switch(self, inst, forced = False):
        prev_bar = self.cur_min[inst]['bar_id']
        bar_id = self.conv_bar_id(self.cur_min[inst]['tick_min'])
        if self.cur_min[inst]['min_id'] == 0:
            return bar_id
        ra = self.min_data[inst][1]
        ra.append_by_dict(self.cur_min[inst])
        for m in sorted(self.min_data_func[inst]):
            ra_m = self.min_data[inst][m]
            if ((int(bar_id/m)>int(prev_bar/m)) or forced):
                if m > 1:
                    if (int(prev_bar/m) == int(ra_m.data['bar_id'][-1]/m)) and (ra.data['date'][-1] == data_handler.conv_date(ra_m.data['date'][-1])):
                        ra_m.remove_lastn(1)
                    last_bar = ra_m.data['bar_id'][-1]
                    last_date = data_handler.conv_date(ra_m.data['date'][-1])
                    rlen = len(ra)
                    idx = 0
                    for i in range(rlen):
                        if (ra.data['date'][rlen-i-1] <= last_date) and (ra.data['bar_id'][rlen-i-1] <= last_bar):
                            idx = i
                            break
                    if idx > 0:
                        new_data = {'datetime':ra.data['datetime'][-idx], 'open':ra.data['open'][-idx], 'high':max(ra.data['high'][-idx:]), \
                                'low': min(ra.data['low'][-idx:]), 'close': ra.data['close'][-1],\
                                'volume': sum(ra.data['volume'][-idx:]), 'openInterest':ra.data['openInterest'][-1],\
                                'min_id': ra.data['min_id'][-1], 'bar_id': ra.data['bar_id'][-1], 'date':ra.data['date'][-1]}
                        ra_m.append_by_dict(new_data)                        
                for fobj in self.min_data_func[inst][m]:
                    fobj.rfunc(self.min_data[inst][m].data)
        if self.save_flag:
            event1 = Event(type=EVENT_DB_WRITE, priority = 500)
            event1.dict['data'] = self.tick_data[inst]
            event1.dict['type'] = EVENT_TICK
            event1.dict['instID'] = inst
            self.eventEngine.put(event1)
            if self.cur_min[inst]['close'] > 0:
                event2 = Event(type=EVENT_DB_WRITE, priority = 500)
                event2.dict['data'] = self.cur_min[inst]
                event2.dict['type'] = EVENT_MIN_BAR
                event2.dict['instID'] = inst
                self.eventEngine.put(event2)
        return bar_id

    def mkt_data_sod(self, tday):
        for inst in self.instruments:
            self.tick_data[inst] = []
            self.cur_min[inst] = dict([(item, 0) for item in min_data_list])
            self.cur_day[inst] = dict([(item, 0) for item in day_data_list])
            self.cur_day[inst]['date'] = tday
            self.cur_min[inst]['datetime'] = datetime.datetime.fromordinal(tday.toordinal())

    def mkt_data_eod(self):
        for inst in self.instruments:
            if (len(self.tick_data[inst]) > 0) :
                last_tick = self.tick_data[inst][-1]
                self.cur_min[inst]['volume'] = last_tick.volume - self.cur_min[inst]['volume']
                self.cur_min[inst]['openInterest'] = last_tick.openInterest
                self.min_switch(inst, True)
            if (self.cur_day[inst]['close']>0):
                new_day = { key: self.cur_day[inst][key] for key in day_data_list }
                self.day_data[inst].append_by_dict(new_day)
                for fobj in self.day_data_func[inst]:
                    fobj.rfunc(self.day_data[inst].data)
                if self.save_flag:
                    event = Event(type=EVENT_DB_WRITE, priority = 500)
                    event.dict['data'] = self.cur_day[inst]
                    event.dict['type'] = EVENT_MKTDATA_EOD
                    event.dict['instID'] = inst
                    self.eventEngine.put(event)

    def write_mkt_data(self, event):
        inst = event.dict['instID']
        type = event.dict['type']
        data = event.dict['data']
        if type == EVENT_MIN_BAR:
            mysqlaccess.insert_min_data(inst, data, dbtable = self.min_db_table)
        elif type == EVENT_TICK:
            mysqlaccess.bulkinsert_tick_data(inst, data, dbtable = self.tick_db_table)
        elif type == EVENT_MKTDATA_EOD:
            mysqlaccess.insert_daily_data(inst, data, dbtable = self.daily_db_table)
        else:
            pass

    def register_event_handler(self):
        self.eventEngine.register(EVENT_DB_WRITE, self.write_mkt_data)

class Agent(MktDataMixin):
    def __init__(self, name, tday=datetime.date.today(), config = {}):
        '''
            trader为交易对象
            tday为当前日,为0则为当日
        '''
        self.tick_id = 0
        self.timer_count = 0
        self.name = name
        self.sched_commands = []
        self.folder = str(config.get('folder', self.name + os.path.sep))
        self.live_trading = config.get('live_trading', False)
        self.realtime_tick_diff = config.get('realtime_tick_diff', 100)
        self.logger = logging.getLogger('.'.join([name, 'agent']))
        self.eod_flag = False
        self.save_flag = False
        self.scur_day = tday
        super(Agent, self).__init__(config)
        self.event_period = config.get('event_period', 1.0)
        self.eventEngine = PriEventEngine(self.event_period)
        self.instruments = {}
        self.positions = {}
        self.gateways = {}
        gateway_dict = config.get('gateway', {})
        for gateway_name in gateway_dict:
            gway_str = gateway_dict[gateway_name]['class']
            str_list = gway_str.split('.')
            gateway_class = __import__(str(str_list[0]), fromlist = [str(str_list[1])])
            for mod_name in str_list[1:]:
                gateway_class = getattr(gateway_class, mod_name)
            self.add_gateway(gateway_class, gateway_name)
        self.type2gateway = {}
        self.inst2strat = {}
        self.spread_data = {}
        self.inst2spread = {}
        self.inst2gateway = {}
        self.strat_list = []
        self.strategies = {}
        self.trade_manager = trade_manager.TradeManager(self)
        self.ref2order = {}
        strat_files = config.get('strat_files', [])
        for sfile in strat_files:
            with open(sfile, 'r') as fp:
                strat_conf = json.load(fp)
            class_str = strat_conf['class']
            strat_mod = class_str.split('.')
            if len(strat_mod) > 1:
                strat_class = getattr(__import__(str(strat_mod[0])), str(strat_mod[1]))
            else:
                strat_class = eval(class_str)
            strat_args  = strat_conf.get('config', {})
            strat = strat_class(strat_args, self)
            self.add_strategy(strat)
        self.init_init()    #init中的init,用于子类的处理

    def register_event_handler(self):
        for key in self.gateways:
            gateway = self.gateways[key]
            gateway.register_event_handler()
        self.eventEngine.register(EVENT_DB_WRITE, self.write_mkt_data)
        self.eventEngine.register(EVENT_LOG, self.log_handler)
        self.eventEngine.register(EVENT_TICK, self.run_tick)
        #self.eventEngine.register(EVENT_MIN_BAR, self.run_min)
        self.eventEngine.register(EVENT_ETRADEUPDATE, self.trade_update)
        self.eventEngine.register(EVENT_DAYSWITCH, self.day_switch)
        self.eventEngine.register(EVENT_TIMER, self.check_commands)

    def put_command(self, timestamp, command, arg = {} ): #按顺序插入
        stamps = [tstamp for (tstamp,cmd, fargs) in self.sched_commands]
        ii = bisect.bisect(stamps, timestamp)
        self.sched_commands.insert(ii,(timestamp, command, arg))

    def check_commands(self, event):
        l = len(self.sched_commands)
        curr_time = datetime.datetime.now()
        i = 0
        while(i<l and curr_time >= self.sched_commands[i][0]):
            logging.info(u'exec command:,i=%s,time=%s,command[i][1]=%s' % (i, curr_time, self.sched_commands[i][1].__name__))
            arg = self.sched_commands[i][2]
            self.sched_commands[i][1](**arg)
            i += 1
        if i>0:
            del self.sched_commands[0:i]

    def gateway_map(self, instID):
        exch = self.instruments[instID].exchange
        if exch in ['CZCE', 'DCE', 'SHFE', 'CFFEX']:
            for key in self.gateways:
                gateway = self.gateways[key]
                gway_class = type(gateway).__name__
                if ('ctp' in gway_class) or ('Ctp' in gway_class):
                    return gateway
        return None

    def add_instrument(self, name):
        if name not in self.instruments:
            if name.isdigit():
                if len(name) == 8:
                    self.instruments[name] = instrument.StockOptionInst(name)
                else:
                    self.instruments[name] = instrument.Stock(name)
            else:
                if len(name) > 10:
                    self.instruments[name] = instrument.FutOptionInst(name)
                else:
                    self.instruments[name] = instrument.Future(name)
            self.instruments[name].update_param(self.scur_day)
            if name not in self.inst2strat:
                self.inst2strat[name] = {}
            if name not in self.inst2gateway:
                gateway = self.gateway_map(name)
                if gateway != None:
                    self.inst2gateway[name] = gateway
                    subreq = VtSubscribeReq()
                    subreq.symbol = name
                    subreq.exchange = self.instruments[name].exchange
                    subreq.productClass = self.instruments[name].ptype
                    subreq.currency = self.instruments[name].ccy
                    subreq.expiry = self.instruments[name].expiry
                    gateway.subscribe(subreq)
                else:
                    self.logger.warning("No Gateway is assigned to instID = %s" % name)
            super(Agent, self).add_instrument(name)

    def add_spread(self, instIDs, weights, multiple = None):        
        key = '_'.join([str(s) for s in instIDs + weights])
        self.spread_data[key] = instrument.SpreadInst(instIDs, weights, multiple)
        self.spread_data[key].update()
        for inst in instIDs:
            if inst not in self.inst2spread:
                self.inst2spread[inst] = []
            self.inst2spread[inst].append(key)
        return self.spread_data[key]
                
    def get_underlying(self, instIDs, weights, multiple = None):
        if len(instIDs) == 1:
            key = instIDs[0]
            return self.instruments[key]
        else:
            key = '_'.join([str(s) for s in instIDs + weights])           
            if key not in self.spread_data:
                self.add_spread(instIDs, weights, multiple)
            return self.spread_data[key]

    def add_strategy(self, strat):
        if strat.name not in self.strat_list:
            self.strat_list.append(strat.name)
            self.strategies[strat.name] = strat
            for instID in strat.dep_instIDs():
                self.add_instrument(instID)
                self.inst2strat[instID][strat.name] = []
            strat.set_agent(self)

    def add_gateway(self, gateway, gateway_name=None):
        """创建接口"""
        if gateway_name not in self.gateways:
            self.gateways[gateway_name] = gateway(self, gateway_name)

    def connect(self, gateway_name):
        """连接特定名称的接口"""
        if gateway_name in self.gateways:
            gateway = self.gateways[gateway_name]
            gateway.connect()
        else:
            self.logger.warning(u'接口不存在：%s' % gateway_name)
        
    #----------------------------------------------------------------------
    def subscribe(self, subscribeReq, gateway_name):
        """订阅特定接口的行情"""
        if gateway_name in self.gateways:
            gateway = self.gateways[gateway_name]
            gateway.subscribe(subscribeReq)
        else:
            self.logger.warning(u'接口不存在：%s' %gateway_name)        
        
    #----------------------------------------------------------------------
    def send_order(self, iorder, urgent = 1):
        """对特定接口发单"""
        gateway = self.inst2gateway[iorder.instrument]
        gateway.add_order(iorder)
        if urgent:
            gateway.sendOrder(iorder)

    #----------------------------------------------------------------------
    def cancel_order(self, iorder):
        """对特定接口撤单"""
        if iorder.gateway != None:
            iorder.gateway.cancelOrder(iorder)
        else:
            self.logger.warning(u'接口不存在')

    def submit_trade(self, xtrade):
        self.trade_manager.add_trade(xtrade)

    def remove_trade(self, xtrade):
        self.trade_manager.remove_trade(xtrade)

    def log_handler(self, event):
        lvl = event.dict['level']
        self.logger.log(lvl, event.dict['data'])

    def get_eod_positions(self):
        for name in self.gateways:
            self.gateways[name].load_local_positions(self.scur_day)

    def get_all_orders(self):
        self.ref2order = {}
        for name in self.gateways:
            gway = self.gateways[name]
            gway.load_order_list(self.scur_day)
            order_dict = gway.id2order
            for local_id in order_dict:
                iorder = order_dict[local_id]
                iorder.gateway = gway
                self.ref2order[iorder.order_ref] = iorder

    def risk_by_strats(self, risk_list = ['pos']):
        # position = lots, delta, gamma, vega, theta in price
        risk_dict = {}
        sum_risk = dict([(inst, dict([(risk, 0) for risk in risk_list])) for inst in self.instruments])
        for strat_name in self.strat_list:
            strat = self.strategies[strat_name]
            risk_dict[strat_name] = strat.risk_agg(risk_list)
            for inst in risk_dict[strat_name]:
                for risk in risk_list:
                    sum_risk[inst][risk] += risk_dict[strat_name][inst][risk]
        return sum_risk, risk_dict

    def prepare_data_env(self, inst, mid_day = True):
        if  self.instruments[inst].ptype == instrument.ProductType.Option:
            return
        if self.daily_data_days > 0 or mid_day:
            #self.logger.debug('Updating historical daily data for %s' % self.scur_day.strftime('%Y-%m-%d'))
            daily_start = workdays.workday(self.scur_day, -self.daily_data_days, CHN_Holidays)
            daily_end = self.scur_day
            ddf = mysqlaccess.load_daily_data_to_df('fut_daily', inst, daily_start, daily_end, index_col = None)            
            if len(ddf) > 0:
                self.instruments[inst].price = ddf['close'].iloc[-1]
                self.instruments[inst].last_update = 0
                self.instruments[inst].prev_close = ddf['close'].iloc[-1]
                for fobj in self.day_data_func[inst]:
                    ts = fobj.sfunc(ddf)
                    if type(ts).__name__ == 'Series':
                        if ts.name in ddf.columns:
                            self.logger.warning('TimeSeries name %s is already in the columns for inst = %s' % (ts.name, inst))                    
                        ddf[ts.name]= ts
                    elif type(ts).__name__ == 'DataFrame':
                        for col_name in ts.columns:
                            if col_name in ddf.columns:
                                self.logger.warning('TimeSeries name %s is already in the columns for inst = %s' % (col_name, inst))                            
                            ddf[col_name] = ts[col_name]
            self.day_data[inst] = data_handler.DynamicRecArray(dataframe = ddf)
        if self.min_data_days > 0 or mid_day:
            #self.logger.debug('Updating historical min data for %s' % self.scur_day.strftime('%Y-%m-%d'))
            d_start = workdays.workday(self.scur_day, -self.min_data_days, CHN_Holidays)
            d_end = self.scur_day
            min_start = int(self.instruments[inst].start_tick_id/1000)
            min_end = int(self.instruments[inst].last_tick_id/1000)+1
            mdf = mysqlaccess.load_min_data_to_df('fut_min', inst, d_start, d_end, minid_start=min_start, minid_end=min_end, database = 'blueshale', index_col = None)
            mdf = backtest.cleanup_mindata(mdf, self.instruments[inst].product, index_col = None)
            mdf['bar_id'] = self.conv_bar_id(mdf['min_id'])
            if len(mdf)>0:
                min_date = mdf['date'].iloc[-1]
                if (len(self.day_data[inst])==0) or (min_date > self.day_data[inst].data['date'][-1]):
                    ddf = data_handler.conv_ohlc_freq(mdf, 'd', index_col = None)
                    self.cur_day[inst]['open'] = float(ddf.open[-1])
                    self.cur_day[inst]['close'] = float(ddf.close[-1])
                    self.cur_day[inst]['high'] = float(ddf.high[-1])
                    self.cur_day[inst]['low'] = float(ddf.low[-1])
                    self.cur_day[inst]['volume'] = int(ddf.volume[-1])
                    self.cur_day[inst]['openInterest'] = int(ddf.openInterest[-1])
                    self.cur_min[inst]['datetime'] = pd.datetime(*mdf['datetime'].iloc[-1].timetuple()[0:-3])
                    self.cur_min[inst]['date'] = mdf['date'].iloc[-1]
                    self.cur_min[inst]['open'] = float(mdf['open'].iloc[-1])
                    self.cur_min[inst]['close'] = float(mdf['close'].iloc[-1])
                    self.cur_min[inst]['high'] = float(mdf['high'].iloc[-1])
                    self.cur_min[inst]['low'] = float(mdf['low'].iloc[-1])
                    self.cur_min[inst]['volume'] = self.cur_day[inst]['volume']
                    self.cur_min[inst]['openInterest'] = self.cur_day[inst]['openInterest']
                    self.cur_min[inst]['min_id'] = int(mdf['min_id'].iloc[-1])
                    self.cur_min[inst]['bar_id'] = self.conv_bar_id(self.cur_min[inst]['min_id'])
                    self.instruments[inst].price = float(mdf['close'].iloc[-1])
                    self.instruments[inst].last_update = 0
                    #self.logger.debug('inst=%s tick data loaded for date=%s' % (inst, min_date))
                if 1 not in self.min_data_func[inst]:
                    self.min_data[inst][1] = data_handler.DynamicRecArray(dataframe = mdf)
                for m in sorted(self.min_data_func[inst]):
                    if m != 1:
                        mdf_m = data_handler.conv_ohlc_freq(mdf, str(m)+'min', index_col = None, bar_func = self.conv_bar_id, extra_cols = ['bar_id'])
                    else:
                        mdf_m = mdf
                    for fobj in self.min_data_func[inst][m]:
                        ts = fobj.sfunc(mdf_m)
                        if type(ts).__name__ == 'Series':
                            if ts.name in mdf_m.columns:
                                self.logger.warning('TimeSeries name %s is already in the columns for inst = %s' % (ts.name, inst))                        
                            mdf_m[ts.name]= ts
                        elif type(ts).__name__ == 'DataFrame':
                            for col_name in ts.columns:
                                if col_name in mdf_m.columns:
                                    self.logger.warning('TimeSeries name %s is already in the columns for inst = %s' % (col_name, inst))
                                mdf_m[col_name] = ts[col_name]                        
                    self.min_data[inst][m] = data_handler.DynamicRecArray(dataframe = mdf_m)
                    #print inst, self.min_data[inst][m].data['date'][-1] < self.cur_min[inst]['date']

    def restart(self):
        self.logger.debug('Prepare trade environment for %s' % self.scur_day.strftime('%y%m%d'))
        for inst in self.instruments:
            self.prepare_data_env(inst, mid_day = True)
        self.get_eod_positions()
        self.get_all_orders()
        self.trade_manager.initialize()
        for strat_name in self.strat_list:
            strat = self.strategies[strat_name]
            strat.initialize()
            strat_trades = self.trade_manager.get_trades_by_strat(strat.name)
            for xtrade in strat_trades:
                if xtrade.status != trade.TradeStatus.StratConfirm:
                    strat.add_live_trades(xtrade)
        for gway in self.gateways:
            gateway = self.gateways[gway]
            for inst in gateway.positions:
                gateway.positions[inst].re_calc()
            gateway.calc_margin()
            gateway.connect()
        self.eventEngine.start()
 
    def save_state(self):
        if not self.eod_flag:
            self.logger.debug(u'保存执行状态.....................')
            for gway in self.gateways:
                self.gateways[gway].save_order_list(self.scur_day)
            self.trade_manager.save_trade_list(self.scur_day, self.trade_manager.ref2trade, self.folder)
    
    def run_eod(self):
        if self.eod_flag:
            return
        print 'run EOD process'
        self.mkt_data_eod()
        if len(self.strat_list) == 0:
            self.eod_flag = True
            return
        self.trade_manager.save_pfill_trades()
        for strat_name in self.strat_list:
            strat = self.strategies[strat_name]
            strat.day_finalize()
        self.save_state()
        self.eod_flag = True
        for name in self.gateways:
            self.gateways[name].day_finalize(self.scur_day)
        self.ref2order = {}
        for inst in self.instruments:
            self.instruments[inst].prev_close = self.cur_day[inst]['close']
            self.instruments[inst].volume = 0

    def day_switch(self, event):
        newday = event.dict['date']
        if newday <= self.scur_day:
            return
        self.logger.info('switching the trading day from %s to %s, reset tick_id=%s to 0' % (self.scur_day, newday, self.tick_id))
        if not self.eod_flag:
            self.run_eod()
        self.scur_day = newday
        self.tick_id = 0
        self.timer_count = 0
        super(Agent, self).mkt_data_sod(newday)
        self.eod_flag = False
        eod_time = datetime.datetime.combine(newday, datetime.time(15, 20, 0))
        self.put_command(eod_time, self.run_eod)
                
    def init_init(self):    #init中的init,用于子类的处理
        self.register_event_handler()

    def update_instrument(self, tick):      
        inst = tick.instID    
        curr_tick = tick.tick_id
        if (self.instruments[inst].exchange == 'CZCE') and (self.instruments[inst].last_update == tick.tick_id) and \
                ((self.instruments[inst].volume < tick.volume) or (self.instruments[inst].ask_vol1 != tick.askVol1) or \
                    (self.instruments[inst].bid_vol1 != tick.bidVol1)):
                if tick.tick_id % 10 < 5:
                    tick.tick_id += 5
                    tick.timestamp = tick.timestamp + datetime.timedelta(milliseconds=500)
        self.tick_id = max(curr_tick, self.tick_id)
        self.instruments[inst].up_limit   = tick.upLimit
        self.instruments[inst].down_limit = tick.downLimit        
        tick.askPrice1 = min(tick.askPrice1, tick.upLimit)
        tick.bidPrice1 = max(tick.bidPrice1, tick.downLimit)
        self.instruments[inst].last_update = curr_tick
        self.instruments[inst].bid_price1 = tick.bidPrice1
        self.instruments[inst].ask_price1 = tick.askPrice1
        self.instruments[inst].mid_price = (tick.askPrice1 + tick.bidPrice1)/2.0
        if (self.instruments[inst].mid_price > tick.upLimit) or (self.instruments[inst].mid_price < tick.downLimit):
            return False
        self.instruments[inst].bid_vol1   = tick.bidVol1
        self.instruments[inst].ask_vol1   = tick.askVol1
        self.instruments[inst].open_interest = tick.openInterest
        last_volume = self.instruments[inst].volume       
        if tick.volume > last_volume:
            self.instruments[inst].price  = tick.price
            self.instruments[inst].volume = tick.volume
            self.instruments[inst].last_traded = curr_tick
        if inst in self.inst2spread:
            for spd_key in self.inst2spread[inst]:
                self.spread_data[spd_key].update()
        return True

    def run_tick(self, event):#行情处理主循环
        tick = event.dict['data']
        if self.live_trading:
            now_ticknum = get_tick_num(datetime.datetime.now())
            cur_ticknum = get_tick_num(tick.timestamp)
            if abs(cur_ticknum - now_ticknum)> self.realtime_tick_diff:
                self.logger.warning('the tick timestamp has more than 10sec diff from the system time, inst=%s, ticknum= %s, now_ticknum=%s' % (tick.instID, cur_ticknum, now_ticknum))
        if not self.update_instrument(tick):
            return
        self.update_min_bar(tick)
        inst = tick.instID
        if inst in self.inst2spread:
            for key in self.inst2spread[inst]:
                self.trade_manager.check_pending_trades(key)
        self.trade_manager.check_pending_trades(inst)
        if inst in self.inst2spread:
            for key in self.inst2spread[inst]:
                self.trade_manager.process_trades(key)
        self.trade_manager.process_trades(inst)
        gway = self.inst2gateway[inst]
        if gway.process_flag:
            gway.send_queued_orders()

    def run_min(self, inst, bar_id):
        for strat_name in self.inst2strat[inst]:
            for m in self.inst2strat[inst][strat_name]:
                if bar_id % m == 0:
                    self.strategies[strat_name].run_min(inst, m)

    def trade_update(self, event):
        trade_ref = event.dict['trade_ref']
        mytrade = self.trade_manager.get_trade(trade_ref)
        if mytrade == None:
            self.logger.warning("get trade update for trade_id = %s, but it is not in the trade list" % trade_ref)
            return
        status = mytrade.refresh()
        if status in trade.Alive_Trade_Status:
            mytrade.execute()
        self.save_state()
            
    def exit(self):
        """退出"""
        # 停止事件驱动引擎
        self.eventEngine.stop()
        self.logger.info('stopped the engine, exiting the agent ...')
        self.save_state()
        for strat_name in self.strat_list:
            strat = self.strategies[strat_name]
            strat.save_state()
        for name in self.gateways:
            gateway = self.gateways[name]
            gateway.close()
            gateway.mdApi = None
            gateway.tdApi = None

if __name__=="__main__":
    pass
