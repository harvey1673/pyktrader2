import datetime
import pandas as pd
import numpy as np
import cmq_crv_defn
from cmq_inst import CMQInstrument
import cmq_curve
import misc

class CMQCalendarSwap(CMQInstrument):
    class_params = dict(CMQInstrument.class_params, **{ 'strike': 0.0,
                                                        'fwd_index': 'SGXIRO',
                                                        'need_disc': True})
    inst_key = ['fwd_index', 'strike', 'start', 'end', 'ccy']

    def __init__(self, trade_data, market_data = {}, model_settings = {}):
        super(CMQCalendarSwap, self).__init__(trade_data, market_data, model_settings)

    def set_trade_data(self, trade_data):
        super(CMQCalendarSwap, self).set_trade_data(trade_data)
        num_days = (self.end - self.start).days + 1
        day_range = [ self.start + datetime.timedelta(days = d) for d in range(num_days)]
        crv_info = cmq_crv_defn.COM_Curve_Map[self.fwd_index]
        self.spotID = crv_info['spotID']
        self.fixing_dates = [d for d in day_range if misc.is_workday(d, crv_info['calendar'])]
        self.fwd_tenors = cmq_crv_defn.curve_expiry(crv_info['exch'], self.fwd_index, self.start, self.end)
        self.mkt_deps['COMFix'] = { self.spotID: self.fixing_dates }
        self.mkt_deps['COMFwd'] = { self.fwd_index: [ x1 for x1, x2 in self.fwd_tenors] }
        if self.need_disc:
            self.mkt_deps['IRCurve'] = { self.ccy.lower() + '_disc': ['ALL'] }

    def set_market_data(self, market_data):
        super(CMQCalendarSwap, self).set_market_data(market_data)
        if len(market_data) == 0:
            self.fwd_curve = None
            self.fix_series =  None
            self.past_fix = []
            self.past_avg = 0.0
            self.fwd_avg = 0.0
            self.df = 1.0
            return
        fwd_quotes = market_data['COMFwd'][self.fwd_index]
        fwd_tenors = [ (self.value_date - quote[1]).days for quote in fwd_quotes]
        fwd_prices = [ quote[2] for quote in fwd_quotes]
        #fwd_quotes = map(list, zip(*fwd_quotes))
        mode = cmq_curve.ForwardCurve.InterpMode.PiecewiseConst
        self.fwd_curve = cmq_curve.ForwardCurve.from_array(fwd_tenors, fwd_prices, interp_mode = mode)
        fix_quotes = market_data['COMFix'][self.spotID]
        fix_quotes = map(list, zip(*fix_quotes))
        self.fix_series = pd.Series(fix_quotes[1], index = fix_quotes[0])
        self.past_fix = [d for d in self.fixing_dates if
                     (d < self.value_date) or ((d == self.value_date) and self.eod_flag)]
        fut_t = [(self.value_date - d).days for d in self.fixing_dates if d not in self.past_fix]
        if len(self.past_fix) > 0:
            self.past_avg = np.mean(self.fix_series[self.past_fix])
        else:
            self.past_avg = 0.0
        self.fwd_avg = np.mean(self.fwd_curve(fut_t))
        if self.need_disc and (self.end >= self.value_date):
            rate_quotes = market_data['IRCurve'][self.ccy.lower() + '_disc']
            tenors = [(quote[1] - self.value_date).days for quote in rate_quotes]
            irates = [quote[2] for quote in rate_quotes]
            mode = cmq_curve.ForwardCurve.InterpMode.Linear
            rate_curve = cmq_curve.ForwardCurve.from_array(tenors, irates, interp_mode = mode)
            t_exp = (self.end-self.value_date).days
            self.df = np.exp(-rate_curve(t_exp)*t_exp/365.0)
        else:
            self.df = 1.0

    def clean_price(self):
        r = float(len(self.past_fix))/float(len(self.fixing_dates))
        avg = self.past_avg * r + self.fwd_avg * (1-r)
        return (avg - self.strike) * self.df
