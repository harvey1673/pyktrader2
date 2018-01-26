from cmq_fxfwd import CMQFXForward
import cmq_crv_defn
import cmq_volgrid
import cmq_curve
import misc
import bsopt

class CMQFXOption(CMQFXForward):
    class_params = dict(CMQFXForward.class_params, **{ 'otype': 'C' })
    inst_key = ['ccypair', 'otype', 'strike', 'end', 'ccy', 'volume']

    def __init__(self, trade_data, market_data = {}, model_settings = {}):
        super(CMQFXOption, self).__init__(trade_data, market_data, model_settings)

    def set_trade_data(self, trade_data):
        super(CMQFXOption, self).set_trade_data(trade_data)
        for field in cmq_crv_defn.FXVOL_fields:
            if field not in self.mkt_deps:
                self.mkt_deps[field] = {}
            self.mkt_deps[field][self.ccypair] = { self.ccypair: [ 'ALL'] }

    def set_market_data(self, market_data):
        super(CMQFXOption, self).set_market_data(market_data)
        if len(market_data) == 0:
            self.volmark = None
        else:
            vol_fields = cmq_crv_defn.FXVOL_fields
            vol_quotes = dict([(field, []) for field in ['expiry'] + vol_fields])
            for idx, v_quote in enumerate(market_data[vol_fields[0]][self.ccypair]):
                vol_quotes['expiry'].append(v_quote[1])
                for field in vol_fields:
                    vol_quotes[field].append(market_data[field][self.ccypair][idx][2])
            vol_tenors = [(self.value_date - exp_date).days for exp_date in vol_quotes['expiry']]
            self.volmark = dict([(field, 0.0) for field in vol_fields])
            tom = (self.value_date - self.end).days
            for idx, field in enumerate(vol_fields):
                if idx == 0:
                    mode = cmq_curve.VolCurve.InterpMode.LinearTime
                else:
                    mode = cmq_curve.VolCurve.InterpMode.SqrtTime
                vcurve = cmq_curve.VolCurve.from_array( vol_tenors, vol_quotes[field], interp_mode = mode )
                self.volmark[field] = vcurve(tom)

    def clean_price(self):
        ws = 1.0 if (self.otype[0].upper() == 'C') else -1.0
        self.volnode = cmq_volgrid.Delta5VolNode(self.value_date, \
                                            self.end, \
                                            self.fx_fwd, \
                                            self.volmark['FXVolATM'], \
                                            self.volmark['FXVolV90'], \
                                            self.volmark['FXVolV75'], \
                                            self.volmark['FXVolV25'], \
                                            self.volmark['FXVolV10'], \
                                            self.accrual)
        self.ivol = self.volnode.GetVolByStrike(self.strike, self.end)
        t_exp = misc.conv_expiry_date(self.value_date, self.end, self.accrual, [])
        pr = bsopt.BSFwd((ws > 0), self.fx_fwd, self.strike, self.ivol, t_exp, 0)/self.fx_fwd * self.df
        return pr
