#-*- coding:utf-8 -*-
from math import exp, log
from QuantLib import Option
from cmq_utils import *
import pandas as pd 
from scipy.stats import norm 
from scipy.interpolate import interp1d, interp2d
from scipy.optimize import brentq as solver
from bisect import bisect_left

class BlackModel(object):
    def __init__(self, forward, vol, term, discount):
        self.forward = forward
        self.sqr_term = term ** 0.5
        self.stdev = vol * term ** 0.5
        self.discount = discount

    def callvalue_to_vol(self, value, strike=None):
        if strike is None: 
            strike = self.forward
        def find_vol(vol):
            self.stdev = vol * self.sqr_term
            return self.value(strike=strike) - value      
        return solver(find_vol, 1e-10, 1e2)

    @classmethod
    def value(self, opt, strike):
        pass

    @classmethod
    def vega(self, strike):
        pass


class BlackLognormalModel(BlackModel):
    def value(self, opt=Option.Call, strike=None):
        if strike is None: 
            strike = self.forward
        d1 = self.__d1(strike)
        asset_value = opt * self.forward * norm.cdf(opt * d1)
        cash_value = opt * strike * norm.cdf(opt * (d1 - self.stdev))
        return  self.discount * (asset_value - cash_value)
    
    def vega(self, strike=None):
        if strike is None: 
            strike = self.forward
        d1 = self.__d1(strike)
        return self.discount * self.forward * norm.pdf(d1) * self.sqr_term
    
    def __d1(self, strike):
        if self.forward <= 0: return -1e10 # partially handles negative rates
        return log(self.forward / strike) / self.stdev + 0.5 * self.stdev 


class BlackNormalModel(BlackModel):
    def value(self, opt=Option.Call, strike=None):
        if strike is None: 
            strike = self.forward
        dr = opt * (self.forward - strike)
        d1 = dr / self.stdev  
        d2 = self.stdev * norm.pdf(d1)
        return  self.discount * (dr * norm.cdf(d1) + d2)
    
    def vega(self, strike=None):
        if strike is None: 
            strike = self.forward
        return self.discount * self.sqr_term * norm.pdf((self.forward - strike) / self.stdev)
      

class CapletVolSurface:
    def __init__(self, today, proj, disc, factory, vols, mode):
        self.proj = proj
        self.disc = disc
        self.factory = factory
        self.today = today
        self.spotdate = factory.roll_date(today, 'spot') # also for marking startdate of hw vol term structure         
        self.surface = interp2d(vols.columns, vols.index, vols.values, kind='linear')
        self.mode = 'capfloor'    
        
        class Caplet(BlackLognormalModel if mode == 'lognormal' else BlackNormalModel):
            def __init__(self, libor, forward, blackvol, opt_term, annuity):
                self.underlier = libor 
                super(Caplet, self).__init__(forward, blackvol, opt_term, annuity)
        self.Caplet = Caplet                    

    def get_caplet(self, fixdate, strike=None):
        libor = self.factory.create(fixdate=fixdate) 
        forward = libor.forward(self.proj) 
        opt_term = libor.fixdate.t - self.today.t
        annuity = self.disc(libor.matdate.t) * libor.coverage           
        blackvol = self.surface(forward if strike is None else strike, fixdate.t).item() / 100
        return self.Caplet(libor, forward, blackvol, opt_term, annuity)    
    
    def get_calibration_instruments(self, tradedate, tenor, lastdate):
        # tradedate=None, lastdate=None are dummy arguments for now 
        def expiry_date(period): # this should be the correct way to derive caplet start date
            startdate = self.factory.roll_date(self.spotdate, period)
            return self.factory.roll_date(startdate, '-spot') # rate fixdate

        unit = Period('3M')
        fixdates = (expiry_date(unit * i) for i in range(1, 50) if unit * (i - 1) < tenor) # generator 
        #fixdates = [Date(14,7,2017),Date(13,7,2018),Date(15,7,2019),Date(16,7,2020),Date(15,7,2021)]            
        return [self.get_caplet(date) for date in fixdates]

    @classmethod
    def load(cls, today, proj, disc, factory, mode, filename, sheetname):
        vols = pd.read_excel(filename, sheetname)
        vols.columns = [strike / 100.0 for strike in vols.columns]  
        vols.index = [Date(d.day, d.month, d.year).t - today.t for d in vols.index]   
        return cls(today, proj, disc, factory, vols, mode)


class SwaptionVolSurface:
    def __init__(self, today, proj, disc, factory, vols, mode):
        self.proj = proj
        self.disc = disc
        self.factory = factory
        self.roll_date = factory.rleg_fac.roll_date
        self.today = today
        self.spotdate = self.roll_date(today, 'spot') # for marking startdate of hw vol term structure
        self.opt_tenors = vols.columns # vols.columns = option_tenors
        self.swap_tenors = vols.index  # vols.index = swap_tenors
        self.surface = [self.__process_vol_slice(vols[p]) for p in vols.columns]
        self.mode = 'swaption'

        class Swaption(BlackLognormalModel if mode == 'lognormal' else BlackNormalModel):
            def __init__(self, swap, forward, blackvol, opt_term, annuity):
                self.underlier = swap 
                super(Swaption, self).__init__(forward, blackvol, opt_term, annuity)
        self.Swaption = Swaption   

    def __process_vol_slice(self, vol_slice):
        #underlying swap: startdate = tradedate (+) expiry (+) spotlag,  enddate = startdate (+) tenor
        opt_tenor = vol_slice.name
        opt_term = self.roll_date(self.today, opt_tenor).t - self.today.t
        fixdate = self.roll_date(self.today, opt_tenor)
        startdate = self.roll_date(fixdate, 'spot')
        @np.vectorize 
        def swap_term(swap_tenor):             
            return self.roll_date(startdate, swap_tenor).t - startdate.t
        return opt_term, LinearFlat(swap_term(self.swap_tenors), vol_slice.values / 100)

    def get_swaption(self, swap): # assume no vol smile
        forward = swap.pleg_parrate(self.proj, self.disc) 
        annuity = swap.pleg.get_annuity(self.disc)
        opt_term = swap.fixdate.t - self.today.t 
        swap_term = swap.matdate.t - swap.effdate.t
        x, y = zip(*[(t, vol(swap_term)) for t, vol in self.surface]) 
        blackvol = LinearFlat(x, y)(opt_term)
        return self.Swaption(swap, forward, blackvol, opt_term, annuity) 

    def get_calibration_instruments(self, tradedate, tenor, lastdate):
        swap = self.factory.create(tradedate=tradedate, tenor=tenor)
        def start_date(period):
            expiry_date = self.roll_date(self.today, period)
            return self.roll_date(expiry_date, 'spot')  

        startdates = [start_date(p) for p in self.opt_tenors if start_date(p) < lastdate] + [lastdate] 
        return [self.get_swaption(swap.subswap(start, cutoff='present')) for start in startdates] 

    @classmethod
    def load(cls, today, proj, disc, factory, mode, filename, sheetname):
        vols = pd.read_excel(filename, sheetname)
        vols.columns = [Period(expiry) for expiry in vols.columns]  # vols.columns = option_tenors
        vols.index = [Period(tenor) for tenor in vols.index] # vols.index = swap_tenors
        return cls(today, proj, disc, factory, vols, mode)


if __name__ == '__main__': 
    pass

