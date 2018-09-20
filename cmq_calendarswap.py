import datetime
import pandas as pd
import numpy as np
import cmq_crv_defn
from cmq_inst import *
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
        prodcode = crv_info['instID']
        roll_rule = crv_info['roll_rule']
        spotID = crv_info['spotID']
        self.fixing_dates = [d for d in day_range if misc.is_workday(d, crv_info['calendar'])]
        nbcont = crv_info.get('nbcont', 1)
        contlist, exp_dates, tenorlist = misc.cont_expiry_list(prodcode, self.start, self.end, roll_rule)
        n = 0
        self.fixing_map = []
        self.fwd_map = []
        for d in self.fixing_dates:
            while d > exp_dates[n]:
                n += 1
            self.fwd_map.append(tenorlist[n + nbcont -1])
            if spotID == prodcode:
                self.fixing_map.append(contlist[n + nbcont -1] + '.' + 'fut_daily')
            else:
                self.fixing_map.append(spotID + '.' + 'spot_daily')
        self.mkt_deps['COMFix'] = {}
        for d, spot_id in zip(self.fixing_dates, self.fixing_map):
            if spot_id not in self.mkt_deps['COMFix']:
                self.mkt_deps['COMFix'][spot_id] = []
            self.mkt_deps['COMFix'][spot_id].append(d)
        self.mkt_deps['COMFwd'] = { self.fwd_index: list(set(self.fwd_map)) }
        if self.need_disc:
            self.mkt_deps['IRCurve'] = { self.ccy.lower() + '_disc': ['ALL'] }

    def set_market_data(self, market_data):
        super(CMQCalendarSwap, self).set_market_data(market_data)
        self.past_fix = []
        self.fwd_fix = []
        self.past_avg = 0.0
        self.fwd_avg = 0.0
        self.df = 1.0
        if len(market_data) == 0:
            return
        fwd_dict = dict([(q[0], q[2]) for q in market_data['COMFwd'][self.fwd_index]])
        for d, spot, cont in zip(self.fixing_dates, self.fixing_map, self.fwd_map):
            if (d < self.value_date) or ((d == self.value_date) and self.eod_flag):
                val = cmq_crv_defn.lookup_fix_mark(spot, market_data, d)
                if val == None:
                    print "No fixing is found"
                    val = market_data['COMFwd'][self.fwd_index][0][2]
                self.past_fix.append(val)
            else:
                self.fwd_fix.append(fwd_dict[cont])
        if len(self.past_fix) > 0:
            self.past_avg = np.mean(self.past_fix)
        if len(self.fwd_fix) > 0:
            self.fwd_avg = np.mean(self.fwd_fix)
        if self.need_disc:
            self.df = disc_factor(self.value_date, self.end, market_data['IRCurve'][self.ccy.lower() + '_disc'])

    def clean_price(self):
        if self.value_date > self.end:
            return 0.0
        r = float(len(self.past_fix))/float(len(self.fixing_dates))
        avg = self.past_avg * r + self.fwd_avg * (1-r)
        return (avg - self.strike) * self.df

class CMQCalSwapFuture(CMQCalendarSwap):
    class_params = dict(CMQCalendarSwap.class_params, **{'need_disc': False})
    inst_key = ['fwd_index', 'strike', 'start', 'end', 'ccy', 'volume']

    def __init__(self, trade_data, market_data = {}, model_settings = {}):
        super(CMQCalSwapFuture, self).__init__(trade_data, market_data, model_settings)