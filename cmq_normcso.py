import datetime
import numpy as np
import cmq_crv_defn
from cmq_inst import CMQInstrument
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
                                                        'need_disc': True})
    inst_key = ['fwd_index', 'contract', 'otype', 'strike', 'end', 'ccy']

    def __init__(self, trade_data, market_data = {}, model_settings = {}):
        super(CMQNormalCSO, self).__init__(trade_data, market_data, model_settings)
        self.ivol = 0.0

    def set_trade_data(self, trade_data):
        super(CMQNormalCSO, self).set_trade_data(trade_data)
        self.mkt_deps['COMFwd'] = { self.fwd_index: [self.leg_a, self.leg_b] }
        self.leg_diff = min(abs((self.leg_b.year * 12 + self.leg_b.month) - (self.leg_a.year * 12 + self.leg_b.month)), 4)
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
                break
        self.ivol = cmq_crv_defn.lookup_vol_mark(self.fwd_index, market_data, self.end, \
                                                    vol_fields=cmq_crv_defn.COMVOL_fields)
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
