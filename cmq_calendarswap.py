import datetime
import pandas as pd
import cmq_crv_defn
from cmq_inst import CMQInstrument
import cmq_curve
import misc

class CMQCalendarSwap(CMQInstrument):
    class_params = dict(CMQInstrument.class_params, **{ 'strike': 0.0,
                                                        'fixing_index': 'tsi62',
                                                        'fwd_index': 'SGX_IO',
                                                        'start_date': datetime.date.today() + datetime.timedelta(days = 1), \
                                                        'end_date': datetime.date.today() + datetime.timedelta(days = 30)})
    def __init__(self, trade_data, market_data = {}, model_settings = {}):
        super(CMQCalendarSwap, self).__init__(trade_data, market_data, model_settings)

    def set_trade_data(self, trade_data):
        super(CMQCalendarSwap, self).set_trade_data(trade_data)
        num_days = (self.end_date - self.start_date).days + 1
        day_range = [ self.start_date + datetime.timedelta(days = d) for d in range(num_days)]
        crv_info = cmq_crv_defn.COM_Curve_Map[self.fwd_index]
        self.fixing_dates = [d for d in day_range if misc.is_workday(d, crv_info['calendar'])]
        self.fwd_tenors = cmq_crv_defn.curve_expiry(crv_info['exch'], self.fwd_index, self.start_date, self.end_date)
        self.set_inst_key()
        self.mkt_deps = {'fixings': { self.fixing_index: self.fixing_dates },
                         'fwdcurves': {self.fwd_index: [ x1 for x1, x2 in self.fwd_tenors] },}

    def set_inst_key(self):
        self.inst_key = [self.__class__.__name__, self.fwd_curve, self.fixing_index, self.strike, self.start_date, self.end_date, self.pricing_ccy]
        self.generate_unique_id()

    def set_market_data(self, market_data):
        super(CMQCalendarSwap, self).set_market_data(market_data)
        fwd_quotes = market_data['COMCurve_' + self.fwd_index]
        fwd_tenors = [ (quote[0] - self.value_date).days for quote in fwd_quotes]
        fwd_prices = [ quote[1] for quote in fwd_quotes]
        #fwd_quotes = map(list, zip(*fwd_quotes))
        self.fwd_curve = cmq_curve.ForwardCurve.from_array(fwd_tenors, fwd_prices)
        fix_quotes = market_data['COMFixing_' + self.fixing_index]
        fix_quotes = map(list, zip(*fix_quotes))
        self.fix_series = pd.Series(fix_quotes[1], index = fix_quotes[0])

    def clean_price(self):
        past_fixes = 0.0
        return 0.0
