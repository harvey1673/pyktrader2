# -*- coding:utf-8 -*-
import cmq_inst
import cmq_utils

class CMQTrade(object):
    def __init__(self, trade_data):
        self.load_trade(trade_data)

    def load_trade(self, trade_data):
        self.name = trade_data.get('id', 'test_trade')
        self.trader = trade_data.get('trader', 'harvey')
        self.sales = trade_data.get('sales', 'harvey')
        self.cpty = trade_data.get('cpty', 'dummy')
        self.positions = trade_data.get('positions', [])
        all_insts = trade_data.get('instruments', [])
        self.instruments = [self.create_instrument(inst_data) for inst_data in all_insts]

    def set_market_data(self, market_data):
        for inst in self.instruments:
            inst.set_market_data(market_data)

    def create_instrument(self, inst_data):
        if 'InstType' in inst_data:
            inst_type = inst_data["InstType"]
            cls_name = cmq_inst.trade_type_map[inst_type]
            cls_str = cls_name.split('.')
            inst_cls = getattr(__import__(str(cls_str[0])), str(cls_str[1]))
            return inst_cls(inst_data)

class CMQBook(object):
    def __init__(self, book_data):
        self.name = book_data.get('name', 'test')
        self.trader = book_data.get('name', 'harvey')
        self.positions = self.load_position_from_dict(book_data)

    def mkt_deps(self):
        return {}

    def load_position_from_dict(self, book_data):
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

    def key_field(self):
        return

if __name__ == '__main__':
    pass
