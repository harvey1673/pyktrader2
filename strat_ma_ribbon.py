#-*- coding:utf-8 -*-
from base import *
from misc import *
import data_handler as dh
import copy
from strategy import *
 
class MARibbonTrader(Strategy):
    common_params =  dict( Strategy.common_params, **{'channel_keys': ['DONCH_HH', 'DONCH_LL'], 'ma_key': 'EMA_C', \
                                                      'price_limit_buffer': 5, \
                                                      'data_func': [["MA_RIBBON", "dh.MA_RIBBON", "dh.ma_ribbon"], \
                                                                    ["DONCH_HH", "dh.DONCH_H", "dh.donch_h", {'field':'high'}], \
                                                                    ["DONCH_LL", "dh.DONCH_L", "dh.donch_l", {'field':'low'}]], \
                                                      'ma_series': [10, 20, 30, 40, 50, 60, 80, 100, 120, 150]})
    asset_params = dict({'freq': 30, 'channels': 20, 'pval_th': [5, 25], 'corr_th': [10, 0], 'daily_close': False, }, **Strategy.asset_params)
    def __init__(self, config, agent = None):
        Strategy.__init__(self, config, agent)
        numAssets = len(self.underliers)        
        self.tick_base = [0.0] * numAssets
        self.ribbon_pval = [0.0] * numAssets
        self.ribbon_dist = [0.0] * numAssets
        self.ribbon_corr = [0.0] * numAssets
        self.daily_close_buffer = 3

    def register_func_freq(self):
        for idx, under in enumerate(self.underliers):            
            for idy, infunc in enumerate(self.data_func):
                name  = infunc[0]
                sfunc = eval(infunc[1])
                rfunc = eval(infunc[2])
                if len(infunc) > 3:
                    fargs = infunc[3]
                else:
                    fargs = {}
                freq_str = str(self.freq[idx]) + 'm'
                if name == "MA_RIBBON":
                    fobj = BaseObject(name = name, sfunc = fcustom(sfunc, self.ma_series), rfunc = fcustom(rfunc, self.ma_series))
                    self.agent.register_data_func(under[0], freq_str, fobj)
                else:
                    chan = self.channels[idx]
                    if chan > 0:
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
            self.update_mkt_state(idx)
        self.update_trade_unit()

    def update_mkt_state(self, idx):
        instID = self.underliers[idx][0]
        xdf = self.agent.min_data[instID][self.freq[idx]].data
        self.ribbon_corr[idx] = xdf['MARIBBON_CORR'][-1]
        self.ribbon_pval[idx] = xdf['MARIBBON_PVAL'][-1]
        self.ribbon_dist[idx] = xdf['MARIBBON_DIST'][-1]
        if self.channels[idx] > 0:
            key = self.channel_keys[0] + str(self.channels[idx])
            self.chan_high[idx] = xdf[key][-2]
            key = self.channel_keys[1] + str(self.channels[idx])
            self.chan_low[idx] = xdf[key][-2]

    def on_bar(self, idx, freq):
        inst = self.underliers[idx][0]
        self.update_mkt_state(idx)
        self.check_trigger(idx)

    def on_tick(self, idx, ctick):
        pass

    def check_trigger(self, idx):
        if len(self.submitted_trades[idx]) > 0:
            return
        inst = self.underliers[idx][0]
        min_id = self.agent.cur_min[inst]['tick_min']
        num_pos = len(self.positions[idx])
        buysell = 0
        if num_pos > 0:
            buysell = self.positions[idx][0].direction
        tick_base = self.tick_base[idx]
        save_status = False
        curr_p = self.curr_prices[idx]
        high_chan = (self.channels[idx] <= 0) or (curr_p >= self.chan_high[idx])
        low_chan = (self.channels[idx] <= 0) or (curr_p <= self.chan_low[idx])
        if (min_id >= self.last_min_id[idx]):
            if (buysell!=0) and (self.close_tday[idx]):
                msg = 'MA ribbon to close position before EOD for inst = %s, direction=%s, volume=%s, current tick_id = %s' \
                        % (inst, buysell, self.trade_unit[idx], min_id)
                self.close_tradepos(idx, self.positions[idx][0], self.curr_prices[idx] - buysell * tick_base)
                self.status_notifier(msg)
                save_status = True
            return save_status
        if (self.ribbon_pval >= self.pval_th[idx][1]) and (((self.ribbon_corr[idx] > -self.corr_th[idx][1]) and (buysell<0)) or ((self.ribbon_corr[idx] < self.corr_th[idx][1]) and (buysell>0))):
            msg = 'MA Ribbon to close position after spiking pval for inst = %s, direction=%s, volume=%s, pval=%s, corr=%s, dist=%s' \
                    % (inst, buysell, self.trade_unit[idx], self.ribbon_pval[idx], self.ribbon_corr[idx], self.ribbon_dist[idx],)
            self.close_tradepos(idx, self.positions[idx][0], self.curr_prices[idx] - buysell * tick_base)
            self.status_notifier(msg)
            save_status = True
            buysell = 0
        if (self.trade_unit[idx] > 0) and (buysell == 0) and (self.ribbon_pval[idx] < self.pval_th[idx][0]):
            if (self.ribbon_corr[idx] >= self.corr_th[idx][0]) and high_chan:
                buysell = 1
            elif (self.ribbon_corr[idx] <= -self.corr_th[idx][0]) and low_chan:
                buysell = -1
            if buysell != 0:
                msg = 'MA ribbon to open position for inst = %s, corr=%s, pval=%s, curr_price= %s, direction=%s, volume=%s' \
                     % (len(self.ma_prices[idx]), inst, self.ribbon_corr[idx], self.ribbon_pval[idx], self.curr_prices[idx], buysell, self.trade_unit[idx])
                self.open_tradepos(idx, buysell, self.curr_prices[idx] + buysell * tick_base)
                self.status_notifier(msg)
                save_status = True
        return save_status
