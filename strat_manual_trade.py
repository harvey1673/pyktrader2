#-*- coding:utf-8 -*-
from base import *
from misc import *
import logging
from strategy import *

class ManualTrade(Strategy):
    common_params =  dict({'daily_close_buffer': 3, 'price_limit_buffer': 5}, \
                          **Strategy.common_params)
    asset_params = dict({}, **Strategy.asset_params)
    def __init__(self, config, agent = None):
        Strategy.__init__(self, config, agent)
        numAssets = len(self.underliers)
        self.tick_base = [0.0] * numAssets
        self.max_pos = [1] * numAssets

    def set_exec_args(self, idx, exec_args):
        pass
    