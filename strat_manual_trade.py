#-*- coding:utf-8 -*-
from base import *
from misc import *
import logging
from strategy import *

class ManualTrade(Strategy):
    common_params =  dict({'daily_close_buffer': 3, 'price_limit_buffer': 5}, \
                          **Strategy.common_params)
    asset_params = Strategy.asset_params.copy()
    asset_params.update({'limit_price': 0.0, 'stop_price': 0.0, \
                         'tick_num': 1, 'order_offset': True, \
                         'max_vol': 10, 'time_period': 600, 'price_type': OPT_LIMIT_ORDER, \
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
        pass

