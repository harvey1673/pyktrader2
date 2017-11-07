#-*- coding:utf-8 -*-
from base import *
from misc import *
import data_handler as dh
import copy
from strategy import *
 
class RsiAtrStrat(Strategy):
    common_params =  dict( {'price_limit_buffer': 5, 'daily_close_buffer': 2, \
                            'pos_class': 'TargetTrailTradePos', 'pos_args': {},
                            'data_func': [["RSI", "dh.RSI_F", "dh.rsi_f", {'field':'close'}], \
                                        ["ATR", "dh.ATR", "dh.atr"], \
                                        ["ATRMA", "dh.MA", "dh.ma"]]}, \
                           **Strategy.common_params)
    asset_params = dict({'rsi_win': 14, 'rsi_th': 20.0, 'atrma_win': 10, 'atr_win': 20, \
                         'freq': 1, 'stoploss': 4, }, **Strategy.asset_params)
    def __init__(self, config, agent = None):
        Strategy.__init__(self, config, agent)
        numAssets = len(self.underliers)
        self.rsi = [0.0] * numAssets
        self.atr   = [0.0] * numAssets
        self.atrma = [0.0] * numAssets
        self.tick_base = [0.0] * numAssets

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
                if name  == 'ATR':
                    chan = self.atr_win[idx]
                elif name == 'ATRMA':
                    name = 'MA_ATR' + str(self.atr_win[idx]) + '_'
                    chan = self.atrma_win[idx]
                    fargs = {'field': 'ATR'+str(self.atr_win[idx])}
                elif name == "RSI":
                    chan = self.rsi_win[idx]
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
            min_id = int(min_id/100)*60 + min_id % 100 - self.freq[idx]
            self.last_min_id[idx] = int(min_id/60)*100 + min_id % 60
            self.update_mkt_state(idx)
        self.update_trade_unit()
        self.save_state()

    def update_mkt_state(self, idx):
        instID = self.underliers[idx][0]
        xdf = self.agent.min_data[instID][self.freq[idx]].data
        rsi_key = "RSI" + str(self.rsi_win[idx])
        self.rsi[idx] = xdf[rsi_key][-1]
        atr_key = "ATR" + str(self.atr_win[idx])
        self.atr[idx]  = xdf[atr_key][-1]
        atrma_key = "MA_ATR" + str(self.atr_win[idx]) + '_' + str(self.atrma_win[idx])
        self.atrma[idx] = xdf[atrma_key][-1]

    def on_bar(self, idx, freq):
        self.update_mkt_state(idx)
        save_status = False
        if (self.freq[idx]>0) and (freq == self.freq[idx]):
            save_status = self.check_trigger(idx)
        return save_status

    def on_tick(self, idx, ctick):
        if len(self.submitted_trades[idx]) == 0:
            curr_p = self.curr_prices[idx]
            min_id = self.agent.tick_id / 1000.0
            for tradepos in self.positions[idx]:
                if (self.close_tday[idx] and (min_id >= self.last_min_id[idx])) \
                                    or tradepos.check_exit(curr_p, self.atrma[idx] * self.stoploss[idx]):
                    msg = 'RSI-ATR to close position for inst = %s, direction=%s, current price = %s, exit target = %s' \
                                    % (tradepos.insts[0], tradepos.direction, curr_p, tradepos.exit_target)
                    self.close_tradepos(idx, tradepos, curr_p - tradepos.direction * self.tick_base[idx])
                    self.status_notifier(msg)
                    return True
                else:
                    tradepos.update_price(curr_p)
                    return False
        else:
            return False

    def check_trigger(self, idx):
        if len(self.submitted_trades[idx]) > 0:
            return False
        inst = self.underliers[idx][0]
        curr_p = self.curr_prices[idx]
        min_id = self.agent.tick_id/1000.0
        tick_base = self.tick_base[idx]
        save_status = False
        rsi_dir = (self.rsi[idx] > 50 + self.rsi_th[idx]) * 1 - (self.rsi[idx] < 50 - self.rsi_th[idx]) * 1
        open_signal = rsi_dir * (self.atr[idx] > self.atrma[idx])
        if len(self.positions[idx])>0:
            buysell = self.positions[idx][0].direction
        else:
            buysell = 0
        if rsi_dir * buysell < 0:
            tradepos = self.positions[idx][0]
            msg = 'RSI-ATR to close position for inst = %s, direction=%s, current price = %s, exit target = %s' \
                    % (tradepos.insts[0], tradepos.direction, curr_p, tradepos.exit_target)
            self.close_tradepos(idx, tradepos, curr_p - tradepos.direction * self.tick_base[idx])
            self.status_notifier(msg)
            save_status = True
        if (min_id < self.last_min_id[idx]) and (self.trade_unit[idx] > 0) \
                and (open_signal != 0) and (buysell * open_signal <= 0):
            msg = 'RSI-ATR to open position for inst = %s, ATRMA=%s, ATR=%s, RSI=%s, curr_price= %s, direction=%s, volume=%s' \
                                % (inst, self.atrma[idx], self.atr[idx], self.rsi[idx], curr_p, open_signal, self.trade_unit[idx])
            self.open_tradepos(idx, open_signal, curr_p + open_signal * tick_base)
            self.status_notifier(msg)
            save_status = True
        return save_status
