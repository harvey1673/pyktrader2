#-*- coding:utf-8 -*-
from misc import *
from strategy import *
 
class DTTrader(Strategy):
    common_params =  dict({'price_limit_buffer': 5,}, **Strategy.common_params)
    asset_params = dict({'lookbacks': 1, 'ratios': 1.0, 'freq': 1, 'min_rng': 0.004, 'cur_ma': 0.0, 'ma_win': 20, 'daily_close': False, 'factors': 0.0, }, **Strategy.asset_params)
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
            ddf = self.agent.day_data[inst]
            win = self.lookbacks[idx]
            if win > 0:
                self.cur_rng[idx] = max(max(ddf.ix[-win:,'high'])- min(ddf.ix[-win:,'close']), max(ddf.ix[-win:,'close']) - min(ddf.ix[-win:,'low']))
            elif win == 0:
                self.cur_rng[idx] = max(max(ddf.ix[-2:,'high'])- min(ddf.ix[-2:,'close']), max(ddf.ix[-2:,'close']) - min(ddf.ix[-2:,'low']))
                self.cur_rng[idx] = max(self.cur_rng[idx] * 0.5, ddf.ix[-1,'high']-ddf.ix[-1,'close'],ddf.ix[-1,'close']-ddf.ix[-1,'low'])
            else:
                self.cur_rng[idx] = max(ddf.ix[-1,'high']- ddf.ix[-1,'low'], abs(ddf.ix[-1,'close'] - ddf.ix[-2,'close']))
            self.cur_ma[idx] = ddf.ix[-self.ma_win[idx]:, 'close'].mean()
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
        for idx, underlier in enumerate(self.underliers):
            inst = underlier[0]
            row = ['CurrRange', str(inst), self.cur_rng[idx]]
            file_writer.writerow(row)
    
    def load_local_variables(self, row):
        if row[0] == 'CurrRange':
            inst = str(row[1])
            idx = self.under2idx[inst]
            if idx >= 0:
                self.cur_rng[idx] = float(row[2])

    def on_bar(self, idx, freq):
        if (self.freq[idx]>0) and (freq == self.freq[idx]):
            inst = self.underliers[idx][0]
            mslice = self.agent.min_data[inst][freq].iloc[-1]
            self.check_trigger(idx, mslice.high, mslice.low)
            
    def on_tick(self, idx, ctick):
        if self.freq[idx] == 0:
            self.check_trigger(idx, self.curr_prices[idx], self.curr_prices[idx])
    
    def check_trigger(self, idx, buy_price, sell_price): 
        if len(self.submitted_trades[idx]) > 0:
            return
        inst = self.underliers[idx][0]
        self.tday_open[idx] = self.agent.cur_day[inst]['open']
        if (self.tday_open[idx] <= 0.0) or (self.cur_rng[idx] <= 0) or (self.curr_prices[idx] <= 0.001):
            self.logger.warning("warning: open price =0.0 or range = 0.0 or curr_price=0 for inst=%s for stat = %s" % (inst, self.name))
            return
        min_id = self.agent.tick_id/1000.0
        num_pos = len(self.positions[idx])
        buysell = 0
        if num_pos > 1:
            self.logger.warning('something wrong with position management - submitted trade is empty but trade position is more than 1')
            return
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
                self.save_state()
            return

        if ((buy_price >= buy_trig) and (buysell <=0)) or ((sell_price <= sell_trig) and (buysell >=0)):
            if buysell!=0:
                msg = 'DT to close position for inst = %s, open= %s, buy_trig=%s, sell_trig=%s, curr_price= %s, direction=%s, volume=%s' \
                                    % (inst, self.tday_open[idx], buy_trig, sell_trig, self.curr_prices[idx], buysell, self.trade_unit[idx])
                self.close_tradepos(idx, self.positions[idx][0], self.curr_prices[idx] - buysell * self.num_tick * tick_base)
                self.status_notifier(msg)
                self.save_state()
            if self.trade_unit[idx] <= 0:
                return
            if  (buy_price >= buy_trig):
                buysell = 1
            else:
                buysell = -1
            msg = 'DT to open position for inst = %s, open= %s, buy_trig=%s, sell_trig=%s, curr_price= %s, direction=%s, volume=%s' \
                                    % (inst, self.tday_open[idx], buy_trig, sell_trig, self.curr_prices[idx], buysell, self.trade_unit[idx])
            self.open_tradepos(idx, buysell, self.curr_prices[idx] + buysell * self.num_tick * tick_base)
            self.status_notifier(msg)
            self.save_state()

