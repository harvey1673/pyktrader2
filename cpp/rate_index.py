#-*- coding:utf-8 -*-
from abc import ABC, abstractclassmethod
from functools import lru_cache
from misc import *
from utilities import *    
from curve import Curve
import numpy as np   
from scipy.stats import norm 
from scipy.optimize import brentq as solver
import copy

class IndexFactory(ABC): 
    def __init__(self): 
        self.fixing_pool = {}

    def set_fixing(self, date, rate):
        if isinstance(date, Date):
            self.fixing_pool[date] = rate
        else:
            self.fixing_pool[Date(date)] = rate

    def get_fixing(self, date):
        try:
            return self.fixing_pool[date]
        except:
            return None

    def remove_fixing(self, date):
        self.fixing_pool.pop(date)

    @abstractclassmethod
    def create(self, period):
        pass

    class Index(ABC):
        def __init__(self, fixing):      
            self.fixing = fixing

        @abstractclassmethod
        def forward(self, proj):
            pass 

        @print_self(4, 8)
        def __repr__(self):
            pass


class FixedIndexFactory(IndexFactory): # Simply follows accrual schedule
    def __init__(self, fixrate=0.0):
        super().__init__()
        self.fixrate = fixrate

    def create(self, period):
        fixing = self.get_fixing(period.fixdate) # for predefined stepping fixed rates
        if fixing is None:
            fixing = self.fixrate
        return self.Index(fixing)

    class Index(IndexFactory.Index):
        def forward(self, proj): # proj is a dummy for fixed rate index
            return self.fixing # fixed rate 


class FloatIndexFactory(IndexFactory):
    def create(self, period): # simply follows payment schedule
        fixing = self.get_fixing(period.fixdate)
        return self.Index(fixing, period.fixdate, period.accr_start, period.accr_end, period.accr_cov) 
    
    class Index(IndexFactory.Index):
        def __init__(self, fixing, fixdate, effdate, matdate, coverage): 
            super().__init__(fixing)       
            self.fixdate = fixdate
            self.effdate = effdate
            self.matdate = matdate
            self.coverage = coverage 

        def forward(self, proj):
            if self.fixing is not None:
                return self.fixing
            elif self.effdate.t >= proj.t0:
                return (proj(self.effdate.t) / proj(self.matdate.t) - 1) / self.coverage 
            else:
                raise BaseException('missing fixing on %s ...' % self.fixdate)  


class LiborIndexFactory(FloatIndexFactory):
    def __init__(self, tenor, calendar, daycount, *, spotlag='2D', dayroll=DayRoll.ModifiedFollowing, endmonth=True): 
        super().__init__()
        self.tenor = Period(tenor)
        self.daycount = daycount
        spotlag = Period(spotlag) 
        def roll_date(startdate, period):
            if isinstance(period, ql.Period):
                date = calendar.advance(startdate, period, dayroll, endmonth)
            elif period == 'spot':
                date = calendar.advance(startdate, spotlag, dayroll)
            elif period == '-spot':
                date = calendar.advance(startdate, -spotlag, dayroll)
            return Date.convert(date) 
        self.roll_date = roll_date 

    def create(self, period=None, fixdate=None):
        if period is not None:
            fixdate = period.fixdate        
        fixing = self.get_fixing(fixdate)
        effdate = self.roll_date(fixdate,  'spot')       
        matdate = self.roll_date(effdate, self.tenor) # normally matdate = paydate for ibor
        coverage = self.daycount.yearFraction(effdate, matdate) 
        return self.Index(fixing, fixdate, effdate, matdate, coverage)


class RangeIndexFactory(FloatIndexFactory): ##### need extra work for aged deal...
    def __init__(self, *,       
                 hw=None, 
                 baserate=None,
                 index_fac=None,       # range leg rate index factory, e.g. Libor3M
                 rng_def=None,       # defines the rate range for range swap, e.g. ('outside',0.01,0.02)
                 num_days='calendar', # count of days in a period, e.g. 'calendar' for calendar days, 'business' for business days
                 two_ends=(None,None),# defines the dates in a period to calculate the range theta, e.g. slice(1,-1) excludes start and end dates
                 lockout=('skipped',None), # lock-out period, e.g. ('crystallized', -5) or ('skipped', -3)
                 digi_gap=1e-5,     # strike gap of digital spread, e.g. 1bp    
                 **kwargs):
        super().__init__(**kwargs)
        self.baserate = baserate
        self.hw = hw
        assert isinstance(index_fac, LiborIndexFactory)  
        self.index_fac = index_fac
        if len(rng_def) == 2:
            self.rng_type, self.rng_rate = rng_def          
        else:
            self.rng_type, self.rng_low, self.rng_high = rng_def
        self.num_days = num_days
        self.two_ends = slice(*two_ends)
        self.lk_type, self.lk_days = lockout
        self.digi_gap = digi_gap

    def __range_libors(self, effdate, matdate):
        dates = [effdate + i for i in range(matdate - effdate + 1)] # all calendar days
        if self.num_days == 'business': # for business days
            dates = [day for day in dates if self.index_fac.calendar.isBusinessDay(day)]
        dates = dates[self.two_ends] # include or exclude the end dates of a period 
        libors = tuple(self.index_fac.create(fixdate=date) for date in dates)
        if PRINT and self.lk_days is not None: 
            print("    lockout %s --> [%s, %s]" % (dates[self.lk_days], dates[self.lk_days + 1], dates[-1]))
        return libors

    @lru_cache(maxsize=None)#@cache_function(1)
    def __parse_libors(self, libors): # paytime is dummy argument for hashing
        ts = HashableArray([l.effdate.t for l in libors])
        te = HashableArray([l.matdate.t for l in libors])
        cov = np.array([l.coverage for l in libors])                 
        return ts, te, cov   

    @lru_cache(maxsize=None)
    def __xi(self, t0, ts, te): # paytime is dummy argument for hashing; = xi2(t0,ts,ts,te), and xi2(t0,ts,ts,ts) = 0; avoid zero
        return np.array([self.hw.vol.xi2(t0,a,a,b) ** 0.5 for a, b in zip(ts, te)]) + 1e-20 # avoid zero 

    def theta_fn(self, proj, libors, paydate): # theta of one coupon period      
        ts, te, cov = self.__parse_libors(libors)
        eta = (te - paydate.t) / (te - ts) 
        p = 1.0 + np.array([l.forward(proj) for l in libors]) * cov #p = proj(ts) / proj(te) # = (1 + libor * cov)
        xi = self.__xi(proj.t0, ts, te) # proj.t0 is spotdate of curve
        def capfloor(k, s): # forward/undiscounted caplet(s=1)/floorlet(s=-1) price
            zstar = np.log((1 + k) / p) / xi - xi / 2
            return s * (p * norm.cdf(-zstar * s) - (1 + k) * norm.cdf(-(zstar + xi) * s))  
        def digital(k, s): # s=1 ==> 1 for above k; s=-1 ==> 1 for below k
            km = cov * (k - self.digi_gap * s)
            kp = cov * (k + self.digi_gap * s) 
            return (1 + eta * kp) * capfloor(km,s) - (1 + eta * km) * capfloor(kp,s)

        denom = 2 * self.digi_gap * cov #* (1 + eta * (p - 1)) # p - 1 = libor * cov
        if self.rng_type == 'between': # inside; == (digital(rng_high,-1) - digital(rng_low,-1)) / denom            
            ratio = (digital(self.rng_low,1) - digital(self.rng_high,1)) / denom
        elif self.rng_type == 'outside': # outside
            ratio = (digital(self.rng_low,-1) + digital(self.rng_high,1)) / denom
        elif self.rng_type == 'above': # above rate
            ratio = digital(self.rng_rate,1) / denom
        elif self.rng_type == 'below': # below rate
            ratio = digital(self.rng_rate,-1) / denom
            
        if self.lk_type == 'skipped':
            ratio = ratio[:self.lk_days]
        elif self.lk_type == 'crystallized':
            ratio[self.lk_days:] = ratio[self.lk_days] 
        return np.mean(ratio) 

    def create(self, period): # accrual startdate and enddate
        libors = self.__range_libors(period.accr_start, period.accr_end)        
        return self.Index(self.baserate, self.theta_fn, libors, period.paydate)

    class Index(IndexFactory.Index):
        def __init__(self, baserate, theta_fn, libors, paydate):
            self.baserate = baserate 
            self.theta_fn = theta_fn
            self.libors = libors
            self.paydate = paydate 

        def forward(self, proj):
            return self.baserate * self.theta_fn(proj, self.libors, self.paydate)

if __name__ == '__main__':
    pass


