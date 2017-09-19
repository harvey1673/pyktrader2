# -*- coding:utf-8 -*-
import copy
import cmq_utils

class CMQInstrument(object):
    def __init__(self, trade_data, market_data, model_settings={}):
        self.price_func_key = 'clean_price'
        self.set_trade_data(trade_data)
        if len(market_data) > 0:
            self.set_market_data(market_data)
        if len(model_settings) > 0:
            self.set_model_settings(model_settings)

    def set_market_data(self, market_data):
        self.value_date = market_data['MarketDate']

    def set_trade_data(self, trade_data):
        self.pricing_ccy = trade_data.get('PricingCCY', 'USD')
        self.notional = trade_data.get('Notional', 1.0)

    def set_model_settings(self, model_settings):
        pass

    def mkt_deps(self):
        return {}

    def price(self):
        return getattr(self, self.price_func_key)

    def clean_price(self):
        return 0.0

    def dirty_price(self):
        return 0.0

    def inst_key(self):
        return self.__class__.__name__
