import datetime
import numpy as np
import cmq_crv_defn
from cmq_inst import *
from cmq_cmfwd import CMQCommodFuture
import cmq_curve
import misc
import cmq_volgrid
import bsopt
import copy

class CMQCommodEuOpt(CMQCommodFuture):
    class_params = dict(CMQCommodFuture.class_params, **{ 'strike': 0.0,
                                                        'fwd_index': 'SGXIRO',
                                                        'contract': datetime.date(2018, 1 ,1),
                                                        'accrual': 'act252',
                                                        'otype': 'C',
                                                        'need_disc': True})
    inst_key = ['fwd_index', 'contract', 'otype', 'strike', 'end', 'ccy', 'volume']

    def __init__(self, trade_data, market_data = {}, model_settings = {}):
        super(CMQCommodEuOpt, self).__init__(trade_data, market_data, model_settings)
        self.volnode = None
        self.ivol = 0.0

    def set_trade_data(self, trade_data):
        super(CMQCommodEuOpt, self).set_trade_data(trade_data)
        for field in cmq_crv_defn.COMVOL_fields:
            if field not in self.mkt_deps:
                self.mkt_deps[field] = {}
            self.mkt_deps[field][self.fwd_index] = copy.deepcopy(self.mkt_deps['COMFwd'][self.fwd_index])

    def set_model_settings(self, model_settings):
        super(CMQCommodEuOpt, self).set_model_settings(model_settings)
        self.alpha = model_settings.get('alpha', 0.8)
        self.beta = model_settings.get('beta', 1.2)

    def set_market_data(self, market_data):
        super(CMQCommodEuOpt, self).set_market_data(market_data)
        if len(market_data) == 0:
            self.volmark = None
        else:
            self.volmark = cmq_crv_defn.lookup_vol_mark(self.fwd_index, market_data, self.end, \
                                                    vol_fields=cmq_crv_defn.COMVOL_fields)

    def clean_price(self):
        ws = 1.0 if (self.otype[0].upper() == 'C') else -1.0
        self.volnode = cmq_volgrid.SamuelDelta5VolNode(self.value_date, \
                                            self.volmark['expiry'], \
                                            self.fwd_avg, \
                                            self.volmark['COMVolATM'], \
                                            self.volmark['COMVolV90'], \
                                            self.volmark['COMVolV75'], \
                                            self.volmark['COMVolV25'], \
                                            self.volmark['COMVolV10'], \
                                            self.alpha,\
                                            self.beta, \
                                            self.accrual)
        self.ivol = self.volnode.GetVolByStrike(self.strike, self.end)
        t_exp = misc.conv_expiry_date(self.value_date, self.end, self.accrual, [])
        pr = bsopt.BSFwd((ws > 0), self.fwd_avg, self.strike, self.ivol, t_exp, 0) * self.df
        return pr
