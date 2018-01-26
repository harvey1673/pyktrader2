import datetime
import pandas as pd
import numpy as np
import cmq_crv_defn
from cmq_inst import *
import cmq_curve
import misc

class CMQCommodForward(CMQInstrument):
    class_params = dict(CMQInstrument.class_params, **{ 'strike': 0.0,
                                                        'fwd_index': 'DCEIRO',
                                                        'need_disc': True})
    inst_key = ['fwd_index', 'strike', 'end', 'ccy', 'volume']

    def __init__(self, trade_data, market_data = {}, model_settings = {}):
        super(CMQCommodForward, self).__init__(trade_data, market_data, model_settings)

    def set_trade_data(self, trade_data):
        super(CMQCommodForward, self).set_trade_data(trade_data)
        self.mkt_deps['COMFwd'] = { self.fwd_index: [ 'ALL'] }
        if self.need_disc:
            self.mkt_deps['IRCurve'] = { self.ccy.lower() + '_disc': ['ALL'] }

    def set_market_data(self, market_data):
        super(CMQCommodForward, self).set_market_data(market_data)
        if len(market_data) == 0:
            self.fwd_curve = None
            self.fwd_avg = 0.0
            self.df = 1.0
            return
        fwd_quotes = market_data['COMFwd'][self.fwd_index]
        fwd_tenors = [ (self.value_date - quote[1]).days for quote in fwd_quotes]
        fwd_prices = [ quote[2] for quote in fwd_quotes]
        mode = cmq_curve.ForwardCurve.InterpMode.Linear
        self.fwd_curve = cmq_curve.ForwardCurve.from_array(fwd_tenors, fwd_prices, interp_mode = mode)
        self.fwd_avg = self.fwd_curve((self.value_date - self.end).days)
        if self.need_disc:
            self.df = disc_factor(self.value_date, self.end, market_data['IRCurve'][self.ccy.lower() + '_disc'])
        else:
            self.df = 1.0

    def clean_price(self):
        return (self.fwd_avg - self.strike) * self.df

class CMQCommodFuture(CMQInstrument):
    class_params = dict(CMQInstrument.class_params, **{ 'strike': 0.0,
                                                        'fwd_index': 'DCEIRO',
                                                        'contract': datetime.date(2018, 1, 1),
                                                        'end': datetime.date(2018, 1, 1),
                                                        'need_disc': False})
    inst_key = ['fwd_index', 'strike', 'end', 'ccy', 'volume']

    def __init__(self, trade_data, market_data = {}, model_settings = {}):
        super(CMQCommodFuture, self).__init__(trade_data, market_data, model_settings)

    def set_trade_data(self, trade_data):
        super(CMQCommodFuture, self).set_trade_data(trade_data)
        self.mkt_deps['COMFwd'] = {self.fwd_index: [self.contract]}
        if self.need_disc:
            self.mkt_deps['IRCurve'] = { self.ccy.lower() + '_disc': ['ALL'] }

    def set_market_data(self, market_data):
        super(CMQCommodFuture, self).set_market_data(market_data)
        if len(market_data) == 0:
            self.fwd_avg = 0.0
            self.df = 1.0
            return
        fwd_quotes = market_data['COMFwd'][self.fwd_index]
        for quote in fwd_quotes:
            if quote[0] == self.contract :
                self.fwd_avg = quote[2]
                break
        if self.need_disc:
            self.df = disc_factor(self.value_date, self.end, market_data['IRCurve'][self.ccy.lower() + '_disc'])
        else:
            self.df = 1.0

    def clean_price(self):
        return (self.fwd_avg - self.strike) * self.df
