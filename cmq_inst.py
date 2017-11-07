# -*- coding:utf-8 -*-
import json
import datetime
import weakref

class CurveShiftType:
    Abs, Rel = range(2)

inst_type_map = {
    "ComCalSwap": "cmq_calendarswap.CMQCalendarSwap",
    "ComMthAsian": "cmq_mthlyasian.CMQMthlyAsian",
    "ComEuroOption": "cmq_commodeuopt.CMQCommodEuOpt",
    "ComDVolCSO": "cmq_normcso.CMQNormalCSO",
}

class CMQInstrument(object):
    _get_obj_cache = weakref.WeakValueDictionary()
    inst_key = [ 'start', 'end', 'ccy']
    class_params = {'ccy': 'USD', 'start': datetime.date.today() + datetime.timedelta(days = 2), \
                    'end': datetime.date.today() + datetime.timedelta(days = 3), }

    @classmethod
    def create_instrument(cls, inst_data, market_data = {}, model_setting = {}):
        cache = cls._get_obj_cache
        identifier = '_'.join([cls.__name__] + [ str(inst_data.get(key, cls.class_params[key])) for key in cls.inst_key])
        obj = cache.get(identifier, None)
        if obj is None:
            obj = cache[identifier] = cls(inst_data, market_data, model_setting)
        return obj

    def __init__(self, inst_data, market_data = {}, model_settings={}):
        self.id = '_'.join([self.__class__.__name__] + [ str(inst_data.get(key, self.class_params[key])) for key in self.inst_key])
        self.eod_flag = False
        self.cmdelta_shift = 0.0001
        self.cmdelta_type = CurveShiftType.Abs
        self.cmvega_shift = 0.005
        self.cmvega_type = CurveShiftType.Abs
        self.ycdelta_shift = 0.0001
        self.ycdelta_type = CurveShiftType.Abs
        self.swnvega_shift = 0.005
        self.swnvega_type = CurveShiftType.Abs
        self.fxdelta_shift = 0.005
        self.fxdelta_type = CurveShiftType.Abs
        self.theta_shift = 1
        self.theta_type = CurveShiftType.Abs
        self.fxvega_shift = 1
        self.fxvega_type = CurveShiftType.Abs
        if isinstance(inst_data, (str, unicode)):
            inst_data = json.loads(inst_data)
        self.set_trade_data(inst_data)
        self.inst_data = inst_data
        self.set_market_data(market_data)
        self.set_model_settings(model_settings)
        self.model_settings = model_settings

    def set_trade_data(self, trade_data):
        d = self.__dict__
        for key in self.class_params:
            d[key] = trade_data.get(key, self.class_params[key])
            if key in ['start', 'end'] and isinstance(d[key], basestring):
                d[key] = datetime.datetime.strptime(d[key], "%Y-%m-%d %H:%M:%S").date()
        self.mkt_deps = {}

    def set_model_settings(self, model_settings):
        self.price_func = model_settings.get('price_func', 'clean_price')

    def set_market_data(self, market_data):
        self.value_date = market_data.get('value_date', datetime.date.today())
        self.eod_flag = market_data.get('eod_flag', False)

    def price(self):
        return getattr(self, self.price_func)()

    def clean_price(self):
        return 0.0

    def dirty_price(self):
        return self.clean_price()

    def inst_key(self):
        return self.__class__.__name__

    def __str__(self):
        output = dict([(param, getattr(self, param)) for param in self.class_params])
        return json.dumps(output)

if __name__ == '__main__':
    pass
