#-*- coding:utf-8 -*-
import instrument
import pyktlib
import os
import csv
import numpy as np
import data_handler as dh
import datetime
from agent import *
from misc import *

def min2time(min_id):
    return int((min_id/100-6)%24)/24.0 + (min_id % 100)/1440.0

def discount(irate, dtoday, dexp):
    return np.exp(-irate * max(dexp - dtoday,0)/365.0)
                
class OptAgentMixin(object):
    def __init__(self, name, tday=datetime.date.today(), config = {}):
        self.volgrids = {}
        self.dtoday = date2xl(tday)
        self.irate = config.get('irate', {'CNY': 0.02, 'USD': 0.00})
        self.option_insts = [inst for inst in self.instruments.values() if inst.ptype == instrument.ProductType.Option]

    def create_volgrids(self):
        volgrids = {}
        for inst in self.option_insts:
            is_spot = False
            accr = 'COM'
            prod = inst.product
            expiry = inst.expiry
            if 'Stock' in inst.__class__.__name__:
                is_spot = True
                accr = 'SSE'
            else:
                if inst.exchange == 'CFFEX':
                    accr = 'CFFEX'
                elif inst.product in night_session_markets and night_session_markets[inst.product] == 4:
                    accr = 'COMN1'
            if prod not in volgrids:
                volgrids[prod] = instrument.VolGrid(prod, accrual= accr, is_spot = is_spot, ccy = 'CNY')
            if expiry not in volgrids[prod].option_insts:
                volgrids[prod].option_insts[expiry] = []
                volgrids[prod].underlier[expiry] = inst.underlying
                volgrids[prod].volparam[expiry] = [0.2, 0.0, 0.0, 0.0, 0.0]
            volgrids[prod].option_insts[expiry].append(inst.name)
        self.volgrids = volgrids

    def load_volgrids(self):
        self.logger.info('loading volgrids')
        for prod in self.volgrids.keys():
            logfile = self.folder + 'volgrids_' + prod + '.csv'
            if os.path.isfile(logfile):       
                with open(logfile, 'rb') as f:
                    reader = csv.reader(f)
                    for row in enumerate(reader):
                        inst = row[0]
                        expiry = datetime.datetime.strptime(row[1], '%Y%m%d %H%M%S')
                        fwd = float(row[2]) 
                        atm = float(row[3])
                        v90 = float(row[4])
                        v75 = float(row[5])
                        v25 = float(row[6])
                        v10 = float(row[7])
                        last_update = float(row[8])
                        if len(row) > 9:
                            mark_date = datetime.date.strptime(row[9], '%Y%m%d')
                            if self.scur_day > mark_date:
                                last_update = 0
                        dexp = datetime2xl(expiry)
                        vg = self.volgrids[prod]
                        vg.underlier[expiry] = inst
                        vg.df[expiry] = discount(self.irate[ccy], self.dtoday, dexp)
                        vg.fwd[expiry] = fwd
                        vg.volparam[expiry] = [atm, v90, v75, v25, v10]
                        vg.volnode[expiry] = pyktlib.Delta5VolNode(self.dtoday, dexp, fwd, atm, v90, v75, v25, v10, self.volgrids[prod].accrual)
                        vg.t2expiry[expiry] = vg.volnode[expiry].expiry_()
                        vg.last_update[expiry] = last_update
            else:
                for expiry in self.volgrids[prod].option_insts:
                    dexp = datetime2xl(expiry)
                    vg = self.volgrids[prod]
                    under_instID =vg.underlier[expiry]
                    fwd = self.instruments[under_instID].price
                    ccy = self.instruments[under_instID].ccy
                    if vg.spot_model:
                        fwd = fwd / vg.df[expiry]
                    vg.fwd[expiry] = fwd
                    vg.df[expiry] = discount(self.irate[ccy], self.dtoday, dexp)
                    atm = vg.volparam[expiry][0]
                    v90 = vg.volparam[expiry][1]
                    v75 = vg.volparam[expiry][2]
                    v25 = vg.volparam[expiry][3]
                    v10 = vg.volparam[expiry][4]
                    vg.volnode[expiry] = pyktlib.Delta5VolNode(self.dtoday, dexp, fwd, atm, v90, v75, v25, v10, self.volgrids[prod].accrual)
                    vg.t2expiry[expiry] = vg.volnode[expiry].expiry_()
                    vg.last_update[expiry] = 0

    def save_volgrids(self):
        self.logger.info('saving volgrids')
        for prod in self.volgrids.keys():
            logfile = self.folder + 'volgrids_' + prod + '.csv'
            with open(logfile,'wb') as log_file:
                file_writer = csv.writer(log_file, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
                vg = self.volgrids[prod]
                for expiry in vg.volparam:
                    if len(vg.volparam[expiry]) == 5:
                        volparam = vg.volparam[expiry]
                        row = [ vg.underlier[expiry], expiry.strftime('%Y%m%d %H%M%S'), vg.fwd[expiry] ] \
                              + volparam + [vg.last_update[expiry], self.scur_day.strftime('%Y%m%d')]
                        file_writer.writerow(row)
    
    def set_opt_pricers(self):
        for instID in self.instruments:
            inst = self.instruments[instID]
            if inst.ptype == instrument.ProductType.Option:
                expiry = inst.expiry
                prod = inst.product
                if expiry in self.volgrids[prod].volnode:
                    inst.set_pricer(self.volgrids[prod], self.irate[inst.ccy])
                    inst.update_greeks(['pv', 'delta', 'gamma', 'vega', 'theta'])
                else:
                    self.logger.warning("missing %s volgrid for %s" % (prod, expiry))

    def intraday_fraction(self, vn, tick_id):
        return vn.getDayFraction_(min2time(tick_id / 1000)) + (tick_id % 1000) / 864000.0

    def set_volgrids(self, product, expiry, fwd, vol_param, tick_id):
        if (expiry in self.volgrids[product].volparam):
            vg = self.volgrids[product]
            vn = vg.volnode[expiry]
            day_fraction = self.intraday_fraction(vn, tick_id)
            t2expiry = max(vg.t2expiry[expiry] - day_fraction, 0)/BDAYS_PER_YEAR
            vg.fwd[expiry] = fwd
            vg.volparam[expiry] = vol_param
            vn.setFwd(fwd)
            vn.setTime2Exp(t2expiry)
            vn.setAtm(vol_param[0])
            vn.setD90Vol(vol_param[1])
            vn.setD75Vol(vol_param[2])
            vn.setD25Vol(vol_param[3])
            vn.setD10Vol(vol_param[4])
            vn.initialize()
            vg.last_update[expiry] = day_fraction
        else:
            self.logger.info('expiry %s is not in the volgrid expiry for %s' % (expiry, product))
    
    def calc_volgrid(self, product, expiry, update_risk=True):
        vg = self.volgrids[product]
        under = vg.underlier[expiry]
        fwd = self.instruments[under].mid_price
        if vg.spot_model:
            fwd = fwd/vg.df[expiry]
        vol_param = vg.volparam[expiry]
        vn = vg.volnode[expiry]
        self.set_volgrids(product, expiry, fwd, vol_param, self.tick_id)
        for instID in vg.option_insts[expiry]:
            inst = self.instruments[instID]
            optpricer = inst.pricer                                        
            optpricer.setFwd(fwd)
            optpricer.setT2Exp(vn.expiry_())
            if update_risk:
                inst.update_greeks(vg.last_update[expiry], greeks = ['pv', 'delta', 'gamma', 'vega'])

    def fit_volgrid(self, product, expiry, fwd, strike_list, vol_list, tick_id):
        vg = self.volgrids[product]
        vn = vg.volnode[expiry]
        day_fraction = self.intraday_fraction(vn, tick_id)
        t2expiry = max(vg.t2expiry[expiry] - day_fraction, 0)/BDAYS_PER_YEAR
        stkList = pyktlib.DblVector(strike_list)
        volList = pyktlib.DblVector(vol_list)
        volparam = pyktlib.FitDelta5VolParams(t2expiry, fwd, stkList, volList)
        atm = volparam[0]
        v90 = volparam[1]
        v75 = volparam[2]
        v25 = volparam[3]
        v10 = volparam[4]
        return [atm, v90, v75, v25, v10]
      
class OptionAgent(Agent, OptAgentMixin):
    def __init__(self, name, tday=datetime.date.today(), config = {}):
        Agent.__init__(self, name, tday, config)
        OptAgentMixin.__init__(self, name, tday, config)
        self.create_volgrids()
        self.load_volgrids()
        self.set_opt_pricers()
    
    def restart(self):
        for prod in self.volgrids:
            for expiry in self.volgrids[prod]:
                self.calc_volgrid(prod, expiry, update_risk = True)
        Agent.restart(self)
