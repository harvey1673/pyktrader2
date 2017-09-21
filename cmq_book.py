# -*- coding:utf-8 -*-
import cmq_inst
import cmq_utils

class CMQTradeStatus:
    Perspective, PendingSignoff, Live, Matured, Cancelled = range(5)

class CMQTrade(object):
    class_params = {'trader': 'harvey', 'sales': 'harvey', 'status': CMQTradeStatus.Perspective, \
                    'cpty': 'dummy', 'positions': [], 'instruments': [], 'last_updated': ''}
    def __init__(self, trade_data):
        if "trade_id" not in trade_data:
            self.trade_id = ''
        self.update_trade_data(trade_data)

    def set_market_data(self, market_data):
        for inst in self.instruments:
            inst.set_market_data(market_data)

    def add_instrument(self, inst_data, pos):
        self.positions.append(pos)
        self.instruments.append(self.create_instrument(inst_data))

    def create_instrument(self, inst_data):
        if 'InstType' in inst_data:
            inst_type = inst_data["InstType"]
            cls_name = cmq_inst.trade_type_map[inst_type]
            cls_str = cls_name.split('.')
            inst_cls = getattr(__import__(str(cls_str[0])), str(cls_str[1]))
            return inst_cls(inst_data)

    def price(self):
        return sum([inst.price() * pos for inst, pos in zip(self.instruments, self.positions)])

    def update_trade_data(self, trade_data):
        d = self.__dict__
        for key in self.class_params:
            d[key] = trade_data.get(key, self.class_params[key])
        self.instruments = [self.create_instrument(inst_data) for inst_data in self.instruments]

    def to_json(self):
        pass

class CMQBook(object):
    def __init__(self, book_data):
        self.name = book_data.get('Name', 'test')
        self.trader = book_data.get('Owner', 'harvey')
        self.trade_list = self.load_trades

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
