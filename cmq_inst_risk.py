# -*- coding:utf-8 -*-
import copy
import json
import cmq_inst
import workdays

def generate_scen(base_market, curve_type, curve_name, curve_tenor = 'ALL', shift_size = 0.0001, shift_type = cmq_inst.CurveShiftType.Abs):
    market_scen = copy.deepcopy(base_market)
    if curve_type == 'value_date':
        market_scen[curve_type] = workdays.workday(base_market[curve_type], shift_size)
    elif (curve_type in market_scen) and (curve_name in market_scen[curve_type]):
            for idx, value in enumerate(market_scen[curve_type][curve_name]):
                if curve_tenor == 'ALL' or value[0] == curve_tenor:
                    curve_shift = shift_size
                    if shift_type == cmq_inst.CurveShiftType.Rel:
                        curve_shift *= value[2]
                    market_scen[curve_type][curve_name][idx][2] += curve_shift
    return market_scen

class CMQInstRiskStore(object):
    def __init__(self, inst_obj, base_market, req_greeks):
        self.instrument = inst_obj
        self.base_market =base_market
        self.req_greeks = req_greeks
        self.scen_keys = []
        self.results = {}
        self.calc_risks = {}

    def get_scen_keys(self):
        self.scen_keys = []
        inst_obj = self.instrument
        for greek in self.req_greeks:
            scens = []
            if greek == 'pv':
                scens += [("value_date", "value_date", "ALL", 0)]
            elif greek == 'theta':
                scens += [("value_date", "value_date", "ALL", 0), ("value_date", "value_date", "ALL", inst_obj.theta_shift)]
            elif greek in ['cmdelta', 'cmgamma']:
                for fwd_idx in inst_obj.mkt_deps['COMFwd']:
                    scens += [('COMFwd',  fwd_idx, 'ALL', inst_obj.cmdelta_shift), ('COMFwd', fwd_idx, 'ALL', -inst_obj.cmdelta_shift)]
            elif greek == 'cmvega':
                for vol_idx in inst_obj.mkt_deps['COMVolATM']:
                    scens += [('COMVolATM', vol_idx, 'ALL', inst_obj.cmvega_shift), ('COMVolATM', vol_idx, 'ALL', -inst_obj.cmvega_shift)]
            elif greek in ['cmdeltas', 'cmgammas']:
                for fwd_idx in inst_obj.mkt_deps['COMFwd']:
                    for tenor in inst_obj.mkt_deps['COMFwd'][fwd_idx]:
                        scens += [('COMFwd',  fwd_idx, tenor, inst_obj.cmdelta_shift), ('COMFwd', fwd_idx, tenor, -inst_obj.cmdelta_shift)]
            elif greek == 'cmvegas':
                for vol_idx in inst_obj.mkt_deps['COMVolATM']:
                    for tenor in inst_obj.mkt_deps['COMVolATM'][vol_idx]:
                        scens += [('COMVolATM', vol_idx, tenor, inst_obj.cmvega_shift), ('COMVolATM', vol_idx, tenor, -inst_obj.cmvega_shift)]
            elif greek in ['ycdelta', 'ycgamma']:
                for fwd_idx in self.instrument.mkt_deps['IRCurve']:
                    scens += [('IRCurve', fwd_idx, 'ALL', inst_obj.ycdelta_shift), ('IRCurve', fwd_idx, 'ALL', -inst_obj.ycdelta_shift)]
            elif greek == 'swnvega':
                for vol_idx in inst_obj.mkt_deps['IRSWNVol']:
                    scens += [('IRSWNVol', vol_idx, 'ALL', inst_obj.swnvega_shift), ('IRSWNVol', vol_idx, 'ALL', -inst_obj.swnvega_shift)]
            elif greek in ['fxdelta', 'fxgamma']:
                for fwd_idx in inst_obj.mkt_deps['FXFwd']:
                    scens += [('FXFwd', fwd_idx, 'ALL', inst_obj.fxdelta_shift), ('FXFwd', fwd_idx, 'ALL', -inst_obj.fxdelta_shift)]
            elif greek == 'fxvega':
                for vol_idx in inst_obj.mkt_deps['FXVolATM']:
                    scens += [('FXVolATM', vol_idx, 'ALL', inst_obj.fxvega_shift), ('FXVolATM', vol_idx, 'ALL', -inst_obj.fxvega_shift)]
            if 'gamma' in greek:
                scens += [("value_date", "value_date", "ALL", 0)]
            for scen in scens:
                if scen not in self.scen_keys:
                    self.scen_keys.append(scen)
        return self.scen_keys

    def run_risk(self, scenarios = {}):
        inst_obj = self.instrument
        for scen in self.scen_keys:  ## can do parallel computing here, get some worker on this
            inst_obj.set_market_data(scenarios[scen])
            self.results[scen] = inst_obj.price()
        for greek in self.req_greeks:
            if greek == 'pv':
                self.calc_risks[greek] = self.results[("value_date", "value_date", "ALL", 0)]
            elif greek == 'theta':
                self.calc_risks[greek] = self.results[("value_date", "value_date", "ALL", inst_obj.theta_shift)] \
                                         - self.results[("value_date", "value_date", "ALL", 0)]
            elif greek == 'cmdelta':
                self.calc_risks[greek] = {}
                for fwd_idx in inst_obj.mkt_deps['COMFwd']:
                    self.calc_risks[greek][fwd_idx] = (self.results[('COMFwd', fwd_idx, 'ALL', inst_obj.cmdelta_shift)] \
                                          - self.results[('COMFwd', fwd_idx, 'ALL', -inst_obj.cmdelta_shift)]) / ( \
                                             2.0 * inst_obj.cmdelta_shift )
            elif greek == 'cmgamma':
                self.calc_risks[greek] = {}
                for fwd_idx in inst_obj.mkt_deps['COMFwd']:
                    self.calc_risks[greek][fwd_idx] = (self.results[('COMFwd', fwd_idx, 'ALL', inst_obj.cmdelta_shift)] \
                                          - 2 * self.results[("value_date", "value_date", "ALL", 0)] \
                                          + self.results[('COMFwd', fwd_idx, 'ALL', -inst_obj.cmdelta_shift)]) \
                                        / ( inst_obj.cmdelta_shift ** 2)
            elif greek == 'cmdeltas':
                self.calc_risks[greek] = {}
                for fwd_idx in inst_obj.mkt_deps['COMFwd']:
                    self.calc_risks[greek][fwd_idx] = {}
                    for tenor in inst_obj.mkt_deps['COMFwd'][fwd_idx]:
                        self.calc_risks[greek][fwd_idx][tenor] = (self.results[('COMFwd', fwd_idx, tenor, inst_obj.cmdelta_shift)] \
                                          - self.results[('COMFwd', fwd_idx, tenor, - inst_obj.cmdelta_shift)]) / ( \
                                             2.0 * inst_obj.cmdelta_shift )
            elif greek == 'cmgammas':
                self.calc_risks[greek] = {}
                for fwd_idx in inst_obj.mkt_deps['COMFwd']:
                    self.calc_risks[greek][fwd_idx] = {}
                    for tenor in inst_obj.mkt_deps['COMFwd'][fwd_idx]:
                        self.calc_risks[greek][fwd_idx][tenor] = (self.results[('COMFwd', fwd_idx, tenor, inst_obj.cmdelta_shift)] \
                                          - 2 * self.results[("value_date", "value_date", "ALL", 0)] \
                                          + self.results[('COMFwd', fwd_idx, tenor, - inst_obj.cmdelta_shift)]) \
                                          /(inst_obj.cmdelta_shift ** 2)
            elif greek == 'cmvega':
                self.calc_risks[greek] = {}
                for vol_idx in inst_obj.mkt_deps['COMVolATM']:
                    self.calc_risks[greek][vol_idx] = (self.results[('COMVolATM', vol_idx, 'ALL', inst_obj.cmvega_shift)] \
                                                                  - self.results[('COMVolATM', vol_idx, 'ALL', -inst_obj.cmvega_shift)]) \
                                                                 / (2.0 * inst_obj.cmvega_shift * 100.0)
            elif greek == 'cmvegas':
                self.calc_risks[greek] = {}
                for vol_idx in inst_obj.mkt_deps['COMVolATM']:
                    self.calc_risks[greek][vol_idx] = {}
                    for tenor in inst_obj.mkt_deps['COMVolATM'][vol_idx]:
                        self.calc_risks[greek][vol_idx][tenor] = (self.results[('COMVolATM', vol_idx, tenor, inst_obj.cmvega_shift)] \
                                                                  - self.results[('COMVolATM', vol_idx, tenor, -inst_obj.cmvega_shift)]) \
                                                                 / (2.0 * inst_obj.cmvega_shift * 100.0)
            elif greek == 'ycdelta':
                self.calc_risks[greek] = {}
                for fwd_idx in inst_obj.mkt_deps['IRCurve']:
                    self.calc_risks[greek][fwd_idx] = (self.results[('IRYCurve', fwd_idx, 'ALL', inst_obj.ycdelta_shift)] \
                                        - self.results[('IRYCurve', fwd_idx, 'ALL', -inst_obj.ycdelta_shift)]) \
                                        / 2.0 / (inst_obj.ycdelta_shift * 10000)
            elif greek == 'ycgamma':
                self.calc_risks[greek] = {}
                for fwd_idx in inst_obj.mkt_deps['IRCurve']:
                    self.calc_risks[greek][fwd_idx] = (self.results[('IRYCurve', fwd_idx, 'ALL', inst_obj.ycdelta_shift)] \
                                          - 2 * self.results[("value_date", "value_date", "ALL", 0)] \
                                          + self.results[('IRYCurve', fwd_idx, 'ALL', -inst_obj.ycdelta_shift)]) / (
                                         (inst_obj.ycdelta_shift * 10000) ** 2)
            elif greek == 'fxdelta':  ## need to be careful here FX shift is assumed to be ratio multiplier
                self.calc_risks[greek] = {}
                for fwd_idx in inst_obj.mkt_deps['FXFwd']:
                    self.calc_risks[greek][fwd_idx] = (self.results[('FXFwd', fwd_idx, 'ALL', inst_obj.fxdelta_shift)] \
                                        - self.results[('FXFwd', fwd_idx, 'ALL', -inst_obj.fxdelta_shift)]) \
                                        / (2 * inst_obj.fxdelta_shift)
            elif greek == 'fxgamma':
                self.calc_risks[greek] = {}
                for fwd_idx in inst_obj.mkt_deps['FXFwd']:
                    self.calc_risks[greek][fwd_idx] = (self.results[('FXFwd', fwd_idx, 'ALL', inst_obj.fxdelta_shift)] \
                                        - 2*self.results[("value_date", "value_date", "ALL", 0)] \
                                        + self.results[('FXFwd', fwd_idx, 'ALL', -inst_obj.fxdelta_shift)]) \
                                        / (inst_obj.fxdelta_shift ** 2)
            elif greek == 'swnvega':
                self.calc_risks[greek] = {}
                for vol_idx in inst_obj.mkt_deps['IRSWNVol']:
                    self.calc_risks[greek][vol_idx] = (self.results[('IRSWNVol', vol_idx, 'ALL', inst_obj.swnvega_shift)] \
                                        - self.results[('IRSWNVol', vol_idx, 'ALL', -inst_obj.swnvega_shift)]) \
                                        / (2 * inst_obj.swnvega_shift * 100.0)
            elif greek == 'fxvega':
                self.calc_risks[greek] = {}
                for vol_idx in inst_obj.mkt_deps['FXVol']:
                    self.calc_risks[greek][vol_idx] = (self.results[('FXVol', vol_idx, 'ALL', inst_obj.fxvega_shift)] \
                                          - self.results[('FXVOL', vol_idx, 'ALL', -inst_obj.fxvega_shift)]) \
                                        / (2 * inst_obj.fxvega_shift * 100.0)

    def save_results(self, filename = None):
        if filename != None:
            with open(filename, 'w') as outfile:
                json.dump(self.calc_risks, outfile)
                return True
        else:
            return json.dumps(self.calc_risks)

if __name__ == '__main__':
    pass
