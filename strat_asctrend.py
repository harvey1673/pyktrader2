#-*- coding:utf-8 -*-
from base import *
from misc import *
import data_handler as dh
import copy
from strategy import *
 
class AsctrendTrader(Strategy):
    common_params =  dict( Strategy.common_params, **{'price_limit_buffer': 5, 'pos_exec_flag': STRAT_POS_MUST_EXEC, \
                                                      'data_func': [["WPR", "dh.WPR", "dh.wpr"], \
                                                                    ["RSI", "dh.RSI", "dh.rsi"], \
                                                                    ["SAR", "dh.SAR", "dh.sar"], ]})
    asset_params = dict({'freq': 30, 'wpr_win': 9, 'wpr_level': [70, 30], \
                        'sar_param': [0.005, 0.02], 'rsi_win': 14, 'rsi_level': [60, 40], 'daily_close': False, }, **Strategy.asset_params)
    def __init__(self, config, agent = None):
        Strategy.__init__(self, config, agent)
        numAssets = len(self.underliers)
        self.rsi_signal = [0] * numAssets
        self.sar_signal = [0] * numAssets
        self.wpr_signal = [0] * numAssets
        self.tick_base = [0.0] * numAssets
        self.daily_close_buffer = 3
        self.num_tick = 1

    def register_func_freq(self):
        for idx, under in enumerate(self.underliers):            
            for idy, infunc in enumerate(self.data_func):
                name  = infunc[0]
                sfunc = eval(infunc[1])
                rfunc = eval(infunc[2])
                freq_str = str(self.freq[idx]) + 'm'
                if name == 'SAR':                                   
                    fargs = {'incr': self.sar_param[idx][0], 'maxaf': self.sar_param[idx][1]}
                    fobj = BaseObject(name = name, sfunc = fcustom(sfunc, **fargs), rfunc = fcustom(rfunc, **fargs))
                else:
                    if name == 'WPR':
                        chan = self.wpr_win[idx]
                        fargs = {}
                    elif name == "RSI":
                        chan = self.rsi_win[idx]
                        fargs = {}
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
        key = 'WPR_%s' % str(self.wpr_win[idx])
        if (xdf[key][-1] >= self.wpr_level[idx][0]) and (xdf[key][-2] < self.wpr_level[idx][0]):
            self.wpr_signal[idx] = 1
        elif (xdf[key][-1] <= self.wpr_level[idx][1]) and (xdf[key][-2] > self.wpr_level[idx][1]):
            self.wpr_signal[idx] = 1
        else:
            self.wpr_signal[idx] = 0
        key = 'SAR'
        if (xdf[key][-1] > 0):
            self.sar_signal[idx] = 1
        elif (xdf[key][-1] < 0):
            self.sar_signal[idx] = -1
        else:
            self.sar_signal[idx] = 0
        key = 'RSI_%s' % str(self.rsi_win[idx])
        if (xdf[key][-1] >= self.rsi_level[idx][0]):
            self.sar_signal[idx] = 1
        elif (xdf[key][-1] <= self.rsi_level[idx][1]):
            self.sar_signal[idx] = -1
        else:
            self.sar_signal[idx] = 0            

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
        if (min_id >= self.last_min_id[idx]):
            if (buysell!=0) and (self.close_tday[idx]):
                msg = 'Asctrend to close position before EOD for inst = %s, direction=%s, volume=%s, current tick_id = %s' \
                        % (inst, buysell, self.trade_unit[idx], min_id)
                self.close_tradepos(idx, self.positions[idx][0], self.curr_prices[idx] - buysell * self.num_tick * tick_base)
                self.status_notifier(msg)
                save_status = True
            return save_status
        if ((buysell > 0) and ((self.rsi_signal[idx]<0) or (self.wpr_signal[idx]<0))) or ((buysell < 0) and ((self.rsi_signal[idx]>0) or (self.wpr_signal[idx]>0))):
            msg = 'Asctrend to close position for inst = %s, direction=%s, volume=%s, current price = %s' \
                    % (inst, buysell, self.trade_unit[idx], self.curr_prices[idx])
            self.close_tradepos(idx, self.positions[idx][0], self.curr_prices[idx] - buysell * self.num_tick * tick_base)
            self.status_notifier(msg)
            save_status = True
            buysell = 0
        if (self.trade_unit[idx] > 0) and (buysell == 0):
            if (self.rsi_signal[idx]>0) and (self.wpr_signal[idx]>0) and (self.sar_signal[idx]>0):
                buysell = 1
            elif (self.rsi_signal[idx]<0) and (self.wpr_signal[idx]<0) and (self.sar_signal[idx]<0):
                buysell = -1
            if buysell != 0:
                msg = 'Asctrend to open position for inst = %s, curr_price= %s, direction=%s, volume=%s' \
                                        % (inst, self.curr_prices[idx], buysell, self.trade_unit[idx])
                self.open_tradepos(idx, buysell, self.curr_prices[idx] + buysell * self.num_tick * tick_base)
                self.status_notifier(msg)
                save_status = True
        return save_status
