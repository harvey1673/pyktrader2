#-*- coding:utf-8 -*-
from base import *
from misc import *
import logging
from strategy import *

class ManualTrade(Strategy):
    common_params =  dict({'daily_close_buffer': 3, 'price_limit_buffer': 5}, \
                          **Strategy.common_params)
    asset_params = Strategy.asset_params.copy()
    asset_params.update({'underliers': [], 'volumes': [], 'trade_unit': 1,  'alloc_w': 0.0, 'price_unit': None, \
                    'close_tday': False, 'last_min_id': 2057, 'trail_loss': 0, \
                    'exec_args': {'max_vol': 20, 'time_period': 600, 'price_type': OPT_LIMIT_ORDER, \
                                  'tick_num': 1, 'order_type': '', 'inst_order': None},})
    def __init__(self, config, agent = None):
        Strategy.__init__(self, config, agent)
        numAssets = len(self.underliers)
        self.tick_base = [0.0] * numAssets
        self.max_pos = [1] * numAssets
        self.limit_price = [0.0] * numAssets
        self.max_vol = [10] * numAssets
        self.time_period = [600] * numAssets
        self.price_type = []

    def set_exec_args(self, idx, exec_args):
        pass

    def initialize(self):
        pass

    def on_tick(self, idx, ctick):
        pass

    def on_bar(self, idx, freq):
        pass

    def save_local_variables(self, file_writer):
        pass

    def load_local_variables(self, row):
        pass
