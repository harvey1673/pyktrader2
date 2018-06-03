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

    def set_exec_args(self, idx, direction):
        for key in ['max_vol', 'time_period', 'price_type', 'tick_num', 'order_offset']:
            self.exec_args[idx][key] = getattr(self, key)[idx]

    def open_long(self, idx):
        if len(self.positions[idx]) < self.max_pos[idx]:
            self.open_tradepos(idx, 1, self.long_price[idx], int(self.trade_unit[idx]))
            return True
        else:
            return False

    def open_short(self, idx):
        if len(self.positions[idx]) < self.max_pos[idx]:
            self.open_tradepos(idx, -1, self.short_price[idx], int(self.trade_unit[idx]))
            return True
        else:
            return False

    def on_tick(self, idx, ctick):
        num_pos = len(self.positions[idx])
        curr_pos = self.curr_pos[idx]
        save_status = False
        if ((self.curr_pos[idx] <= 0) and (self.curr_prices[idx] >= self.long_price[idx])) or \
                ((self.curr_pos[idx] >= 0) and (self.curr_prices[idx] <= self.short_price[idx])):
            save_status = self.liquidate_tradepos(idx) or save_status
            num_pos = 0
            curr_pos = 0
        if (self.curr_prices[idx] >= self.long_price[idx]):
            save_status = self.open_long(idx) or save_status
        elif (self.curr_prices[idx] <= self.short_price[idx]):
            save_status = self.open_short(idx) or save_status
        return save_status






