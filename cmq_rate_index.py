#-*- coding:utf-8 -*-
from abc import abstractmethod
from repoze.lru import lru_cache
from cmq_curve import DiscountCurve
from cmq_utils import *
from cmq_rate_option import BlackLognormalModel
import numpy as np
from scipy.stats import norm 
from scipy.optimize import brentq as solver
import copy

class IndexFactory(object):
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

    @abstractmethod
    def create(self, period):
        pass

    class Index(object):
        def __init__(self, fixing):      
            self.fixing = fixing

        @abstractmethod
        def forward(self, proj):
            pass 

        @print_self(4, 8)
        def __repr__(self):
            pass


class FixedIndexFactory(IndexFactory): # Simply follows accrual schedule
    def __init__(self, fixrate=0.0):
        super(FixedIndexFactory, self).__init__()
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
        return self.Index(fixing, period.fixdate, period.accr_end)

    class Index(IndexFactory.Index):
        def __init__(self, fixing, fixdate, effdate, matdate, coverage):
            super(FloatIndexFactory.Index, self).__init__(fixing)
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


class FwdCurveIndexFactory(IndexFactory):
    def create(self, period):  # simply follows payment schedule
        fixing = self.get_fixing(period.fixdate)
        return self.Index(fixing, period.fixdate, period.accr_start, period.accr_end, period.accr_cov)

    class Index(IndexFactory.Index):
        def __init__(self, fixing, fixdate, matdate):
            super(FwdCurveIndexFactory.Index, self).__init__(fixing)
            self.fixdate = fixdate
            self.matdate = matdate

        def forward(self, fwdcurve):
            if self.fixing is not None:
                return self.fixing
            elif self.effdate.t >= fwdcurve.t0:
                return fwdcurve(self.matdate.t)
            else:
                raise BaseException('missing fixing on %s ...' % self.fixdate)

class LiborIndexFactory(FloatIndexFactory):
    def __init__(self, tenor, calendar, daycount, spotlag='2D', dayroll=DayRoll.ModifiedFollowing, endmonth=True):
        super(LiborIndexFactory, self).__init__()
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
    def __init__(self,
                 hw=None, 
                 baserate=None,
                 index_fac=None,       # range leg rate index factory, e.g. Libor3M
                 rng_def=None,       # defines the rate range for range swap, e.g. ('outside',0.01,0.02)
                 num_days='calendar', # count of days in a period, e.g. 'calendar' for calendar days, 'business' for business days
                 two_ends=(None,None),# defines the dates in a period to calculate the range theta, e.g. slice(1,-1) excludes start and end dates
                 lockout=('skipped',None), # lock-out period, e.g. ('crystallized', -5) or ('skipped', -3)
                 digi_gap=1e-5,     # strike gap of digital spread, e.g. 1bp    
                 **kwargs):
        super(RangeIndexFactory, self).__init__(**kwargs)
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

    @lru_cache(maxsize=100)#@cache_function(1)
    def __parse_libors(self, libors): # paytime is dummy argument for hashing
        ts = HashableArray([l.effdate.t for l in libors])
        te = HashableArray([l.matdate.t for l in libors])
        cov = np.array([l.coverage for l in libors])                 
        return ts, te, cov   

    @lru_cache(maxsize=100)
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


class CMSIndexFactory(FixedIndexFactory):
    __shift_clamp = 1.0

    class Option:
        Cap = 1
        Floor = -1

    def __init__(self, today, proj, disc, swpnsurf,
                 index_fac,  # cms index swap factory
                 kappa=0.0,
                 nswpns=50):
        super(CMSIndexFactory, self).__init__()
        self.today = today
        self.proj = proj
        self.disc = disc
        self.index_fac = index_fac
        self.swpnsurf = swpnsurf
        self.nswpns = nswpns

        def __b(t, T):
            if kappa > 5e-5:  # this is about the optimal cutoff value for kappa
                return (1 - np.exp(-kappa * (T - t))) / kappa
            else:
                return T - t

        self.__b = __b

    def __strikes_and_weights(self, opt, swaption, strike, period):
        if isinstance(swaption, BlackLognormalModel):  # lognormal model
            strike_at_maxvega = swaption.forward * np.exp(swaption.stdev ** 2 / 2)  # at which max vega occurs
            lower_bound = 1e-10  # rate must be positive
        else:  # normal model
            strike_at_maxvega = swaption.forward  # at which max vega occurs
            lower_bound = -1e2  # rate can be negative
        cutoff_vega = swaption.vega(strike_at_maxvega) / 100.0  # cutoff at vega that is 100 times smaller

        find_strike = lambda k: swaption.vega(k) - cutoff_vega
        if opt == self.Option.Cap:
            cutoff_rate = solver(find_strike, strike_at_maxvega, 1e2)  # to high end
        else:  # == self.Option.Floor
            cutoff_rate = solver(find_strike, lower_bound, strike_at_maxvega)  # to low end

        def curves(t, h):  # bumped by h, new curve with (t, T, h)
            def bump(curve):
                def newcurve(T):  # T can be float or Numpy.Array
                    return curve(T) * np.exp(-h * self.__b(t, T))  # curve(t) = 1.0

                return DiscountCurve.from_fn(t, newcurve)

            return bump(self.proj), bump(self.disc)

        def rate_to_h(swaprate):
            def find_h(h):
                newproj, newdisc = curves(period.fixdate.t, h)
                return swaption.underlier.pleg_parrate(newproj, newdisc) - swaprate

            try:  # clamped to avoid double precision overflow
                return solver(find_h, -self.__shift_clamp, self.__shift_clamp)
            except ValueError:
                return self.__shift_clamp  # only positive h causes trouble

        h_stt = rate_to_h(strike)
        h_end = rate_to_h(cutoff_rate)  # clamped if too large

        n = self.nswpns
        H = np.linspace(h_stt, h_end, n + 1)
        K = np.zeros_like(H)
        G = np.zeros_like(H)
        for i, h in enumerate(H):
            newproj, newdisc = curves(period.fixdate.t, h)
            K[i] = swaption.underlier.pleg_parrate(newproj, newdisc)
            G[i] = period.accr_cov * newdisc(period.paydate.t) / swaption.underlier.pleg.get_annuity(newdisc)
        GK = G * (K - K[0])  # [g * (k - K[0]) for g, k in zip(G, K)]

        W = np.zeros(n)
        for i in range(1, n):
            W[i - 1] = (GK[i] - W[:i].dot(K[i] - K[:i])) / (K[i] - K[i - 1])
        return K[:-1], W  # swaption at K[n] is not used

    def cms_rate(self, period, strike=None):
        cms_index_swap = self.index_fac.create(tradedate=period.fixdate)
        swaption = self.swpnsurf.get_swaption(cms_index_swap)
        if period.fixdate == self.today:
            rate = swaption.forward
        else:
            if strike is None:
                strike = swaption.forward

            def weighted_sum(opt):
                K, W = self.__strikes_and_weights(opt, swaption, strike, period)
                return sum(w * swaption.value(opt, k) for k, w in zip(K, W))

            cap = weighted_sum(self.Option.Cap)
            floor = weighted_sum(self.Option.Floor)
            rate = strike + (cap - floor) / (period.accr_cov * self.disc(period.paydate.t))
        if PRINT: print('cms, par, covexity: %s\t%s\t%s' % (rate, swaption.forward, rate - swaption.forward))
        return rate

    def create(self, period):
        fixing = self.get_fixing(period.fixdate)
        if fixing is not None:
            return self.Index(fixing)
        elif period.fixdate >= self.today:
            return self.Index(self.cms_rate(period))
        else:
            raise BaseException('missing fixing on %s ...' % period.fixdate)

if __name__ == '__main__':
    pass
