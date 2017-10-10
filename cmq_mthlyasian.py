# -*- coding:utf-8 -*-
from cmq_calendarswap import CMQCalendarSwap
import cmq_inst
import cmq_crv_defn
import bsopt
import copy
import misc
import cmqlib as qlib
import numpy as np
import workdays
import datetime

class CMQMthlyAsian(CMQCalendarSwap):
    class_params = dict(CMQCalendarSwap.class_params, **{ 'otype': 'C', 'accrual': 'act252', 'need_disc': False})
    inst_key = ['fwd_index', 'otype', 'strike', 'start', 'end', 'ccy']

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
        #vol_idx = cmq_crv_defn.COM_Curve_Map[self.fwd_index]['vol_index']
        self.volmark = cmq_crv_defn.lookup_vol_mark(self.fwd_index, market_data, self.end, \
                                               vol_fields = cmq_crv_defn.COMVOL_fields)

    def clean_price(self):
        ws = 1.0 if (self.otype[0].upper() == 'C') else -1.0
        n = len(self.fixing_dates)
        m = len(self.past_fix)
        if n == m:
            return max((self.past_avg - self.strike) * ws, 0.0)
        strike = (self.strike * n - self.past_avg * m)/float(n - m)
        if strike < 0:
            return max((self.past_avg * m + self.fwd_avg * (n - m))/float(n) - self.strike, 0) if ws > 0 else 0.0
        volnode = qlib.Delta5VolNode( misc.date2xl(self.value_date), \
                                      misc.date2xl(self.volmark['expiry']), \
                                      self.fwd_avg, \
                                      self.volmark['COMVolATM'], \
                                      self.volmark['COMVolV90'], \
                                      self.volmark['COMVolV75'], \
                                      self.volmark['COMVolV25'], \
                                      self.volmark['COMVolV10'], \
                                      "act365")
        ivol = volnode.GetVolByStrike( strike, misc.date2xl(self.end))
        if self.accrual == 'act252':
            cal_str = cmq_crv_defn.COM_Curve_Map[self.fwd_index]['calendar'] + '_Holidays'
            hols = getattr(misc, cal_str)
            tau = max(workdays.networkdays(self.value_date + datetime.timedelta(days = int(self.eod_flag)), \
                                       self.start - datetime.timedelta(days = 1), hols)/252.0, 0.0)
            t_exp = tau + (n - m)/252.0
        else:
            t_exp = ((self.end - self.value_date).days + int(not self.eod_flag))/365.25
            tau = max((self.start - self.value_date).days - int(self.eod_flag), 0.0)/365.25
        exp_m = (2.0 * np.exp(ivol * ivol * t_exp) - 2.0 * np.exp(ivol * ivol * tau) * \
                (1.0 + ivol * ivol * (t_exp - tau))) / ((ivol ** 4) * ((t_exp - tau) ** 2))
        vol_adj = np.sqrt(np.log(exp_m) / t_exp)
        pr =  bsopt.BSFwd((ws>0), self.fwd_avg, strike, vol_adj, t_exp, 0) * self.df * float(n - m) / float(n)
        return pr

if __name__ == '__main__':
    pass
