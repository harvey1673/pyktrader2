# -*- coding:utf-8 -*-
import json
import datetime

class CMQInstrument(object):
    class_params = {'pricing_ccy': 'USD'}
    def __init__(self, inst_data, market_data, model_settings={}):
        if isinstance(inst_data, (str, unicode)):
            inst_data = json.loads(inst_data)
        self.set_trade_data(inst_data)
        if len(market_data) > 0:
            self.set_market_data(market_data)
        if len(model_settings) > 0:
            self.set_model_settings(model_settings)

    def set_trade_data(self, trade_data):
        d = self.__dict__
        for key in self.class_params:
            d[key] = trade_data.get(key, self.class_params[key])
        self.set_inst_key()
        self.mkt_deps = {}

    def set_inst_key(self):
        self.inst_key = [self.__class__.__name__, self.pricing_ccy]
        self.generate_unique_id()

    def generate_unique_id(self):
        self.unique_id = '_'.join([str(key) for key in self.inst_key])

    def set_model_settings(self, model_settings):
        self.price_func = model_settings.get('price_func', 'clean_price')

    def set_market_data(self, market_data):
        self.value_date = market_data.get('value_date', datetime.date.today())

    def price(self):
        return getattr(self, self.price_func)

    def clean_price(self):
        return 0.0

    def dirty_price(self):
        return self.clean_price()

    def inst_key(self):
        return self.__class__.__name__

    def __str__(self):
        output = dict([(param, getattr(self, param)) for param in self.class_params])
        return json.dumps(output)

