# -*- coding:utf-8 -*-
import copy
import cmq_utils

class CMQInstrument(object):
    def __init__(self, trade_data, market_data, model_settings={}):
        self.set_market_data(market_data)
        self.set_trade_data(trade_data)
        self.set_model_settings(model_settings)

    def set_market_data(self, market_data):
        self.value_date = market_data['MarketDate']

    def set_trade_data(self, trade_data):
        pass

    def set_model_settings(self, model_settings):
        pass

    def mkt_deps(self):
        return {}

    def price(self):
        return getattr(self, 'price_func_key')

    def price_func_key(self):
        return 'clean_price'

    def clean_price(self):
        return 0.0

    def dirty_price(self):
        return 0.0

    def serialize(self):
        pass
