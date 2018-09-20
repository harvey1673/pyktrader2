# -*- coding:utf-8 -*-
import copy
import json
import cmq_inst
import cmq_crv_defn
import misc
import workdays

def inst_valuation(val_data):
    inst_data = val_data[0]
    market_data = val_data[1]
    model_settings = {}
    if len(val_data) > 2:
        model_settings = val_data[2]
    inst_type = inst_data["inst_type"]
    cls_name = cmq_inst.inst_type_map[inst_type]
    cls_str = cls_name.split('.')
    inst_cls = getattr(__import__(str(cls_str[0])), str(cls_str[1]))
    inst_obj = inst_cls.create_instrument(inst_data, market_data, model_settings)
    pr = inst_obj.price()
    return pr

def generate_scen(base_market, curve_type, curve_name, curve_tenor = 'ALL', shift_size = 0.0001, shift_type = cmq_inst.CurveShiftType.Abs):
    market_scen = copy.deepcopy(base_market)
    if curve_type == 'value_date':
        if shift_size >= 1:
            market_scen[curve_type] = workdays.workday(market_scen[curve_type], shift_size)
            curr_date = market_scen['market_date']
            prefix_dates = [workdays.workday(curr_date, shift) for shift in range(1, shift_size + 1)]
            for fwd_idx in market_scen['COMFwd']:
                crv_info = cmq_crv_defn.COM_Curve_Map[fwd_idx]
                if (crv_info['exch'] == 'SGX') and ('COMFix' in market_scen) and (crv_info['spotID'] in market_scen['COMFix']):
                    fixes = market_scen['COMFix'][crv_info['spotID']]
                    fwd_quotes = market_scen['COMFwd'][fwd_idx]
                    idy = 0
                    if len(fixes) > 0:
                        for fix_date in prefix_dates:
                            if fix_date <= fixes[-1][0]:
                                continue
                            while fwd_quotes[idy][1] < fix_date:
                                idy += 1
                            fixes.append([fix_date, fwd_quotes[idy][2]])
    elif (curve_type in market_scen) and (curve_name in market_scen[curve_type]):
            for idx, value in enumerate(market_scen[curve_type][curve_name]):
                if curve_tenor == 'ALL' or value[0] == curve_tenor:
                    curve_shift = shift_size
                    if shift_type == cmq_inst.CurveShiftType.Rel:
                        curve_shift *= value[2]
                    market_scen[curve_type][curve_name][idx][2] += curve_shift
    return market_scen

class CMQInstRiskStore(object):
    def __init__(self, inst_obj, base_market, req_greeks, reporting_ccy = 'USD'):
        self.instrument = inst_obj
        self.base_market =base_market
        self.req_greeks = req_greeks
        self.scen_keys = []
        self.results = {}
        self.calc_risks = {}
        self.reporting_ccy = reporting_ccy
        self.fx_rate = {}
        self.map_results = None

    def get_scen_keys(self):
        self.scen_keys = []
        inst_obj = self.instrument
        for greek_str in self.req_greeks:
            greek_keys = greek_str.split('_')
            greek = greek_keys[0]
            scens = []
            if greek == 'pv':
                scens += [("value_date", "value_date", "ALL", 0)]
            elif greek == 'theta':
                theta_shift = 1
                if len(greek_keys) > 1:
                    theta_shift = int(greek_keys[1])
                scens += [("value_date", "value_date", "ALL", 0), ("value_date", "value_date", "ALL", theta_shift)]
            elif greek in ['cmdelta', 'cmgamma']:
                if 'COMFwd' not in inst_obj.mkt_deps:
                    continue
                for fwd_idx in inst_obj.mkt_deps['COMFwd']:
                    scens += [('COMFwd',  fwd_idx, 'ALL', inst_obj.cmdelta_shift), ('COMFwd', fwd_idx, 'ALL', -inst_obj.cmdelta_shift)]
            elif greek == 'cmvega':
                vol_key = 'COMVol'+ greek_keys[1].upper()
                if vol_key not in inst_obj.mkt_deps:
                    continue
                for vol_idx in inst_obj.mkt_deps[vol_key]:
                    scens += [(vol_key, vol_idx, 'ALL', inst_obj.cmvega_shift), (vol_key, vol_idx, 'ALL', -inst_obj.cmvega_shift)]
            elif greek in ['cmdeltas', 'cmgammas']:
                if 'COMFwd' not in inst_obj.mkt_deps:
                    continue
                for fwd_idx in inst_obj.mkt_deps['COMFwd']:
                    for tenor in inst_obj.mkt_deps['COMFwd'][fwd_idx]:
                        scens += [('COMFwd',  fwd_idx, tenor, inst_obj.cmdelta_shift), ('COMFwd', fwd_idx, tenor, -inst_obj.cmdelta_shift)]
            elif greek == 'cmvegas':
                vol_key = 'COMVol' + greek_keys[1].upper()
                if vol_key not in inst_obj.mkt_deps:
                    continue
                for vol_idx in inst_obj.mkt_deps[vol_key]:
                    for tenor in inst_obj.mkt_deps[vol_key][vol_idx]:
                        scens += [(vol_key, vol_idx, tenor, inst_obj.cmvega_shift), (vol_key, vol_idx, tenor, -inst_obj.cmvega_shift)]
            elif greek in ['ycdelta', 'ycgamma']:
                if 'IRCurve' not in inst_obj.mkt_deps:
                    continue
                for fwd_idx in self.instrument.mkt_deps['IRCurve']:
                    scens += [('IRCurve', fwd_idx, 'ALL', inst_obj.ycdelta_shift), ('IRCurve', fwd_idx, 'ALL', -inst_obj.ycdelta_shift)]
            elif greek == 'swnvega':
                if 'IRSWNVol' not in inst_obj.mkt_deps:
                    continue
                for vol_idx in inst_obj.mkt_deps['IRSWNVol']:
                    scens += [('IRSWNVol', vol_idx, 'ALL', inst_obj.swnvega_shift), ('IRSWNVol', vol_idx, 'ALL', -inst_obj.swnvega_shift)]
            elif greek in ['fxdelta', 'fxgamma']:
                if 'FXFwd' not in inst_obj.mkt_deps:
                    continue
                for fwd_idx in inst_obj.mkt_deps['FXFwd']:
                    scens += [('FXFwd', fwd_idx, 'ALL', inst_obj.fxdelta_shift), ('FXFwd', fwd_idx, 'ALL', -inst_obj.fxdelta_shift)]
            elif greek == 'fxvega':
                vol_key = 'FXVol' + greek_keys[1].upper()
                if vol_key not in inst_obj.mkt_deps:
                    continue
                for vol_idx in inst_obj.mkt_deps[vol_key]:
                    scens += [(vol_key, vol_idx, 'ALL', inst_obj.fxvega_shift), (vol_key, vol_idx, 'ALL', -inst_obj.fxvega_shift)]
            elif greek == 'fxvegas':
                vol_key = 'FXVol' + greek_keys[1].upper()
                if vol_key not in inst_obj.mkt_deps:
                    continue
                for vol_idx in inst_obj.mkt_deps[vol_key]:
                    for tenor in inst_obj.mkt_deps[vol_key][vol_idx]:
                        scens += [(vol_key, vol_idx, tenor, inst_obj.fxvega_shift), (vol_key, vol_idx, tenor, -inst_obj.fxvega_shift)]
            if 'gamma' in greek:
                scens += [("value_date", "value_date", "ALL", 0)]
            for scen in scens:
                if scen not in self.scen_keys:
                    self.scen_keys.append(scen)
        return self.scen_keys

    def run_scenarios(self, scenarios = {}, pool = None):
        self.map_result = None
        if pool == None:
            for scen in self.scen_keys:
                self.instrument.set_market_data(scenarios[scen])
                self.results[scen] = self.instrument.price()
                if self.instrument.ccy != self.reporting_ccy:
                    self.fx_rate[scen] = misc.conv_fx_rate(self.instrument.ccy, self.reporting_ccy, scenarios[scen]['FXFwd'])
                else:
                    self.fx_rate[scen] = 1.0
        else:  ## can do parallel computing here
            param_list = [[self.instrument.inst_data, scenarios[scen], self.instrument.model_settings] \
                          for scen in self.scen_keys]
            for scen in self.scen_keys:
                if self.instrument.ccy != self.reporting_ccy:
                    self.fx_rate[scen] = misc.conv_fx_rate(self.instrument.ccy, self.reporting_ccy, scenarios[scen]['FXFwd'])
                else:
                    self.fx_rate[scen] = 1.0
            self.map_result = pool.map_async(inst_valuation, param_list)

    def summarize_risks(self):
        inst_obj = self.instrument
        if self.map_result != None:
            pool_result = self.map_result.get()
            self.results = dict([(scen, val) for scen, val in zip(self.scen_keys, pool_result)])
        if self.instrument.ccy != self.reporting_ccy:
            base_fx = misc.conv_fx_rate(self.instrument.ccy, self.reporting_ccy, self.base_market['FXFwd'])
        else:
            base_fx = 1.0
        for greek_str in self.req_greeks:
            greek_keys = greek_str.split('_')
            greek = greek_keys[0]
            if greek == 'pv':
                self.calc_risks[greek_str] = self.results[("value_date", "value_date", "ALL", 0)]
                self.calc_risks[greek_str] = self.calc_risks[greek_str] * base_fx
            elif greek == 'theta':
                self.calc_risks[greek_str] = self.results[("value_date", "value_date", "ALL", inst_obj.theta_shift)] \
                                         - self.results[("value_date", "value_date", "ALL", 0)]
                self.calc_risks[greek_str] = self.calc_risks[greek_str] * base_fx
            elif greek == 'cmdelta':
                self.calc_risks[greek_str] = {}
                if 'COMFwd' not in inst_obj.mkt_deps:
                    continue
                for fwd_idx in inst_obj.mkt_deps['COMFwd']:
                    self.calc_risks[greek_str][fwd_idx] = (self.results[('COMFwd', fwd_idx, 'ALL', inst_obj.cmdelta_shift)] \
                                          - self.results[('COMFwd', fwd_idx, 'ALL', -inst_obj.cmdelta_shift)]) / ( \
                                             2.0 * inst_obj.cmdelta_shift )
                    crv_data = cmq_crv_defn.COM_Curve_Map[fwd_idx]
                    if crv_data['ccy'] != self.reporting_ccy:
                        shift_rate =  misc.conv_fx_rate(crv_data['ccy'], self.reporting_ccy, self.base_market['FXFwd'])
                    else:
                        shift_rate = 1.0
                    self.calc_risks[greek_str][fwd_idx] = self.calc_risks[greek_str][fwd_idx] * base_fx/shift_rate

            elif greek == 'cmgamma':
                self.calc_risks[greek_str] = {}
                if 'COMFwd' not in inst_obj.mkt_deps:
                    continue
                for fwd_idx in inst_obj.mkt_deps['COMFwd']:
                    self.calc_risks[greek_str][fwd_idx] = (self.results[('COMFwd', fwd_idx, 'ALL', inst_obj.cmdelta_shift)] \
                                          - 2 * self.results[("value_date", "value_date", "ALL", 0)] \
                                          + self.results[('COMFwd', fwd_idx, 'ALL', -inst_obj.cmdelta_shift)]) \
                                        / ( inst_obj.cmdelta_shift ** 2)
                    crv_data = cmq_crv_defn.COM_Curve_Map[fwd_idx]
                    if crv_data['ccy'] != self.reporting_ccy:
                        shift_rate = misc.conv_fx_rate(crv_data['ccy'], self.reporting_ccy, self.base_market['FXFwd'])
                    else:
                        shift_rate = 1.0
                    self.calc_risks[greek_str][fwd_idx] = self.calc_risks[greek_str][fwd_idx] * base_fx/(shift_rate**2)
            elif greek == 'cmdeltas':
                self.calc_risks[greek_str] = {}
                if 'COMFwd' not in inst_obj.mkt_deps:
                    continue
                for fwd_idx in inst_obj.mkt_deps['COMFwd']:
                    self.calc_risks[greek_str][fwd_idx] = {}
                    for tenor in inst_obj.mkt_deps['COMFwd'][fwd_idx]:
                        self.calc_risks[greek_str][fwd_idx][tenor] = (self.results[('COMFwd', fwd_idx, tenor, inst_obj.cmdelta_shift)] \
                                          - self.results[('COMFwd', fwd_idx, tenor, - inst_obj.cmdelta_shift)]) / ( \
                                             2.0 * inst_obj.cmdelta_shift )
                        crv_data = cmq_crv_defn.COM_Curve_Map[fwd_idx]
                        if crv_data['ccy'] != self.reporting_ccy:
                            shift_rate = misc.conv_fx_rate(crv_data['ccy'], self.reporting_ccy,
                                                           self.base_market['FXFwd'])
                        else:
                            shift_rate = 1.0
                            self.calc_risks[greek_str][fwd_idx][tenor] = self.calc_risks[greek_str][fwd_idx][tenor] * base_fx / shift_rate
            elif greek == 'cmgammas':
                self.calc_risks[greek_str] = {}
                if 'COMFwd' not in inst_obj.mkt_deps:
                    continue
                for fwd_idx in inst_obj.mkt_deps['COMFwd']:
                    self.calc_risks[greek_str][fwd_idx] = {}
                    for tenor in inst_obj.mkt_deps['COMFwd'][fwd_idx]:
                        self.calc_risks[greek_str][fwd_idx][tenor] = (self.results[('COMFwd', fwd_idx, tenor, inst_obj.cmdelta_shift)] \
                                          - 2 * self.results[("value_date", "value_date", "ALL", 0)] \
                                          + self.results[('COMFwd', fwd_idx, tenor, - inst_obj.cmdelta_shift)]) \
                                          /(inst_obj.cmdelta_shift ** 2)
                        crv_data = cmq_crv_defn.COM_Curve_Map[fwd_idx]
                        if crv_data['ccy'] != self.reporting_ccy:
                            shift_rate = misc.conv_fx_rate(crv_data['ccy'], self.reporting_ccy, self.base_market['FXFwd'])
                        else:
                            shift_rate = 1.0
                            self.calc_risks[greek_str][fwd_idx][tenor] = self.calc_risks[greek_str][fwd_idx][tenor] \
                                                                         * base_fx / (shift_rate ** 2)
            elif greek == 'cmvega':
                vol_key = 'COMVol' + greek_keys[1].upper()
                self.calc_risks[greek_str] = {}
                if vol_key not in inst_obj.mkt_deps:
                    continue
                for vol_idx in inst_obj.mkt_deps[vol_key]:
                    self.calc_risks[greek_str][vol_idx] = (self.results[(vol_key, vol_idx, 'ALL', inst_obj.cmvega_shift)] \
                                                                  - self.results[(vol_key, vol_idx, 'ALL', -inst_obj.cmvega_shift)]) \
                                                                 / (2.0 * inst_obj.cmvega_shift * 100.0)
                    self.calc_risks[greek_str][vol_idx] = self.calc_risks[greek_str][vol_idx] * base_fx
            elif greek == 'cmvegas':
                vol_key = 'COMVol' + greek_keys[1].upper()
                self.calc_risks[greek_str] = {}
                if vol_key not in inst_obj.mkt_deps:
                    continue
                for vol_idx in inst_obj.mkt_deps[vol_key]:
                    self.calc_risks[greek_str][vol_idx] = {}
                    for tenor in inst_obj.mkt_deps[vol_key][vol_idx]:
                        self.calc_risks[greek_str][vol_idx][tenor] = (self.results[(vol_key, vol_idx, tenor, inst_obj.cmvega_shift)] \
                                                                  - self.results[(vol_key, vol_idx, tenor, -inst_obj.cmvega_shift)]) \
                                                                 / (2.0 * inst_obj.cmvega_shift * 100.0)
                        self.calc_risks[greek_str][vol_idx][tenor] = self.calc_risks[greek_str][vol_idx][tenor] * base_fx
            elif greek == 'ycdelta':
                self.calc_risks[greek_str] = {}
                if 'IRCurve' not in inst_obj.mkt_deps:
                    continue
                for fwd_idx in inst_obj.mkt_deps['IRCurve']:
                    self.calc_risks[greek_str][fwd_idx] = (self.results[('IRYCurve', fwd_idx, 'ALL', inst_obj.ycdelta_shift)] \
                                        - self.results[('IRYCurve', fwd_idx, 'ALL', -inst_obj.ycdelta_shift)]) \
                                        / 2.0 / (inst_obj.ycdelta_shift * 10000)
                    self.calc_risks[greek_str][fwd_idx] = self.calc_risks[greek_str][fwd_idx] * base_fx
            elif greek == 'ycgamma':
                self.calc_risks[greek_str] = {}
                if 'IRCurve' not in inst_obj.mkt_deps:
                    continue
                for fwd_idx in inst_obj.mkt_deps['IRCurve']:
                    self.calc_risks[greek_str][fwd_idx] = (self.results[('IRYCurve', fwd_idx, 'ALL', inst_obj.ycdelta_shift)] \
                                          - 2 * self.results[("value_date", "value_date", "ALL", 0)] \
                                          + self.results[('IRYCurve', fwd_idx, 'ALL', -inst_obj.ycdelta_shift)]) / (
                                         (inst_obj.ycdelta_shift * 10000) ** 2)
                    self.calc_risks[greek_str][fwd_idx] = self.calc_risks[greek_str][fwd_idx] * base_fx
            elif greek == 'fxdelta':  ## need to be careful here FX shift is assumed to be ratio multiplier
                self.calc_risks[greek_str] = {}
                if 'FXFwd' not in inst_obj.mkt_deps:
                    continue
                for fwd_idx in inst_obj.mkt_deps['FXFwd']:
                    self.calc_risks[greek_str][fwd_idx] = (self.results[('FXFwd', fwd_idx, 'ALL', inst_obj.fxdelta_shift)] \
                                        * self.fx_rate[('FXFwd', fwd_idx, 'ALL', inst_obj.fxdelta_shift)] \
                                        - self.results[('FXFwd', fwd_idx, 'ALL', -inst_obj.fxdelta_shift)] \
                                        * self.fx_rate[('FXFwd', fwd_idx, 'ALL', -inst_obj.fxdelta_shift)]) \
                                        / (2 * inst_obj.fxdelta_shift)
            elif greek == 'fxgamma':
                self.calc_risks[greek_str] = {}
                if 'FXFwd' not in inst_obj.mkt_deps:
                    continue
                for fwd_idx in inst_obj.mkt_deps['FXFwd']:
                    self.calc_risks[greek_str][fwd_idx] = (self.results[('FXFwd', fwd_idx, 'ALL', inst_obj.fxdelta_shift)] \
                                        * self.fx_rate[('FXFwd', fwd_idx, 'ALL', inst_obj.fxdelta_shift)] \
                                        - 2*self.results[("value_date", "value_date", "ALL", 0)] * base_fx \
                                        + self.results[('FXFwd', fwd_idx, 'ALL', -inst_obj.fxdelta_shift)] \
                                        * self.fx_rate[('FXFwd', fwd_idx, 'ALL', -inst_obj.fxdelta_shift)]) \
                                        / (inst_obj.fxdelta_shift ** 2)
            elif greek == 'swnvega':
                self.calc_risks[greek_str] = {}
                if 'IRSWNVol' not in inst_obj.mkt_deps:
                    continue
                for vol_idx in inst_obj.mkt_deps['IRSWNVol']:
                    self.calc_risks[greek_str][vol_idx] = (self.results[('IRSWNVol', vol_idx, 'ALL', inst_obj.swnvega_shift)] \
                                        - self.results[('IRSWNVol', vol_idx, 'ALL', -inst_obj.swnvega_shift)]) \
                                        / (2 * inst_obj.swnvega_shift * 100.0)
                    self.calc_risks[greek_str][vol_idx] = self.calc_risks[greek_str][vol_idx] * base_fx
            elif greek == 'fxvega':
                vol_key = 'FXVol' + greek_keys[1].upper()
                self.calc_risks[greek_str] = {}
                if vol_key not in inst_obj.mkt_deps:
                    continue
                for vol_idx in inst_obj.mkt_deps[vol_key]:
                    self.calc_risks[greek_str][vol_idx] = (self.results[(vol_key, vol_idx, 'ALL', inst_obj.fxvega_shift)] \
                                          - self.results[(vol_key, vol_idx, 'ALL', -inst_obj.fxvega_shift)]) \
                                        / (2 * inst_obj.fxvega_shift * 100.0)
                    self.calc_risks[greek_str][vol_idx] = self.calc_risks[greek_str][vol_idx] * base_fx
            elif greek == 'fxvegas':
                vol_key = 'FXVol' + greek_keys[1].upper()
                self.calc_risks[greek_str] = {}
                if vol_key not in inst_obj.mkt_deps:
                    continue
                for vol_idx in inst_obj.mkt_deps[vol_key]:
                    self.calc_risks[greek_str][vol_idx] = {}
                    for tenor in inst_obj.mkt_deps[vol_key][vol_idx]:
                        self.calc_risks[greek_str][vol_idx] = (self.results[(vol_key, vol_idx, tenor, inst_obj.fxvega_shift)] \
                                          - self.results[(vol_key, vol_idx, tenor, -inst_obj.fxvega_shift)]) \
                                        / (2 * inst_obj.fxvega_shift * 100.0)
                        self.calc_risks[greek_str][vol_idx] = self.calc_risks[greek_str][vol_idx] * base_fx

    def run_risk(self, scenarios = {}):
        self.run_scenarios(scenarios)
        self.summarize_risks()

    def save_results(self, filename = None):
        if filename != None:
            with open(filename, 'w') as outfile:
                json.dump(self.calc_risks, outfile)
                return True
        else:
            return json.dumps(self.calc_risks)

if __name__ == '__main__':
    pass