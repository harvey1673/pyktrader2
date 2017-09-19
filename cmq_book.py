# -*- coding:utf-8 -*-
import cmq_inst
import cmq_utils

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
