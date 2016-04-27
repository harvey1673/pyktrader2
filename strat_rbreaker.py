#-*- coding:utf-8 -*-
#from base import *
from misc import *
from strategy import *
 
class RBreaker(Strategy):
    common_params =  dict({'price_limit_buffer': 5}, **Strategy.common_params)
    asset_params = dict({'ratios': [0.35, 0.08, 0.25], 'freq': 1,'min_rng': 0.015, 'start_min_id': 303, 'last_min_id': 2057, 'daily_close': True, 'reverse_flag': True}, **Strategy.asset_params)
    def __init__(self, config, agent = None):
        Strategy.__init__(self, config, agent)
        num_assets = len(self.underliers)
        self.ssetup = [0.0]*num_assets
        self.bsetup = [0.0]*num_assets
        self.senter = [0.0]*num_assets
        self.benter = [0.0]*num_assets
        self.sbreak = [0.0]*num_assets
        self.bbreak = [0.0]*num_assets
        self.tick_base = [0.0]*num_assets
        self.entry_limit = 2

    def initialize(self):
        self.load_state()
        for idx, underlier in enumerate(self.underliers):
            inst = underlier[0]
            self.tick_base[idx] = self.agent.instruments[inst].tick_base
            ddf = self.agent.day_data[inst]
            a = self.ratios[idx][0]
            b = self.ratios[idx][1]
            c = self.ratios[idx][2]
            dhigh = ddf.ix[-1,'high']
            dlow = ddf.ix[-1,'low']
            dclose = ddf.ix[-1,'close']
            if dhigh - dlow <= self.min_rng[idx] * dclose:
                self.reverse_flag[idx] = False
            self.ssetup[idx] = dhigh + a*(dclose - dlow)
            self.bsetup[idx] = dlow  - a*(dhigh -  dclose)
            self.senter[idx] = (1 + b)*(dhigh + dclose)/2.0 - b*dlow
            self.benter[idx] = (1 + b)*(dlow  + dclose)/2.0 - b*dhigh
            self.bbreak[idx] = self.ssetup[idx] + c * (self.ssetup[idx] - self.bsetup[idx])
            self.sbreak[idx] = self.bsetup[idx] - c * (self.ssetup[idx] - self.bsetup[idx]) 
            min_id = self.agent.instruments[inst].last_tick_id/1000
            min_id = int(min_id/100)*60 + min_id % 100 - max(self.freq[idx], self.daily_close_buffer) - 1
            self.last_min_id[idx] = int(min_id/60)*100 + min_id % 60
            min_id = self.agent.instruments[inst].start_tick_id/1000
            min_id = int(min_id/100)*60 + min_id % 100 + max(self.freq[idx], self.daily_close_buffer) - 1
            self.start_min_id[idx] = int(min_id/60)*100 + min_id % 60   
        self.save_state()
        return         

    def register_func_freq(self):
        pass

    def register_bar_freq(self):
        for idx, under in enumerate(self.underliers):
            inst = under[0]
            self.agent.inst2strat[inst][self.name].append(self.freq[idx])

    def save_local_variables(self, file_writer):
        for idx, underlier in enumerate(self.underliers):
            inst = underlier[0]
            row = ['NumTrade', str(inst), self.num_entries[idx], self.num_exits[idx]]
            file_writer.writerow(row)
        for idx, underlier in enumerate(self.underliers):
            inst = underlier[0]
            row = ['Signals', str(inst), self.bbreak[idx], self.ssetup[idx], self.senter[idx], self.benter[idx], self.bsetup[idx], self.sbreak[idx]]
            file_writer.writerow(row)
    
    def load_local_variables(self, row):
        if row[0] == 'NumTrade':
            inst = str(row[1])
            idx = self.under2idx[inst]
            if idx >=0:
                self.num_entries[idx] = int(row[2])
                self.num_exits[idx] =int(row[3])
    
    def on_bar(self, idx, freq):
        inst = self.underliers[idx][0]
        min_id = self.agent.cur_min[inst]['min_id']
        if (min_id < self.start_min_id[idx]):
            self.logger.debug('inst=%s has not started in this strategy = %s' % (inst, self.name))
            return
        if (freq != self.freq[idx]) or (len(self.submitted_trades[idx]) > 0):
            if (min_id >= self.last_min_id[idx]):
                for etrade in self.submitted_trades[idx]:
                    self.speedup(etrade)
            return
        num_pos = len(self.positions[idx])
        curr_pos = None
        tick_base = self.tick_base[idx]
        dhigh = self.agent.cur_day[inst]['high']
        dlow  = self.agent.cur_day[inst]['low']
        mhigh = self.agent.min_data[inst][freq]['high'][-1]
        mlow  = self.agent.min_data[inst][freq]['low'][-1]
        if num_pos > 1:
            self.logger.warning('something wrong with position management - submitted trade is empty but trade position is more than 1')
            return
        elif num_pos == 1:
            curr_pos = self.positions[idx][0]
        save_status = False
        buysell = 0 if curr_pos == None else curr_pos.direction
        if ((min_id >= self.last_min_id[idx]) or self.agent.check_price_limit(inst, 5)):
            if buysell != 0:
                msg = 'R-Breaker to close position before EOD or hitting price limit for inst = %s, direction=%s, volume=%s, current min_id = %s, current price = %s' \
                        % (inst, buysell, self.trade_unit[idx], min_id, self.curr_prices[idx])
                self.close_tradepos(idx, curr_pos, self.curr_prices[idx] - buysell * self.num_tick * tick_base)
                self.num_entries[idx] = self.entry_limit
                self.save_state()
                self.status_notifier(msg)
            return
        if ((self.curr_prices[idx] >= self.bbreak[idx]) and (buysell <=0)) or ((self.curr_prices[idx] <= self.sbreak[idx]) and (buysell >= 0)):
            if curr_pos != None:
                self.close_tradepos(idx, curr_pos, self.curr_prices[idx] - buysell * self.num_tick * tick_base)
                save_status = True
                msg = 'R-Breaker to close position for inst = %s, direction=%s, volume=%s, current min_id = %s' \
                        % (inst, buysell, self.trade_unit[idx], min_id)
                self.status_notifier(msg)     
            if self.num_entries[idx] < self.entry_limit:   
                if  self.curr_prices[idx] >= self.bbreak[idx]:
                    buysell = 1
                else:
                    buysell = -1
                msg = 'R-Breaker to open position for inst = %s, bbreak=%s, sbreak=%s, curr_price= %s, direction=%s, volume=%s' \
                        % (inst, self.bbreak[idx], self.sbreak[idx], self.curr_prices[idx], buysell, self.trade_unit[idx])
                self.open_tradepos(idx, buysell, self.curr_prices[idx] + buysell * self.num_tick * tick_base)
                save_status = True
                self.status_notifier(msg)
        elif self.reverse_flag[idx]:
            if ((dhigh<self.bbreak[idx]) and (dhigh>=self.ssetup[idx]) and (self.curr_prices[idx]<=self.senter[idx]) and (mhigh>=self.senter[idx]) and (buysell>=0)) or \
             ((dlow>self.sbreak[idx]) and (dlow<=self.bsetup[idx]) and (self.curr_prices[idx]>=self.benter[idx]) and (mlow<=self.benter[idx]) and (buysell<=0)):
                if curr_pos != None:
                    self.close_tradepos(idx, curr_pos, self.curr_prices[idx] - buysell * self.num_tick * tick_base)
                    save_status = True
                    msg = 'R-Breaker to close position for inst = %s, direction=%s, volume=%s, current min_id = %s' \
                                        % (inst, buysell, self.trade_unit[idx], min_id)
                    self.status_notifier(msg)
                if self.num_entries[idx] < self.entry_limit:
                    if  (self.curr_prices[idx]<=self.senter[idx]) and (mhigh>=self.senter[idx]):
                        buysell = -1
                    else:
                        buysell = 1
                    self.open_tradepos(idx, buysell, self.curr_prices[idx] + buysell * self.num_tick * tick_base)
                    save_status = True
                    msg = 'R-Breaker to open position for inst = %s, bbreak= %s, ssetup=%s, senter=%s, sbreak= %s, bsetup=%s, benter=%s, curr_price= %s, direction=%s, volume=%s' \
                                        % (inst, self.bbreak[idx], self.ssetup[idx], self.senter[idx],
                                           self.sbreak[idx], self.bsetup[idx], self.benter[idx], self.curr_prices[idx], buysell, self.trade_unit[idx])
                    self.status_notifier(msg)
        if save_status:
            self.save_state()
