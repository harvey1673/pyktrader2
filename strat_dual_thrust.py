#-*- coding:utf-8 -*-
from misc import *
from strategy import *
import logging
 
class DTTrader(Strategy):
    common_params =  dict({'price_limit_buffer': 5,}, **Strategy.common_params)
    asset_params = dict({'lookbacks': 1, 'ratios': 1.0, 'freq': 1, 'min_rng': 0.004, 'cur_ma': 0.0, 'ma_win': 20, \
                         'factors': 0.0, 'price_mode': 'HL', }, **Strategy.asset_params)
    def __init__(self, config, agent = None):
        Strategy.__init__(self, config, agent)
        numAssets = len(self.underliers)
        self.tday_open = [0.0] * numAssets
        self.cur_rng = [0.0] * numAssets
        self.open_idx = [0] * numAssets
        self.tick_base = [0.0] * numAssets
        self.last_min_id = [0] * numAssets
        self.daily_close_buffer = 3
        self.num_tick = 1

    def initialize(self):
        self.load_state()
        for idx, underlier in enumerate(self.underliers):
            inst = underlier[0]
            self.tick_base[idx] = self.agent.instruments[inst].tick_base
            ddf = self.agent.day_data[inst].data
            win = self.lookbacks[idx]
            if win > 0:
                self.cur_rng[idx] = max(max(ddf['high'][-win:])- min(ddf['close'][-win:]), max(ddf['close'][-win:]) - min(ddf['low'][-win:]))
            elif win == 0:
                self.cur_rng[idx] = max(max(ddf['high'][-2:])- min(ddf['close'][-2:]), max(ddf['close'][-2:]) - min(ddf['low'][-2:]))
                self.cur_rng[idx] = max(self.cur_rng[idx] * 0.5, ddf['high'][-1]-ddf['close'][-1],ddf['close'][-1]-ddf['low'][-1])
            else:
                self.cur_rng[idx] = max(ddf['high'][-1]- ddf['low'][-1], abs(ddf['close'][-1] - ddf['close'][-2]))
            self.cur_ma[idx] = ddf['close'][-self.ma_win[idx]:].mean()
            min_id = self.agent.instruments[inst].last_tick_id/1000
            min_id = int(min_id/100)*60 + min_id % 100 - self.daily_close_buffer
            self.last_min_id[idx] = int(min_id/60)*100 + min_id % 60
        self.update_trade_unit()
        self.save_state()

    def register_bar_freq(self):
        for idx, underlier in enumerate(self.underliers):
            if self.freq[idx] > 0:
                instID = self.underliers[idx][0]
                self.agent.inst2strat[instID][self.name].append(self.freq[idx])
            
    def save_local_variables(self, file_writer):
        pass
        #for idx, underlier in enumerate(self.underliers):
        #    inst = underlier[0]
        #    row = ['CurrRange', str(inst), self.cur_rng[idx]]
        #    file_writer.writerow(row)
    
    def load_local_variables(self, row):
        pass
        #if row[0] == 'CurrRange':
        #    inst = str(row[1])
        #    idx = self.under2idx[inst]
        #    if idx >= 0:
        #        self.cur_rng[idx] = float(row[2])

    def on_bar(self, idx, freq):
        if (self.freq[idx]>0) and (freq == self.freq[idx]):
            inst = self.underliers[idx][0]
            if self.agent.cur_min[inst]['min_id'] < 300:
                return
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
        self.tday_open[idx] = self.agent.cur_day[inst]['open']
        if (self.tday_open[idx] <= 0.0) or (self.cur_rng[idx] <= 0) or (self.curr_prices[idx] <= 0.001):
            self.on_log("warning: open price =0.0 or range = 0.0 or curr_price=0 for inst=%s for stat = %s" % (inst, self.name), level = logging.WARNING)
            return save_status
        min_id = self.agent.tick_id/1000.0
        num_pos = len(self.positions[idx])
        buysell = 0
        if num_pos > 1:
            self.on_log('something wrong with position management - submitted trade is empty but trade position is more than 1', level = logging.WARNING)
            return save_status
        elif num_pos == 1:
            buysell = self.positions[idx][0].direction
        tick_base = self.tick_base[idx]
        t_open = self.tday_open[idx]
        c_rng = max(self.cur_rng[idx] * self.ratios[idx], t_open * self.min_rng[idx])
        buy_trig  = t_open + c_rng
        sell_trig = t_open - c_rng
        if self.cur_ma[idx] > t_open:
            buy_trig  += self.factors[idx] * c_rng
        elif self.cur_ma[idx] < t_open:
            sell_trig -= self.factors[idx] * c_rng
        buy_trig = min( self.agent.instruments[inst].up_limit - self.tick_base[idx] * self.price_limit_buffer, buy_trig )
        sell_trig = max( self.agent.instruments[inst].down_limit + self.tick_base[idx] * self.price_limit_buffer, sell_trig )

        if (min_id >= self.last_min_id[idx]):
            if (buysell!=0) and (self.close_tday[idx]):
                msg = 'DT to close position before EOD for inst = %s, direction=%s, volume=%s, current tick_id = %s' \
                        % (inst, buysell, self.trade_unit[idx], min_id)
                self.close_tradepos(idx, self.positions[idx][0], self.curr_prices[idx] - buysell * self.num_tick * tick_base)
                self.status_notifier(msg)
                save_status = True
            return save_status
        if ((buy_price >= buy_trig) and (buysell <=0)) or ((sell_price <= sell_trig) and (buysell >=0)):
            if buysell!=0:
                msg = 'DT to close position for inst = %s, open= %s, buy_trig=%s, sell_trig=%s, curr_price= %s, direction=%s, volume=%s' \
                                    % (inst, self.tday_open[idx], buy_trig, sell_trig, self.curr_prices[idx], buysell, self.trade_unit[idx])
                self.close_tradepos(idx, self.positions[idx][0], self.curr_prices[idx] - buysell * self.num_tick * tick_base)
                self.status_notifier(msg)
                save_status = True
            if self.trade_unit[idx] <= 0:
                return save_status
            if  (buy_price >= buy_trig):
                buysell = 1
            else:
                buysell = -1
            msg = 'DT to open position for inst = %s, open= %s, buy_trig=%s, sell_trig=%s, curr_price= %s, direction=%s, volume=%s' \
                                    % (inst, self.tday_open[idx], buy_trig, sell_trig, self.curr_prices[idx], buysell, self.trade_unit[idx])
            self.open_tradepos(idx, buysell, self.curr_prices[idx] + buysell * self.num_tick * tick_base)
            self.status_notifier(msg)
            save_status = True
        return save_status
