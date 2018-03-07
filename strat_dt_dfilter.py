#-*- coding:utf-8 -*-
from base import *
from misc import *
import logging
import data_handler as dh
import numpy as np
import copy
from strategy import *
 
class DTSplitChanAddon(Strategy):
    common_params =  dict({'open_period': [300, 2115], \
                           'daily_close_buffer': 3, 'price_limit_buffer': 5}, \
                          **Strategy.common_params)
    asset_params = dict({'lookbacks': 1, 'ratios': 1.0, 'freq': 1, 'channels': 20, 'ma_chan': 0, 'trend_factor': 0.0, \
                         'vol_ratio': [1.0, 1.0], 'price_mode': 'HL', 'min_rng': 0.004}, **Strategy.asset_params)
    def __init__(self, config, agent = None):
        Strategy.__init__(self, config, agent)
        numAssets = len(self.underliers)
        self.cur_rng = [0.0] * numAssets
        self.chan_high = [-1000000.0] * numAssets
        self.chan_low  = [1000000.0] * numAssets
        self.tday_open = [0.0] * numAssets
        self.ma_level = [0.0] * numAssets
        self.tick_base = [0.0] * numAssets
        self.open_idx = [0] * numAssets
        self.max_pos = [1] * numAssets
        self.split_data = [None] * numAssets
        self.high_func = None
        self.low_func = None
        self.high_func = fcustom(eval(self.data_func[0][1]), **self.data_func[0][3])
        self.high_field = self.data_func[0][2]
        self.low_sfunc = fcustom(eval(self.data_func[1][1]), **self.data_func[1][3])
        self.low_field = self.data_func[1][2]

    def register_bar_freq(self):
        for idx, under in enumerate(self.underliers):
            inst = under[0]
            self.agent.inst2strat[inst][self.name].append(1)
            if self.freq[idx] > 1:
                self.agent.inst2strat[inst][self.name].append(self.freq[idx])            

    def initialize(self):
        self.load_state()
        for idx, underlier in enumerate(self.underliers):
            inst = underlier[0]
            self.max_pos[idx] = sum(v > 0.0 for v in self.vol_ratio[idx])
            self.tick_base[idx] = self.agent.instruments[inst].tick_base
            min_id = self.agent.instruments[inst].last_tick_id/1000
            min_id = int(min_id/100)*60 + min_id % 100 - self.daily_close_buffer
            self.last_min_id[idx] = int(min_id/60)*100 + min_id % 60
            ddf = self.agent.day_data[inst].data
            mdf = self.agent.min_data[inst][1].data
            min_date = mdf['date'][-1]
            last_date = ddf['date'][-1]
            if last_date < min_date:
                last_min = mdf['min_id'][-1]
                pid = 0
                for i in range(1, len(self.open_period)):
                    if self.open_period[i] > last_min:
                        pid = i - 1
                        break
                self.open_idx[idx] = pid
                midx = len(mdf)-1
                for i in range(len(mdf)-2, -1, -1):
                    if (mdf['date'][i] < min_date) or (mdf['min_id'][i] < self.open_period[pid]):
                        midx = i + 1
                        break
                self.tday_open[idx] = mdf['open'][midx]
                df = mdf[:midx]
            else:
                self.tday_open[idx] = mdf['close'][-1]
                self.open_idx[idx] = 0
                df = mdf
            self.split_data[idx] = dh.array_split_by_bar(df, split_list = self.open_period, field = 'min_id')
            self.recalc_rng(idx)
        self.update_trade_unit()
        self.save_state()

    def update_data(self, idx):
        pass

    def recalc_rng(self, idx):
        win = int(self.lookbacks[idx])
        ddf = self.split_data[idx].data
        if self.channels[idx] > 0:
            self.chan_high[idx] = self.high_func(ddf[self.high_field][-self.channels[idx]:])
            self.chan_low[idx] = self.low_func(ddf[self.low_field][-self.channels[idx]:])
        if self.ma_chan[idx] > 0:
            self.ma_level[idx] = np.mean(ddf['close'][-self.ma_chan[idx]:])
        if win > 0:
            self.cur_rng[idx] = max(max(ddf['high'][-win:])- min(ddf['close'][-win:]), \
                                    max(ddf['close'][-win:]) - min(ddf['low'][-win:]))
        elif win == 0:
            self.cur_rng[idx] = max(max(ddf['high'][-2:])- min(ddf['close'][-2:]), \
                                    max(ddf['close'][-2:]) - min(ddf['low'][-2:]))
            self.cur_rng[idx] = max(self.cur_rng[idx] * 0.5, ddf['high'][-1]-ddf['close'][-1], \
                                    ddf['close'][-1]-ddf['low'][-1])
        else:
            self.cur_rng[idx] = max(ddf['high'][-1] - ddf['low'][-1], abs(ddf['close'][-1] - ddf['close'][-2]))

    def save_local_variables(self, file_writer):
        pass
    
    def load_local_variables(self, row):
        pass

    def on_bar(self, idx, freq):
        inst = self.underliers[idx][0]
        min_id = self.agent.cur_min[inst]['min_id']
        curr_min = self.agent.cur_min[inst]['tick_min']
        for i in range(self.open_idx[idx], len(self.open_period)-1):
            if (self.open_period[i+1] > curr_min):
                self.open_idx[idx] = i
                break
        pid = self.open_idx[idx]
        if (self.open_period[pid] > min_id) and (self.open_period[pid] <= curr_min):
            self.tday_open[idx] = self.agent.instruments[inst].price
            self.open_idx[idx] = pid
            self.recalc_rng(idx)
        if min_id < 300:
            return False
        if (self.freq[idx]>0) and (freq == self.freq[idx]):
            inst = self.underliers[idx][0]
            min_data = self.agent.min_data[inst][freq].data
            if self.price_mode[idx] == 'HL':
                buy_p = min_data['high'][-1]
                sell_p = min_data['low'][-1]
            elif self.price_mode[idx] == 'C':
                buy_p = min_data['close'][-1]
                sell_p = buy_p
            elif self.price_mode[idx] == 'TP':
                buy_p = (min_data['high'][-1] + min_data['low'][-1] + min_data['close'][-1])/3.0
                sell_p = buy_p
            else:
                self.on_log('Unsupported price type for strat=%s inst=%s' % (self.name, inst), level = logging.WARNING)
            save_status = self.check_trigger(idx, buy_p, sell_p)
            return save_status

    def on_tick(self, idx, ctick):
        if self.freq[idx] == 0:
            self.check_trigger(idx, self.curr_prices[idx], self.curr_prices[idx])

    def check_trigger(self, idx, buy_price, sell_price):
        save_status = False
        if len(self.submitted_trades[idx]) > 0:
            return save_status
        inst = self.underliers[idx][0]
        if (self.tday_open[idx] <= 0.0) or (self.cur_rng[idx] <= 0) or (self.curr_prices[idx] <= 0.001):
            self.on_log("warning: open price =0.0 or range = 0.0 or curr_price=0 for inst=%s for stat = %s" % (inst, self.name), level = logging.WARNING)
            return save_status
        min_id = int(self.agent.instruments[inst].last_update/1000.0)
        num_pos = len(self.positions[idx])
        buysell = 0
        if num_pos > self.max_pos[idx]:
            self.on_log('something wrong - number of tradepos is more than max_pos=%s' % self.max_pos[idx], level = logging.WARNING)
            return save_status
        elif num_pos >= 1:
            buysell = self.positions[idx][0].direction
        tick_base = self.tick_base[idx]
        t_open = self.tday_open[idx]
        rng = max(self.cur_rng[idx] * self.ratios[idx], t_open * self.min_rng[idx])
        up_fact = 1.0
        dn_fact = 1.0
        if (self.ma_chan[idx] > 0):
            if (t_open < self.ma_level[idx]):
                up_fact += self.trend_factor[idx]
            else:
                dn_fact += self.trend_factor[idx]            
        buy_trig  = min( t_open + up_fact * rng, self.agent.instruments[inst].up_limit - self.price_limit_buffer * tick_base)
        sell_trig = max( t_open - dn_fact * rng, self.agent.instruments[inst].down_limit + self.price_limit_buffer * tick_base)
        if (min_id >= self.last_min_id[idx]):
            if (buysell!=0) and (self.close_tday[idx]):
                msg = 'DT to close position before EOD for inst = %s, direction=%s, num_pos=%s, current min_id = %s' \
                        % (inst, buysell, num_pos, min_id)
                for tp in self.positions[idx]:
                    self.close_tradepos(idx, tp, self.curr_prices[idx] - buysell * tick_base)
                self.status_notifier(msg)
                save_status = True
            return save_status
        if ((buy_price >= buy_trig) and (buysell <0)) or ((sell_price <= sell_trig) and (buysell > 0)):            
            msg = 'DT to close position for inst = %s, open= %s, buy_trig=%s, sell_trig=%s, buy_price= %s, sell_price= %s, direction=%s, num_pos=%s' \
                                    % (inst, t_open, buy_trig, sell_trig, buy_price, sell_price, buysell, num_pos)
            for tp in self.positions[idx]:
                self.close_tradepos(idx, tp, self.curr_prices[idx] - buysell * tick_base)
            self.status_notifier(msg)
            save_status = True
            num_pos = 0
        if (self.trade_unit[idx] <= 0):
            return save_status
        if  (buy_price >= buy_trig):
            buysell = 1
        elif (sell_price <= sell_trig):
            buysell = -1
        else:
            buysell = 0
        if (buysell!=0) and (self.vol_ratio[idx][0]>0) and (num_pos == 0):
            new_vol = int(self.trade_unit[idx] * self.vol_ratio[idx][0])
            msg = 'DT to open position for inst = %s, open= %s, buy_trig=%s, sell_trig=%s, buy_price= %s, sell_price= %s, direction=%s, volume=%s' \
                                        % (inst, t_open, buy_trig, sell_trig, buy_price, sell_price, buysell, new_vol)
            self.open_tradepos(idx, buysell, self.curr_prices[idx] + buysell * tick_base, new_vol)
            self.status_notifier(msg)
            save_status = True
            num_pos = 1
        if (num_pos < self.max_pos[idx]) and (self.vol_ratio[idx][1]>0) and (((buysell > 0) and (buy_price >= self.chan_high[idx])) or ((buysell < 0) and (sell_price <= self.chan_low[idx]))):
            addon_vol = int(self.vol_ratio[idx][1]*self.trade_unit[idx])
            msg = 'DT to add position for inst = %s, high=%s, low=%s, buy= %s, sell= %s, direction=%s, volume=%s' \
                                    % (inst, self.chan_high[idx], self.chan_low[idx], buy_price, sell_price, buysell, addon_vol)
            self.open_tradepos(idx, buysell, self.curr_prices[idx] + buysell * tick_base, addon_vol)
            self.status_notifier(msg)
            save_status = True
        return save_status
