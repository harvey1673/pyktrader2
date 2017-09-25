import datetime
import pandas as pd
import cmq_crv_defn
from cmq_calendarswap import CMQCalendarSwap
import cmq_curve
import misc

class CMQCalendarAsian(CMQCalendarSwap):
    class_params = dict(CMQCalendarSwap.class_params, **{ 'strike': 0.0, 'otype': 'C',
                                                        'fixing_index': 'tsi62',
                                                        'fwd_index': 'SGX_IO',
                                                        'start_date': datetime.date.today() + datetime.timedelta(days = 1), \
                                                        'end_date': datetime.date.today() + datetime.timedelta(days = 30)})
    def __init__(self, trade_data, market_data = {}, model_settings = {}):
        super(CMQCalendarSwap, self).__init__(trade_data, market_data, model_settings)

    def set_trade_data(self, trade_data):
        super(CMQCalendarSwap, self).set_trade_data(trade_data)

    def set_inst_key(self):
        self.inst_key = [self.__class__.__name__, self.fwd_curve, self.fixing_index, self.otype, self.strike, self.start_date, self.end_date, self.pricing_ccy]
        self.generate_unique_id()

    def set_market_data(self, market_data):
        super(CMQCalendarSwap, self).set_market_data(market_data)

    def clean_price(self):
        past_fix = [ d for d in self.fixing_dates if d < self.value_date]
        fut_fix = [ d for d in self.fixing_dates if d >= self.value_date]
        if self.value_date in self.fix_series.index:
            past_fix.append(self.value_date)
            fut_fix.remove(self.value_date)
        fut_t = [ (d - self.value_date).days for d in fut_fix]
        avg = (sum(self.fix_series[past_fix]) + sum(self.fwd_curve(fut_t)))/(len(past_fix) + len(fut_fix))
        return avg
