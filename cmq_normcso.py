import datetime
import numpy as np
import cmq_crv_defn
from cmq_inst import *
import cmq_curve
import misc
import cmq_volgrid
import bsopt
import copy

class CMQNormalCSO(CMQInstrument):
    class_params = dict(CMQInstrument.class_params, **{ 'strike': 0.0,
                                                        'fwd_index': 'SGXIRO',
                                                        'leg_a': datetime.date(2018, 1 ,1),
                                                        'leg_b': datetime.date(2018, 2, 1),
                                                        'accrual': 'act252',
                                                        'otype': 'C',
                                                        'leg_diff': 1,
                                                        'need_disc': True})
    inst_key = ['fwd_index', 'leg_a', 'leg_b', 'otype', 'strike', 'end', 'ccy', 'volume']

    def __init__(self, trade_data, market_data = {}, model_settings = {}):
        super(CMQNormalCSO, self).__init__(trade_data, market_data, model_settings)
        self.ivol = 0.0

    def set_trade_data(self, trade_data):
        super(CMQNormalCSO, self).set_trade_data(trade_data)
        self.mkt_deps['COMFwd'] = { self.fwd_index: [self.leg_a, self.leg_b] }
        self.leg_diff = 1
        self.mkt_deps['COMDV'+str(self.leg_diff)] = { self.fwd_index: [self.leg_a] }
        if self.need_disc:
            self.mkt_deps['IRCurve'] = { self.ccy.lower() + '_disc': ['ALL'] }

    def set_model_settings(self, model_settings):
        super(CMQNormalCSO, self).set_model_settings(model_settings)

    def set_market_data(self, market_data):
        super(CMQNormalCSO, self).set_market_data(market_data)
        if len(market_data) == 0:
            self.fwd_avg = 1.0
            self.df = 1.0
            return
        fwd_quotes = market_data['COMFwd'][self.fwd_index]
        for quote in fwd_quotes:
            if quote[0] == self.leg_a:
                self.fwd_a = quote[2]
                continue
            elif quote[0] == self.leg_b:
                self.fwd_b = quote[2]
                break
        volmark = cmq_crv_defn.lookup_vol_mark(self.fwd_index, market_data, self.end, \
                                                    vol_fields=['COMDV'+str(self.leg_diff)])
        self.ivol = volmark['COMDV'+str(self.leg_diff)]
        if self.need_disc:
            self.df = disc_factor(self.value_date, self.end, market_data['IRCurve'][self.ccy.lower() + '_disc'])
        else:
            self.df = 1.0

    def clean_price(self):
        ws = 1.0 if (self.otype[0].upper() == 'C') else -1.0
        cal_str = cmq_crv_defn.COM_Curve_Map[self.fwd_index]['calendar'] + '_Holidays'
        hols = getattr(misc, cal_str)
        t_exp = misc.conv_expiry_date(self.value_date, self.end, self.accrual, hols)
        pr = bsopt.BSFwdNormal((ws > 0), self.fwd_a - self.fwd_b, self.strike, self.ivol, t_exp, 0) * self.df
        return pr
