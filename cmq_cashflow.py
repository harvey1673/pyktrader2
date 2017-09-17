#-*- coding:utf-8 -*-
from repoze.lru import lru_cache
from cmq_utils import *  
from cmq_rate_index import *  
import numpy as np
from scipy.optimize import brentq as solver
import copy

class LegFactory:
    class RollingRule(ql.DateGeneration):         
        #Backward = 0 # Bcackward from maturity date to effective date
        #Forward = 1 # forward from effective date to maturity date
        pass

    def __init__(self, frequency, calendar, daycount, index_fac,                                 
                 dayroll=DayRoll.ModifiedFollowing,
                 endmonth=False,
                 spotlag='2D', 
                 paylag='0D', 
                 rollrule=RollingRule.Backward,
                 notl_base=1e6,
                 notl_amort_abs=None,
                 notl_amort_rel=None,
                 notl_amort_freq=1,
                 rate_spread=0.0, # rate adjustment
                 rate_leverage=1.0,
                 **kwargs):
        #super(LegFactory, self).__init__(**kwargs)
        self.frequency = Period(frequency) 
        self.calendar = calendar
        self.daycount = daycount 
        self.index_fac = index_fac
                      
        self.dayroll = dayroll
        self.endmonth = endmonth
        self.spotlag = Period(spotlag)                     
        self.paylag = Period(paylag)         
        self.rollrule = rollrule  
              
        self.notl_base = notl_base
        self.notl_amort_abs = notl_amort_abs
        self.notl_amort_rel = notl_amort_rel
        self.notl_amort_freq = notl_amort_freq

        self.rate_spread = rate_spread
        self.rate_leverage = rate_leverage
                 
    def copy(self, **kwargs):
        specs = copy.copy(self)
        for k in kwargs.keys():
            if k in specs.__dict__:
                specs.__setattr__(k, kwargs[k])        
        return specs

    def __notl_generator(self, n):
        if self.notl_amort_abs is not None:
            for stuff in self.notl_base + np.arange(n) / self.notl_amort_freq * self.notl_amort_abs: # '//' integer division
                yield stuff
        elif self.notl_amort_rel is not None:
            for stuff in self.notl_base * (1 + self.notl_amort_rel) ** int(np.arange(n)/self.notl_amort_freq):
                yield stuff
        else:
            for stuff in self.notl_base * np.ones(n):
                yield stuff

    def roll_date(self, start, period):
        if isinstance(period, Period):
            date = self.calendar.advance(start, period, self.dayroll, self.endmonth)
        elif period == 'spot':
            date = self.calendar.advance(start, self.spotlag, self.dayroll)
        elif period == '-spot':
            date = self.calendar.advance(start, -self.spotlag, self.dayroll)
        elif period == 'pay':
            date = self.calendar.advance(start, self.paylag, self.dayroll)
        else:
            raise BaseException('invalid date rolling ...')   
        return Date.convert(date)

    def schedule(self, tradedate=None, expiry=None, start=None, tenor=None):
        """
        'expiry', 'start' both are None ==> spot swap
            effdate = spotdate = tradedate (+) spotlag
        'start' is Not None ==> forward swap start
            if 'start' is Date: effdate = start
            if 'start' is Period: effdate = tradedate (+) spotlag (+) start
        'expiry' is Not None ==> option expiry
            if 'expiry' is Date: fixdate = expiry
            if 'expiry' is Period: fixdate = tradedate (+) expiry
        """     
        # determine effdate
        if isinstance(expiry, Period): # effdate = tradedate (+) expiry (+) spotlag
            effdate = self.roll_date(self.roll_date(tradedate, expiry), 'spot')
        elif isinstance(expiry, Date): # effdate = expiry (+) spotlag
            effdate = self.roll_date(expiry, 'spot')
        elif isinstance(start, Period): # effdate = tradedate (+) spotlag (+) start = spotdate (+) start
            effdate = self.roll_date(self.roll_date(tradedate, 'spot'), start)
        elif isinstance(start, Date): # effdate = start
            effdate = start
        else: # expiry/start both are NONE => spot swap; effdate = trade (+) spotlag
            effdate = self.roll_date(tradedate, 'spot') # by default: dayroll=Following, EoM=False

        matdate = self.roll_date(effdate, tenor)

        #return Schedule(effdate, matdate, self.frequency, self.calendar, self.dayroll, self.rollrule, self.endmonth).dates()           
        if tenor <= self.frequency: # products with single cashflow 
            return [effdate, self.roll_date(effdate, tenor)]
        else: # products with multiple cashflows
            def n_months(p):
                if p.units() == Period.Units.Months:
                    return p.length()
                elif p.units() == Period.Units.Years:
                    return p.length() * 12
                else:
                    raise BaseException('invalid tenor period ...') 
            nm_tenor = n_months(tenor)
            nm_index = n_months(self.frequency) 
            if self.rollrule == self.RollingRule.Backward:
                accr_end_months = list(reversed(range(nm_tenor, 0, -nm_index)))                  
            elif self.rollrule == self.RollingRule.Forward:
                accr_end_months = list(range(nm_index, nm_tenor, nm_index)) + [nm_tenor]
            else:
                raise BaseException('invalid schedule rolling rule ...') 
            return [effdate] + [self.roll_date(effdate, Period(n, Period.Units.Months)) for n in accr_end_months]

    def create(self, tradedate=None, expiry=None, start=None, tenor=None):
        """
        'expiry', 'start' both are None ==> spot swap
            effdate = spotdate = tradedate (+) spotlag
        'start' is Not None ==> forward swap start
            if 'start' is Date: effdate = start
            if 'start' is Period: effdate = tradedate (+) spotlag (+) start
        'expiry' is Not None ==> option expiry
            if 'expiry' is Date: fixdate = expiry
            if 'expiry' is Period: fixdate = tradedate (+) expiry

        The following illustrates the accrual and fixing period for a spot start floating leg:        
                 trade  spot                    A0e                     A1e                     A2e
        Accrual &: |-----|-----------------------|---|-------------------|---|-------------------|---|   
        Payment  : F0   A0s                     A1s  P0                 A2s  P1                 A3s  P2
                         :                       :                       :
        Fixing[0]: |-----|-------------------------|                     :
                   F0   F0s                      : F0e                   :
        Fixing[1]:                         |-----|--------------------------|         
                                           F1   F1s                      : F1e
        Fixing[2]:                                                 |-----|-------------------------|         
                                                                   F2   F2s                        F2e
        """     
        grid = self.schedule(tradedate=tradedate, expiry=expiry, start=start, tenor=tenor)
        notionals = self.__notl_generator(len(grid) - 1)  
        def create_coupon(accr_start, accr_end):
            notional = next(notionals) # amortization if any
            fixdate = self.roll_date(accr_start, '-spot') # fixdate = fix_start (-) spotlag
            paydate = self.roll_date(accr_end, 'pay') # paydate = accr_end (+) paylag       
            accr_cov = self.daycount.yearFraction(accr_start, accr_end)                                          
            period = self.Leg.Coupon(fixdate, accr_start, accr_end, paydate, accr_cov, notional)
            period.index = self.index_fac.create(period) # attach an index to coupon period     
            return period      
        cp = np.array([create_coupon(start, end) for start, end in zip(grid[:-1], grid[1:])])
        return self.Leg(self, cp)

    class Leg: # floating leg fixed in advance and paid in-arrears     
        class Coupon:
            """ Container for Accrual Periods """
            def __init__(self, fixdate, accr_start, accr_end, paydate, accr_cov, notional):
                self.fixdate = fixdate
                self.accr_start = accr_start 
                self.accr_end = accr_end
                self.paydate = paydate
                self.accr_cov = accr_cov                        
                self.notional = notional

            @print_self(2, 10, 1)
            def __repr__(self):
                pass
         
        def __init__(self, factory, coupon_array):
            self.factory = factory  
            self.__update(coupon_array)

        def __update(self, cp):
            self.cp = cp
            self.fixdate = cp[0].fixdate
            self.effdate = cp[0].accr_start
            self.matdate = cp[-1].accr_end 

            # create numpy.arrays for caching purpose
            self.np_paydates = HashableArray([p.paydate.t for p in self.cp])
            self.np_acovs = np.array([p.accr_cov for p in self.cp])        
            self.np_effnotl = self.np_acovs * np.array([p.notional for p in self.cp])

        def value(self, proj, disc, spread=0.0):
            """
            the coupons of the leg must be unpaid yet as of today (assuming today is the valuation date):                    
            |-----|-----------------------|---|
            F0   A0s                     A0e  P0  
                                    |-----|-----------------------|---|
                                    F1   A1s                     A1e  P1   
                                                            |-----|-----------------------|---|
                                                            F2   A2s                     A2e  P2         
            It can be that F1 < today < P0, there would be 2 unpaid but fixed coupons, however this is very rare.
            """
            if isinstance(proj, (float, int)): # proj is a single float, e.g. a single fixed rate
                rates = proj             
            elif np.iterable(proj): # proj is a vector of floats, e.g. predefined fixed rates           
                assert len(proj) == len(self.cp)
                rates = proj                      
            elif callable(proj): # proj is a curve or a function, a floating leg
                rates = np.array([p.index.forward(proj) for p in self.cp])
            else: 
                raise BaseException('invalid rate/projection ...') 

            rates = rates * self.factory.rate_leverage + self.factory.rate_spread
            return self.np_effnotl.dot((rates + spread) * disc(self.np_paydates)) 

        def get_spread(self, proj, disc, pv):
            def find_spread(spread):
                return self.value(proj, disc, spread=spread) - pv 
            return solver(find_spread, -1e2, 1e2)
    
        def get_annuity(self, disc):
            """ Assuming cp[0].paydate >= today """
            return self.np_acovs.dot(disc(self.np_paydates))
 
        def get_schedule(self):
            return [self.cp[0].accr_start] + [p.accr_end for p in self.cp]

        def subleg(self, cutdate, enddate=None, cutoff='preceding'):
            """
            slice coupon periods:
                return subleg having coupon periods in between cutdate and enddate 
                cut at enddate follows 'preceding' rule if enddate is not one of the accrual end dates                     
            before: 
            leg:     |--------------|--------------|--------------|--------------|
                                    .      ^       .              .              .
                                    .   cutdate    .              .              .
            after:                  .      .       .              .              .
            cutoff = 'preceding':   |--------------|--------------|--------------|
            cutoff = 'present':            |-------|--------------|--------------|
            cutoff = 'following':                  |--------------|--------------| 
            """      
            if enddate is None: enddate = Date.maxDate()
            assert self.effdate <= cutdate <= self.matdate
            assert cutdate < enddate

            cp = [p for p in self.cp if cutdate < p.accr_end <= enddate]
            if not cp: return None # cp is an empty list

            if cutoff == 'preceding':
                pass # no additional process
            elif cutoff == 'following':
                cp = cp[1:] # remove the leading period
                if not cp: return None
            elif cutoff == 'present':
                if cutdate != cp[0].accr_start:
                    print('warning: leg cut to present and cutdate %s does not follow payment schedule' % cutdate)
                period = copy.copy(cp[0]) # make a shadow copy to leave the original period intact
                period.fixdate = self.factory.roll_date(cutdate, '-spot')
                period.accr_start = cutdate
                period.accr_cov = self.factory.daycount.yearFraction(period.accr_start, period.accr_end)              
                if isinstance(period.index, FloatIndexFactory.Index): # create a chopped Libor, e.g. for calibration swaptions
                    period.index = FloatIndexFactory().create(period) 
                cp[0] = period
            else:
                raise BaseException('invalid cutoff spec. ...')
        
            sub_leg = copy.copy(self) # shallow copy              
            sub_leg.__update(cp)
            return sub_leg   
    
        #def __getitem__(self, slice):
        #    """ slice coupon periods: return subleg having cp[start:end] """
        #    if isinstance(slice, int):  
        #        cp = [self.cp[slice]] # keep a single period as a list
        #    else:
        #        cp = self.cp[slice]
        #    sub_leg = copy.copy(self) # shallow copy              
        #    sub_leg.__update(cp)
        #    return sub_leg 

        @print_self(0, 11)
        def __repr__(self):
            pass


class ExerciseSchedule:
    def __init__(self, frequency, calendar,
                 dayroll=DayRoll.ModifiedFollowing, endmonth=True, spotlag='2D', 
                 paylag='0D', rollrule=LegFactory.RollingRule.Backward):
        self.factory = LegFactory(frequency, calendar, None, FixedIndexFactory(None), dayroll=dayroll, 
                                  endmonth=endmonth, spotlag=spotlag, paylag=paylag, rollrule=rollrule)
    
    def dates(self, tradedate, start, end):
        start = Period(start)
        end = Period(end)
        short = self.factory.schedule(tradedate=tradedate, tenor=start)
        long = self.factory.schedule(tradedate=tradedate, tenor=end)
        return short[-1:] + [d for d in long if d not in short]


class InterestRateSwapFactory:
    def __init__(self, rleg_fac, pleg_fac, tenor=None):
        self.rleg_fac = rleg_fac  # receiver leg factory
        self.pleg_fac = pleg_fac  # payer leg factory
        self.tenor = tenor 

    def create(self, tradedate=None, expiry=None, start=None, tenor=None):
        if tenor is None:
            tenor = self.tenor
        rleg = self.rleg_fac.create(tradedate=tradedate, expiry=expiry, start=start, tenor=tenor)        
        pleg = self.pleg_fac.create(tradedate=tradedate, expiry=expiry, start=start, tenor=tenor)
        return self.InterestRateSwap(rleg, pleg)

    class InterestRateSwap:
        def __init__(self, rleg, pleg):
            self.rleg = rleg # receiver leg
            self.pleg = pleg # payer leg 
            self.__update()  
    
        def __update(self):
            self.fixdate = None if self.rleg.fixdate != self.pleg.fixdate else self.rleg.fixdate
            self.effdate = None if self.rleg.effdate != self.pleg.effdate else self.rleg.effdate
            self.matdate = None if self.rleg.matdate != self.pleg.matdate else self.rleg.matdate

        def value(self, rrates, prates, disc): # value of payer swap: rleg_value - pleg_value
            """ Rates can be a float array, a float, or a projection curve """
            return self.rleg.value(rrates, disc) - self.pleg.value(prates, disc)

        def pleg_parrate(self, proj, disc):
            """ assuming rleg is floating leg, pleg is fixed leg """
            return self.pleg.get_spread(0.0, disc, self.rleg.value(proj, disc))
            #if self.fixing is not None:
            #    return self.fixing
            #elif self.effdate.t >= proj.t0:
            #    return self.pleg.get_spread(0.0, disc, self.rleg.value(proj, disc))
            #else:
            #    raise BaseException('missing fixing on %s ...' % self.fixdate)

        def subswap(self, cutdate, enddate=None, cutoff='preceding'):
            """
            generate sub-swap:
                return subswap having coupon periods in between cutdate and enddate
                **kwargs: cutoff='preceding'

            note that usually the payment dates of fixed leg are a subset of that of floating leg        
                    
            Before cut:
            Floating: |------|------|------|------|------|------|------|------|------|------|------|------|
            Fixed     |---------------------------|---------------------------|---------------------------|
                                                  .             .   ^  .      .                           . 
            After cut:                            .             . cutdate     .                           .
                                                  .             .   .  .      .                           .
            cutoff='preceding':                   .             .   .  .      .                           .
            Floating:                             .             |------|------|------|------|------|------|
            Fixed                                 |---------------------------|---------------------------|
                                                                    .  .      .                           .
            cutoff='present':                                       .  .      .                           .
            Floating:                                               |--|------|------|------|------|------|
            Fixed                                                   |---------|---------------------------|
                                                                              .                           .
            cutoff='following':                                               .                           .
            Floating:                                                         |------|------|------|------|
            Fixed                                                             |---------------------------|
            """
            sub_swap = copy.copy(self) # shallow copy
            sub_swap.rleg = self.rleg.subleg(cutdate, enddate, cutoff=cutoff)
            sub_swap.pleg = self.pleg.subleg(cutdate, enddate, cutoff=cutoff)
            sub_swap.__update()
            return sub_swap 
    

if __name__ == '__main__':
    pass
    
