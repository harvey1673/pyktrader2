#-*- coding:utf-8 -*-
from base import *
from misc import *
import data_handler as dh
import copy
from strategy import *
 
class BbandPChanTrader(Strategy):
    common_params =  dict({'channel_keys': ['DONCH_H', 'DONCH_L'], 'band_keys': ['MA_C', 'STDEV_C'], 'price_limit_buffer': 5}, **Strategy.common_params)
    asset_params = dict({'band_win': 40, 'ratios': 1.0, 'freq': 30, 'channels': 20, 'daily_close': False, }, **Strategy.asset_params)
    def __init__(self, config, agent = None):
        Strategy.__init__(self, config, agent)
        numAssets = len(self.underliers)
        self.upper_band = [0.0] * numAssets
        self.mid_band   = [0.0] * numAssets
        self.lower_band = [0.0] * numAssets
        self.chan_high = [0.0] * numAssets
        self.chan_low  = [0.0] * numAssets
        self.tick_base = [0.0] * numAssets
        self.data_func = [()]
        self.daily_close_buffer = 3
        self.num_tick = 1

    def register_func_freq(self):
        for idx, under in enumerate(self.underliers):
            for infunc in self.data_func:
                name  = infunc[0]
                sfunc = eval(infunc[1])
                rfunc = eval(infunc[2])
                if len(infunc) > 3:
                    fargs = infunc[3]
                else:
                    fargs = {}
                freq_str = str(self.freq[idx]) + 'm'
                fobj = BaseObject(name = name + str(chan), sfunc = fcustom(sfunc, n = chan, **fargs), rfunc = fcustom(rfunc, n = chan, **fargs))                
                self.agent.register_data_func(under[0], freq_str, fobj)

    def register_bar_freq(self):
        for idx, under in enumerate(self.underliers):
            inst = under[0]
            if self.freq[idx] > 0:
                self.agent.inst2strat[inst][self.name].append(self.freq[idx])

    def initialize(self):
        self.load_state()
        for idx, underlier in enumerate(self.underliers):
            inst = underlier[0]
            self.tick_base[idx] = self.agent.instruments[inst].tick_base
            min_id = self.agent.instruments[inst].last_tick_id/1000
            min_id = int(min_id/100)*60 + min_id % 100 - self.daily_close_buffer
            self.last_min_id[idx] = int(min_id/60)*100 + min_id % 60
            self.update_mkt_data(idx)
        self.update_trade_unit()

    def update_mkt_data(self, idx):
        instID = self.underliers[idx][0]
        xdf = self.agent.min_data[inst][self.freq[idx]]
        key = self.channel_keys[0] + str(self.channels[idx])
        self.chan_high[idx] = xdf.ix[-1, key]
        key = self.channel_keys[1] + str(self.channels[idx])
        self.chan_low[idx]  = xdf.ix[-1, key]
        key = self.band_keys[0] + str(self.band_win[idx])
        self.mid_band[idx] = xdf.ix[-1, key]
        key = self.band_keys[1] + str(self.band_win[idx])
        stdev = xdf.ix[-1, key]
        self.upper_band[idx] = self.mid_band[idx] + self.ratios[idx] * stdev
        self.lower_band[idx] = self.mid_band[idx] - self.ratios[idx] * stdev

    #def save_local_variables(self, file_writer):
    #    pass
    
    #def load_local_variables(self, row):
    #    pass

    def on_bar(self, idx, freq):
        inst = self.underliers[idx][0]
        self.update_mkt_data(idx)
        mslice = self.agent.min_data[inst][self.freq[idx]].iloc[-1]
        if len(self.positions[idx]) > 0:
            self.positions[idx][0].set_exit(self.mid_band[idx])
        self.check_trigger(idx, mslice)

    def on_tick(self, idx, ctick):
        if self.freq[idx] == 0:
            curr_p = self.curr_prices[idx]
            mslice = BaseObject(open = curr_p, high = curr_p, low = curr_p, close = curr_p)
            self.check_trigger(idx, mslice)

    def check_trigger(self, idx, mslice):
        if len(self.submitted_trades[idx]) > 0:
            return
        inst = self.underliers[idx][0]
        min_id = self.agent.tick_id/1000.0
        num_pos = len(self.positions[idx])
        buysell = 0
        if num_pos > 0:
            buysell = self.positions[idx][0].direction
        tick_base = self.tick_base[idx]
        if (min_id >= self.last_min_id[idx]):
            if (buysell!=0) and (self.close_tday[idx]):
                msg = 'BbandPchanTrader to close position before EOD for inst = %s, direction=%s, volume=%s, current tick_id = %s' \
                        % (inst, buysell, self.trade_unit[idx], min_id)
                self.close_tradepos(idx, self.positions[idx][0], self.curr_prices[idx] - buysell * self.num_tick * tick_base)
                self.status_notifier(msg)
                self.save_state()
            return
        if ((mslice.close >= buy_trig) and (buysell <=0)) or ((sell_price <= sell_trig) and (buysell >=0)):
            save_status = False
            if buysell!=0:
                msg = 'DT to close position for inst = %s, open= %s, buy_trig=%s, sell_trig=%s, curr_price= %s, direction=%s, volume=%s' \
                                    % (inst, t_open, buy_trig, sell_trig, self.curr_prices[idx], buysell, self.trade_unit[idx])
                self.close_tradepos(idx, self.positions[idx][0], self.curr_prices[idx] - buysell * self.num_tick * tick_base)
                self.status_notifier(msg)
                save_status = True
            if self.trade_unit[idx] <= 0:
                if save_status:
                    self.save_state()
                return
            if  (buy_price >= buy_trig):
                buysell = 1
            else:
                buysell = -1
            if buy_price >= max(buy_trig, self.chan_high[idx]) or sell_price <= min(sell_trig, self.chan_low[idx]):
                msg = 'DT to open position for inst = %s, open= %s, buy_trig=%s, sell_trig=%s, curr_price= %s, direction=%s, volume=%s' \
                                        % (inst, t_open, buy_trig, sell_trig, self.curr_prices[idx], buysell, self.trade_unit[idx])
                self.open_tradepos(idx, buysell, self.curr_prices[idx] + buysell * self.num_tick * tick_base)
                self.status_notifier(msg)
                save_status = True
            if save_status:
                self.save_state()
