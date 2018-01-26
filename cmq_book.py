# -*- coding:utf-8 -*-
import json
import datetime
import itertools
import cmq_inst
import dbaccess
import misc

class CMQDealStatus:
    Perspective, PendingSignoff, Live, Matured, Unwinded, Cancelled = range(6)

class CMQBookStatus:
    Test, UAT, Prod = range(3)

def agg_mkt_deps(mkt_deps, inst_list):
    for inst in inst_list:
        for key in inst.mkt_deps:
            if key not in mkt_deps:
                mkt_deps[key] = {}
            for idx in inst.mkt_deps[key]:
                if idx not in mkt_deps[key]:
                    mkt_deps[key][idx] = []
                mkt_deps[key][idx] = list(set(mkt_deps[key][idx]).union(set(inst.mkt_deps[key][idx])))
                mkt_deps[key][idx].sort()
    return mkt_deps

class CMQDeal(object):
    id_generator = itertools.count(int(datetime.datetime.strftime(datetime.datetime.now(), '%d%H%M%S')))
    class_params = {'trader': 'harvey', 'sales': 'harvey', 'status': CMQDealStatus.Perspective, \
                    'cpty': 'dummy', 'strategy': 'test',\
                    'enter_date': datetime.date.today(), 'last_updated': datetime.datetime.now(), \
                    'last_date': datetime.date.today(), \
                    'external_id': 'dummy', 'external_src': 'dummy', \
                    'internal_id': 'dummy', 'business': 'commod', \
                    'desk': 'CST', 'prtfolio': 'test', 'product': 'SGIRO', \
                    'day1_comments': '', 'commission': 0.0, 'premium': 0.0}
    def __init__(self, deal_data):
        self.mkt_deps = {}
        if isinstance(deal_data, (str, unicode)):
            deal_data = json.loads(deal_data)
        self.id = deal_data.get('id', next(self.id_generator))
        self.update_deal_data(deal_data)

    def set_market_data(self, market_data):
        for inst, pos in self.positions:
            inst.set_market_data(market_data)

    def add_instrument(self, inst_data, pos):
        new_inst = self.create_instrument(inst_data)
        self.positions.append([new_inst, pos])

    def create_instrument(self, inst_data):
        if 'inst_type' in inst_data:
            inst_type = inst_data["inst_type"]
            cls_name = cmq_inst.inst_type_map[inst_type]
            cls_str = cls_name.split('.')
            inst_cls = getattr(__import__(str(cls_str[0])), str(cls_str[1]))
            return inst_cls.create_instrument(inst_data)
        else:
            print 'inst_type key is missing in the instrument data'
            return None

    def price(self):
        return sum([inst.price() * pos for inst, pos in self.positions])

    def update_deal_data(self, deal_data):
        d = self.__dict__
        for key in self.class_params:
            d[key] = deal_data.get(key, self.class_params[key])
        if isinstance(deal_data['positions'], (str, unicode)):
            pos_data =  json.loads(deal_data['positions'])
        else:
            pos_data = deal_data['positions']
        self.positions = [ [self.create_instrument(inst_data), pos] for inst_data, pos in pos_data ]
        agg_mkt_deps(self.mkt_deps, [inst for inst, pos in self.positions])

    def remove_instrument(self, inst_obj):
        self.positions = [ [inst, pos] for inst, pos in self.positions if inst != inst_obj ]
        self.mkt_deps = {}
        agg_mkt_deps(self.mkt_deps, [inst for inst, pos in self.positions])

    def __str__(self):
        output = dict([(param, getattr(self, param)) for param in self.class_params])
        output['position'] = [ [str(inst), pos] for inst, pos in self.positions ]
        return json.dumps(output)

class CMQBook(object):
    class_params = {'name': 'test_book', 'owner': 'harvey', 'reporting_ccy': 'USD', 'status': CMQBookStatus.Test}
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
        self.update_inst_dict()

    def book_deal(self, cmq_deal):
        self.deal_list.append(cmq_deal)
        for inst, pos in cmq_deal.positions:
            if inst not in self.inst_dict:
                self.inst_dict[inst] = 0
                agg_mkt_deps(self.mkt_deps, [inst])
            self.inst_dict[inst] += pos

    def update_inst_dict(self):
        self.inst_dict = {}
        self.mkt_deps= {}
        for cmq_deal in self.deal_list:
            for inst, pos in cmq_deal.positions:
                if inst not in self.inst_dict:
                    self.inst_dict[inst] = 0
                self.inst_dict[inst] += pos
        agg_mkt_deps(self.mkt_deps, self.deal_list)
        for inst in self.inst_dict:
            if inst.ccy != self.reporting_ccy:
                fx_pair = None
                fx_direction = misc.get_mkt_fxpair(self.reporting_ccy, inst.ccy)
                if fx_direction > 0 :
                    fx_pair =  '/'.join([self.reporting_ccy, inst.ccy])
                elif fx_direction < 0:
                    fx_pair = '/'.join([inst.ccy, self.reporting_ccy])
                else:
                    print "ERROR: unsupported FX pair: %s - %s" % (self.reporting_ccy, inst.ccy)
                    fx_pair = None
                if fx_pair != None:
                    if 'FXFwd' not in self.mkt_deps:
                        self.mkt_deps['FXFwd'] = {}
                    self.mkt_deps['FXFwd'][fx_pair] = ['ALL']

    def price(self):
        return sum([ deal.price() for deal in self.deal_list])

    def __str__(self):
        output = dict([(param, getattr(self, param)) for param in self.class_params])
        output['deal_list'] = [ str(deal) for deal in self.deal_list]
        return json.dumps(output)

def get_book_from_db(book_name, status, dbtable = 'trade_data'):
    cnx = dbaccess.connect(**dbaccess.trade_dbconfig)
    df = dbaccess.load_deal_data(cnx, dbtable, book = book_name, deal_status = status)
    deal_list = df.to_dict(orient = 'record')
    book_data = {'book': book_name,  'owner': 'harvey', 'reporting_ccy': 'USD', \
                 'status': CMQBookStatus.Prod, 'deal_list': deal_list }
    book_obj = CMQBook(book_data)
    return book_obj

if __name__ == '__main__':
    pass
