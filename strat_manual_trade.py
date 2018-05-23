#-*- coding:utf-8 -*-
from base import *
from misc import *
import logging
from strategy import *

class ManualTrade(Strategy):
    common_params =  dict({'daily_close_buffer': 3, 'price_limit_buffer': 5}, \
                          **Strategy.common_params)
    asset_params = Strategy.asset_params.copy()
    asset_params.update({'long_price': 0.0, 'long_stop': 0.0, 'short_price': 0.0, 'short_stop': 0.0, \
                         'tick_num': 1, 'order_offset': True, 'run_flag': 0, \
                         'max_pos': 1, 'max_vol': 10, 'time_period': 600, 'price_type': OPT_LIMIT_ORDER, \
                         'exec_args': {'max_vol': 10, 'time_period': 600, 'price_type': OPT_LIMIT_ORDER, \
                                  'tick_num': 1, 'order_type': '', 'order_offset': True, 'inst_order': None},})
    def __init__(self, config, agent = None):
        Strategy.__init__(self, config, agent)
        numAssets = len(self.underliers)
        self.tick_base = [0.0] * numAssets

    def set_exec_args(self, idx):
        for key in ['max_vol', 'time_period', 'price_type', 'tick_num', 'order_offset']:
            self.exec_args[idx][key] = getattr(self, key)[idx]

    def on_tick(self, idx, ctick):
        num_pos = len(self.positions[idx])
        if ((self.curr_pos[idx] <= 0) and (self.curr_prices[idx] >= self.long_price[idx])) or \
                ((self.curr_pos[idx] >= 0) and (self.curr_prices[idx] <= self.short_price[idx])):
            for tp in self.positions[idx]:
                self.close_tradepos(idx, tp, self.curr_prices[idx])
            num_pos = 0
        if ((num_pos <= self.max_pos[idx]) and (self.curr_prices[idx] >= self.long_price[idx])):
            self.open_tradepos(idx, 1, self.curr_prices[idx], int(self.trade_unit[idx]))
        elif ((num_pos <= self.max_pos[idx]) and (self.curr_prices[idx] >= self.long_price[idx])):
            self.open_tradepos(idx, -1, self.curr_prices[idx], int(self.trade_unit[idx]))






