# -*- coding:utf-8 -*-
import json
import cmq_inst

class CMQTradeStatus:
    Perspective, PendingSignoff, Live, Matured, Expired, Cancelled = range(6)

class CMQTrade(object):
    class_params = {'trader': 'harvey', 'sales': 'harvey', 'status': CMQTradeStatus.Perspective, \
                    'cpty': 'dummy', 'strategy': 'test', 'last_updated': ''}
    def __init__(self, trade_data):
        if isinstance(trade_data, (str, unicode)):
            trade_data = json.loads(trade_data)
        if "trade_id" not in trade_data:
            self.trade_id = ''
        self.update_trade_data(trade_data)

    def set_market_data(self, market_data):
        for inst in self.instruments:
            inst.set_market_data(market_data)

    def add_instrument(self, inst_data, pos):
        new_inst = self.create_instrument(inst_data)
        self.positions.append([new_inst, pos])

    def create_instrument(self, inst_data):
        if 'InstType' in inst_data:
            inst_type = inst_data["InstType"]
            cls_name = cmq_inst.trade_type_map[inst_type]
            cls_str = cls_name.split('.')
            inst_cls = getattr(__import__(str(cls_str[0])), str(cls_str[1]))
            return inst_cls(inst_data)

    def price(self):
        return sum([inst.price() * pos for inst, pos in self.positions])

    def update_trade_data(self, trade_data):
        d = self.__dict__
        for key in self.class_params:
            d[key] = trade_data.get(key, self.class_params[key])
        self.positions = [ [self.create_instrument(inst_data), pos] for inst_data, pos in trade_data.get('positions', []) ]

    def remove_instrument(self, inst_key):
        self.positions = [ [inst, pos] for inst, pos in self.positions if inst.inst_key != inst_key ]

    def __str__(self):
        output = dict([(param, getattr(self, param)) for param in self.class_params])
        output['position'] = [ [str(inst), pos] for inst, pos in self.positions ]
        return json.dumps(output)

class CMQBook(object):
    class_params = {'name': 'test_book', 'owner': 'harvey'}
    def __init__(self, book_data):
        if isinstance(book_data, (str, unicode)):
            trade_data = json.loads(book_data)
        self.load_book(book_data)

    def load_book(self, book_data):
        d = self.__dict__
        for key in self.class_params:
            d[key] = book_data.get(key, self.class_params[key])
        self.trade_list = [ CMQTrade(trade_data) for trade_data in book_data.get('trade_list', [])]
        self.inst_dict = {}
        for trade in self.trade_list:
            for inst, pos in trade.positions:
                if inst not in self.inst_dict:
                    self.inst_dict[inst] = 0
                self.inst_dict[inst] += pos

    def book_trade(self, cmq_trade):
        self.trade_list.append(cmq_trade)
        for inst, pos in zip(cmq_trade.instruments, cmq_trade.positions):
            if inst not in self.inst_dict:
                self.inst_dict[inst] = 0
            self.inst_dict[inst] += pos

    def update_inst_dict(self):
        inst_dict = {}
        for cmq_trade in self.trade_list:
            for inst, pos in zip(cmq_trade.instruments, cmq_trade.positions):
                if inst not in inst_dict:
                    inst_dict[inst] = 0
                inst_dict[inst] += pos
        self.inst_dict = inst_dict

    def mkt_deps(self):
        return {}

    def price(self):
        return sum([ trade.price() for trade in self.trade_list])

    def __str__(self):
        output = dict([(param, getattr(self, param)) for param in self.class_params])
        output['trade_list'] = [ str(trade) for trade in self.trade_list]
        return json.dumps(output)

if __name__ == '__main__':
    pass
