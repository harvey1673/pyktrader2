# -*- coding:utf-8 -*-
import json
import cmq_inst

class CMQDealStatus:
    Perspective, PendingSignoff, Live, Matured, Expired, Cancelled = range(6)

def agg_mkt_deps(mkt_deps, inst_list):
    for inst in inst_list:
        for key in ['fixings', 'fwdcurves']:
            for idx in inst.mkt_deps[key]:
                if idx not in mkt_deps[key]:
                    mkt_deps[key][idx] = []
                    mkt_deps[key][idx] = list(set(mkt_deps[key][idx]).union(set(inst.mkt_deps[key][idx])))

class CMQDeal(object):
    class_params = {'trader': 'harvey', 'sales': 'harvey', 'status': CMQDealStatus.Perspective, \
                    'cpty': 'dummy', 'strategy': 'test', 'last_updated': ''}
    def __init__(self, deal_data):
        self.mkt_deps = {}
        if isinstance(deal_data, (str, unicode)):
            deal_data = json.loads(deal_data)
        if "deal_id" not in deal_data:
            self.deal_id = ''
        self.update_deal_data(deal_data)

    def set_market_data(self, market_data):
        for inst in self.instruments:
            inst.set_market_data(market_data)

    def add_instrument(self, inst_data, pos):
        new_inst = self.create_instrument(inst_data)
        self.positions.append([new_inst, pos])

    def create_instrument(self, inst_data):
        if 'InstType' in inst_data:
            inst_type = inst_data["InstType"]
            cls_name = cmq_inst.deal_type_map[inst_type]
            cls_str = cls_name.split('.')
            inst_cls = getattr(__import__(str(cls_str[0])), str(cls_str[1]))
            return inst_cls(inst_data)

    def price(self):
        return sum([inst.price() * pos for inst, pos in self.positions])

    def update_deal_data(self, deal_data):
        d = self.__dict__
        for key in self.class_params:
            d[key] = deal_data.get(key, self.class_params[key])
        self.positions = [ [self.create_instrument(inst_data), pos] for inst_data, pos in deal_data.get('positions', []) ]
        agg_mkt_deps(self.mkt_deps, self.positions)

    def remove_instrument(self, inst_key):
        self.positions = [ [inst, pos] for inst, pos in self.positions if inst.inst_key != inst_key ]
        self.mkt_deps = {}
        agg_mkt_deps(self.mkt_deps, self.positions)

    def __str__(self):
        output = dict([(param, getattr(self, param)) for param in self.class_params])
        output['position'] = [ [str(inst), pos] for inst, pos in self.positions ]
        return json.dumps(output)

class CMQBook(object):
    class_params = {'name': 'test_book', 'owner': 'harvey'}
    def __init__(self, book_data):
        self.mkt_deps = {}
        if isinstance(book_data, (str, unicode)):
            book_data = json.loads(book_data)
        self.load_book(book_data)

    def load_book(self, book_data):
        d = self.__dict__
        for key in self.class_params:
            d[key] = book_data.get(key, self.class_params[key])
        self.deal_list = [ CMQDeal(deal_data) for deal_data in book_data.get('deal_list', [])]
        self.inst_dict = {}
        for deal in self.deal_list:
            for inst, pos in deal.positions:
                if inst not in self.inst_dict:
                    self.inst_dict[inst] = 0
                self.inst_dict[inst] += pos
        agg_mkt_deps(self.mkt_deps, self.inst_dict.keys())

    def book_deal(self, cmq_deal):
        self.deal_list.append(cmq_deal)
        for inst, pos in zip(cmq_deal.instruments, cmq_deal.positions):
            if inst not in self.inst_dict:
                self.inst_dict[inst] = 0
                agg_mkt_deps(self.mkt_deps, [inst])
            self.inst_dict[inst] += pos

    def update_inst_dict(self):
        inst_dict = {}
        mkt_deps= {}
        for cmq_deal in self.deal_list:
            for inst, pos in zip(cmq_deal.instruments, cmq_deal.positions):
                if inst not in inst_dict:
                    inst_dict[inst] = 0
                    agg_mkt_deps(mkt_deps, [inst])
                inst_dict[inst] += pos
        self.inst_dict = inst_dict
        self.mkt_deps = mkt_deps

    def price(self):
        return sum([ deal.price() for deal in self.deal_list])

    def __str__(self):
        output = dict([(param, getattr(self, param)) for param in self.class_params])
        output['deal_list'] = [ str(deal) for deal in self.deal_list]
        return json.dumps(output)

if __name__ == '__main__':
    pass
