# -*- coding:utf-8 -*-
from cmq_calendarswap import CMQCalendarSwap
import cmq_inst
import cmq_crv_defn
import bsopt
import copy
import misc
import cmq_volgrid
import numpy as np
import workdays
import datetime

class CMQMthlyAsian(CMQCalendarSwap):
    class_params = dict(CMQCalendarSwap.class_params, **{ 'otype': 'C', 'accrual': 'act252', 'need_disc': False})
    inst_key = ['fwd_index', 'otype', 'strike', 'start', 'end', 'ccy', 'volume']

    def __init__(self, trade_data, market_data = {}, model_settings = {}):
        super(CMQMthlyAsian, self).__init__(trade_data, market_data, model_settings)

    def set_trade_data(self, trade_data):
        super(CMQMthlyAsian, self).set_trade_data(trade_data)
        for field in cmq_crv_defn.COMVOL_fields:
            if field not in self.mkt_deps:
                self.mkt_deps[field] = {}
            self.mkt_deps[field][self.fwd_index] = copy.deepcopy(self.mkt_deps['COMFwd'][self.fwd_index])

    def set_market_data(self, market_data):
        super(CMQMthlyAsian, self).set_market_data(market_data)
        if len(market_data) == 0:
            self.volmark = None
            return
        self.volmark = cmq_crv_defn.lookup_vol_mark(self.fwd_index, market_data, self.end, \
                                               vol_fields = cmq_crv_defn.COMVOL_fields)

    def clean_price(self):
        if self.value_date > self.end:
            return 0.0
        ws = 1.0 if (self.otype[0].upper() == 'C') else -1.0
        n = len(self.fixing_dates)
        m = len(self.past_fix)
        if n == m:
            return max((self.past_avg - self.strike) * ws, 0.0)
        strike = (self.strike * n - self.past_avg * m)/float(n - m)
        if strike < 0:
            return max((self.past_avg * m + self.fwd_avg * (n - m))/float(n) - self.strike, 0) if ws > 0 else 0.0
        volnode = cmq_volgrid.Delta5VolNode( self.value_date, \
                                        self.volmark['expiry'], \
                                        self.fwd_avg, \
                                        self.volmark['COMVolATM'], \
                                        self.volmark['COMVolV90'], \
                                        self.volmark['COMVolV75'], \
                                        self.volmark['COMVolV25'], \
                                        self.volmark['COMVolV10'], \
                                        "act365")
        ivol = volnode.GetVolByStrike( strike, self.end)
        cal_str = cmq_crv_defn.COM_Curve_Map[self.fwd_index]['calendar'] + '_Holidays'
        hols = getattr(misc, cal_str)
        tau = misc.conv_expiry_date(self.value_date + datetime.timedelta(days = int(self.eod_flag)), \
                                    self.start - datetime.timedelta(days=1), \
                                    self.accrual, hols)
        t_exp = misc.conv_expiry_date(self.value_date + datetime.timedelta(days = int(self.eod_flag)), \
                                    self.end, self.accrual, hols)
        vol_adj = bsopt.asian_vol_adj(ivol, t_exp, tau)
        pr =  bsopt.BSFwd((ws>0), self.fwd_avg, strike, vol_adj, t_exp, 0) * self.df * float(n - m) / float(n)
        return pr

if __name__ == '__main__':
    pass