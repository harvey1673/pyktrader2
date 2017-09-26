import copy
import json
import workdays

trade_type_map = {
    "ComCalSwap": "cmq_rate_swap.CMQIRSwap",
    "Bermudan": "cmq_rate_swap.CMQIRBermSwaption",
    "FXOption": "cmq_fxopt.CMQFXOption",
}

class CMRiskEngine(object):
    def __init__(self, trade_data, market_data):
        self.market_data = market_data
        self.create_instrument(trade_data, market_data)
        self.req_greeks = trade_data.get("ReqRisks", ['pv'])
        self.run_flag = False
        self.cmdelta_shift = 0.0001
        self.cmvega_shift = 0.005
        self.ycdelta_shift = 0.0001
        self.swnvega_shift = 0.005
        self.fxdelta_shift = 0.005
        self.theta_shift = 1
        self.fxvega_shift = 1
        self.scenarios = {}
        self.results = {}
        self.calc_risks = {}
        self.pricing_ccy = trade_data.get("PricingCCY", "usd")

    def create_instrument(self, trade_data, market_data):
        trade_type = trade_data.get("TradeType", "IRS")
        cls_name = trade_type_map[trade_type]
        cls_str = cls_name.split('.')
        inst_cls = getattr(__import__(str(cls_str[0])), str(cls_str[1]))
        self.instrument = inst_cls(trade_data, market_data)

    def gen_market_data(self, market_data, scen):
        if hasattr(scen[0], '__iter__'):
            crv_type = scen[0][0].split('_')[0]
        else:
            crv_type = scen[0].split('_')[0]
        md = copy.deepcopy(market_data)
        if crv_type == "MarketDate":
            md[scen[0]] = workdays.workday(md[scen[0]], scen[1])
        else:
            if hasattr(scen[0], '__iter__'):
                data = md[scen[0][0]]
                for i in range(1, len(scen[0])):
                    data = data[scen[0][i]]
            else:
                data = md[scen[0]]
            if crv_type == 'FXFwd':
                for knot in data:
                    knot[1] = knot[1] * (1 + scen[1])
            else:
                for knot in data:
                    knot[1] = knot[1] + scen[1]
        return md

    def get_all_scens(self):
        all_scens = []
        for greek in self.req_greeks:
            item = greek.split('_')
            if item[0] == 'pv':
                scens = [("MarketDate", 0)]
            elif item[0] == 'theta':
                scens = [("MarketDate", 0), ("MarketDate", self.theta_shift)]
            elif item[0] in ['cmdelta', 'cmgamma']:
                scens = [('COMCurve_' + item[1], self.cmdelta_shift), ("MarketDate", 0),
                         ('COMCurve_' + item[1], -self.cmdelta_shift)]
            elif item[0] in ['ycdelta', 'ycgamma']:
                scens = [('IRYCurve_' + item[1], self.ycdelta_shift), ("MarketDate", 0),
                         ('IRYCurve_' + item[1], -self.ycdelta_shift)]
            elif item[0] == 'swnvega':
                scens = [('SWNVOL_' + item[1], self.swnvega_shift), ('SWNVOL_' + item[1], -self.swnvega_shift)]
            elif item[0] in ['fxdelta', 'fxgamma']:
                scens = [('FXFwd_' + item[1], self.fxdelta_shift), ("MarketDate", 0),
                         ('FXFwd_' + item[1], -self.fxdelta_shift)]
            elif item[0] == 'fxvega':
                scens = [(('FXVOL_' + item[1], 'ATM'), self.fxvega_shift), ("MarketDate", 0), \
                         (('FXVOL_' + item[1], 'ATM'), -self.fxvega_shift)]
            for s in scens:
                if s not in all_scens:
                    all_scens.append(s)
        for scen in all_scens:
            self.scenarios[scen] = self.gen_market_data(self.market_data, scen)

    def run_risk(self):
        self.get_all_scens()
        for scen in self.scenarios:  ## can do parallel computing here, get some worker on this
            self.instrument.set_market_data(self.scenarios[scen])
            self.results[scen] = self.instrument.price()
        for greek in self.req_greeks:
            item = greek.split('_')
            if item[0] == 'pv':
                self.calc_risks[greek] = self.results[("MarketDate", 0)]
            elif item[0] == 'theta':
                self.calc_risks[greek] = self.results[("MarketDate", 1)] - self.results[("MarketDate", 0)]
            elif item[0] == 'cmdelta':
                self.calc_risks[greek] = (self.results[('COMCurve_' + item[1], self.cmdelta_shift)] \
                                          - self.results[('COMCurve_' + item[1], -self.cmdelta_shift)]) / ( \
                                             2.0 * self.cmdelta_shift )
            elif item[0] == 'cmgamma':
                self.calc_risks[greek] = (self.results[('COMCurve_' + item[1], self.cmdelta_shift)] \
                                          - 2 * self.results[("MarketDate", 0)] \
                                          + self.results[('COMCurve_' + item[1], -self.cmdelta_shift)]) / ( \
                                             self.cmdelta_shift ** 2)
            elif item[0] == 'ycdelta':
                self.calc_risks[greek] = (self.results[('IRYCurve_' + item[1], self.ycdelta_shift)] \
                                          - self.results[('IRYCurve_' + item[1], -self.ycdelta_shift)]) / 2.0 / (
                                         self.ycdelta_shift * 10000)
            elif item[0] == 'ycgamma':
                self.calc_risks[greek] = (self.results[('IRYCurve_' + item[1], self.ycdelta_shift)] \
                                          - 2 * self.results[("MarketDate", 0)] \
                                          + self.results[('IRYCurve_' + item[1], - self.ycdelta_shift)]) / (
                                         (self.ycdelta_shift * 10000) ** 2)
            elif item[0] == 'fxdelta':  ## need to be careful here FX shift is assumed to be ratio multiplier
                self.calc_risks[greek] = (self.results[('FXFwd_' + item[1], self.fxdelta_shift)] \
                                          - self.results[('FXFwd_' + item[1], -self.fxdelta_shift)]) / (
                                         2 * self.fxdelta_shift)
            elif item[0] == 'fxgamma':
                self.calc_risks[greek] = (self.results[('FXFwd_' + item[1], self.fxdelta_shift)] - 2 * self.results[
                    ("MarketDate", 0)] \
                                          + self.results[('FXFwd_' + item[1], - self.fxdelta_shift)]) / (
                                         self.fxdelta_shift ** 2)
            elif item[0] == 'swnvega':
                self.results[greek] = (self.results[('SWNVOL_' + item[1], self.swnvega_shift)] \
                                       - self.results[('SWNVOL_' + item[1], - self.swnvega_shift)]) / (
                                      2 * self.swnvega_shift * 100.0)
            elif item[0] == 'fxvega':
                self.calc_risks[greek] = (self.results[(('FXVOL_' + item[1], 'ATM'), self.fxvega_shift)] \
                                          - self.results[(('FXVOL_' + item[1], 'ATM'), - self.fxvega_shift)]) / (
                                         2 * self.fxvega_shift * 100.0)
        return self.calc_risks

if __name__ == '__main__':
    pass
