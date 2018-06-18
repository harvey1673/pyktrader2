# -*- coding:utf-8 -*-
import misc
import cmq_inst_risk
import json

class CMQRiskEngine(object):
    def __init__(self, book_obj, base_market, req_greeks, pool = None):
        self.book = book_obj
        self.base_market = base_market
        self.req_greeks = req_greeks
        self.scen_keys = []
        self.scenarios = {}
        self.risk_store = {}
        self.inst_risks = {}
        self.deal_risks = {}
        self.book_risks = {}
        self.update_risk_store()
        self.pool = pool

    def update_risk_store(self):
        self.scen_keys = []
        for inst in self.book.inst_dict:
            self.risk_store[inst] = cmq_inst_risk.CMQInstRiskStore(inst, self.base_market, self.req_greeks, self.book.reporting_ccy)
            self.risk_store[inst].get_scen_keys()
            for scen in self.risk_store[inst].scen_keys:
                if scen not in self.scen_keys:
                    self.scen_keys.append(scen)
                    self.scenarios[scen] = cmq_inst_risk.generate_scen(self.base_market, \
                                                                       scen[0], scen[1], scen[2], scen[3])

    def run_risk(self):
        self.run_scenarios()
        self.summerize_risks()

    def run_scenarios(self):
        if self.pool != None:
            for inst in self.book.inst_dict:
                self.risk_store[inst].run_scenarios(self.scenarios, self.pool)
        else:
            for inst in self.book.inst_dict:
                self.risk_store[inst].run_scenarios(self.scenarios)

    def summerize_risks(self):
        for inst in self.book.inst_dict:
            self.risk_store[inst].summarize_risks()
            self.inst_risks[inst.id] = self.risk_store[inst].calc_risks
        for deal in self.book.deal_list:
            self.deal_risks[deal.id] = {}
            for inst, pos in deal.positions:
                for greek in self.req_greeks:
                    if isinstance(self.inst_risks[inst.id][greek], dict):
                        if greek not in self.deal_risks[deal.id]:
                            self.deal_risks[deal.id][greek] = {}
                        misc.merge_dict(self.inst_risks[inst.id][greek], self.deal_risks[deal.id][greek], pos, 1)
                    else:
                        if greek not in self.deal_risks[deal.id]:
                            self.deal_risks[deal.id][greek] = 0
                        self.deal_risks[deal.id][greek] += self.inst_risks[inst.id][greek] * pos
            misc.merge_dict(self.deal_risks[deal.id], self.book_risks, 1, 1)

    def ccy_converter(self, fx, greek):
        if ('cmdelta' in greek):
            factor = 1.0
        elif greek in ['cmgamma', 'cmgammas']:
            factor = 1.0 / fx
        elif greek == 'fxdelta':
            factor = 1.0
        elif greek in ['fxgamma', 'fxgammas']:
            factor = 1.0
        else:
            factor = fx
        return factor

    def save_results(self, filename = None):
        output = {'book_risks': self.book_risks, 'deal_risks': self.deal_risks, 'inst_risks': self.inst_risks}
        if filename != None:
            with open(filename, 'w') as outfile:
                json.dump(output, outfile)
                return True
        else:
            return json.dumps(output)

if __name__ == '__main__':
    pass