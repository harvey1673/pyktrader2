#-*- coding:utf-8 -*-
from scipy.interpolate import interp1d, UnivariateSpline
import QuantLib as ql
import numpy as np
from math import log
import time
from functools import wraps

# from bisect import bisect_left 
# bisect_left: a[:i] < x <= a[i:] or a[i-1] < x <= a[i]
# bisect_right: a[:i] <= x < a[i:] or a[i-1] <= x < a[i]

def str2tenor(input):
    if input == None:
        return None
    if '-' in input:
        tenor = Date(str(input))
    else:
        tenor = Period(str(input))
    return tenor
    
class LinearFlat(interp1d): # linear interpolation with flat extension
    def __init__(self, x, y):
        return super(LinearFlat, self).__init__(x, y, kind='linear', bounds_error=False, fill_value=(y[0],y[-1]))


class CubicSplineFlat(UnivariateSpline): # cubic spline interpolation with flat extension
    def __init__(self, x, y):
        return super(CubicSplineFlat, self).__init__(x, y, s=0, ext=3)


class FlatCubicSpline(UnivariateSpline): # cubic spline interpolation with zero 1st and 2nd derivative at edges
    def __init__(self, x, y): # x is in ascending order
        epsilon = 1e-8 # mimic zero 1st and 2nd derivatives at edges
        x = np.hstack((x[0] * (1 - epsilon), x, x[-1] * (1 + epsilon)))
        y = np.hstack((y[0], y, y[-1]))
        super(FlatCubicSpline, self).__init__(x, y,  s=0, ext=3)

class HashableArray(np.ndarray):
    def __new__(cls, *args):
        return np.asarray(*args).view(cls)     

    def __eq__(self, other):
        return np.array_equal(self, other)

    def __hash__(self):
        return hash(self.tostring())

    def __getitem__(self, *args):
        return HashableArray(super(HashableArray, self).__getitem__(*args))

class DayCount:
    ACT360 = ql.Actual360() 
    ACT365Fixed = ql.Actual365Fixed()
    _30360BB = ql.Thirty360(ql.Thirty360.BondBasis)
    _30E360 = ql.Thirty360(ql.Thirty360.EurobondBasis)
    _30360US = ql.Thirty360(ql.Thirty360.USA)
    ACT365NL = ql.Actual365NoLeap()
    ACTACT = ql.ActualActual()

class Calendar:
    def decorate(obj): # process 'advance' function to return 'Date' object
        old_advance = obj.advance
        def new_advance(*args, **kwargs):
            return Date.convert(old_advance(*args, **kwargs))
        obj.advance = new_advance
        return obj

    TGT = decorate(ql.TARGET())
    US = decorate(ql.UnitedStates(ql.UnitedStates.NYSE))     
    UK = decorate(ql.UnitedKingdom(ql.UnitedKingdom.Exchange))
    US_UK = decorate(ql.JointCalendar(US, UK))
    SG = decorate(ql.Singapore(ql.Singapore.SGX))
    CN = decorate(ql.China())
    JP = decorate(ql.Japan())
    HK = decorate(ql.HongKong())
    DE = decorate(ql.Germany())

    @classmethod
    def fetch(cls, id): # id as string, e.g. 'US' / 'TGT'
        return cls.__dict__[id]   


class DayRoll:
    Following = ql.Following 
    ModifiedFollowing = ql.ModifiedFollowing
    Unadjusted = ql.Unadjusted
    Preceding = ql.Preceding
    ModPreceding = ql.ModifiedPreceding
     

class Date(ql.Date):
    origin = None
    year_frac = DayCount.ACT365Fixed.yearFraction
    weekdays = ('', 'Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat') # Sun=1, ..., Sat=7 

    @classmethod
    def set_origin(cls, *args):
        cls.origin = ql.Date(*args) # firstly initiate to ql.Date object
        cls.origin = cls.convert(cls.origin) # then convert to Date object
        return cls.origin

    @classmethod
    def maxDate(cls):
        return cls.convert(super(Date, cls).maxDate())
    
    @classmethod
    def convert(cls, date):
        return cls(date.serialNumber()) 

    @classmethod
    def from_timestamp(cls, date): # convert pandas timestamp to Date object
        return cls(date.day, date.month, date.year) 

    def __init__(self, *args):
        if isinstance(args[0], str): # e.g. '2012-11-23'
            super(Date, self).__init__(*[int(s) for s in args[0].split('-')][::-1])
        else: # other format
            super(Date, self).__init__(*args)
        self.t = self.year_frac(self.origin, self)

    def __ge__(self, x): # ql.Date from Python SWIG has no '>=' and '<=' 
        return not self < x

    def __le__(self, x):
        return not self > x

    def __float__(self):
        return self.t

    def __add__(self, n):
        return self.convert(super(Date, self).__add__(int(n)))

    def __sub__(self, n):
        if isinstance(n, ql.Date): 
            return self.serialNumber() - n.serialNumber()
        else:
            return self + (-n)

    def __repr__(self):
        return "Date(%s-%s-%s %s)" % (self.year(), self.month(), self.dayOfMonth(), self.weekdays[self.weekday()])

    def __str__(self):
        return "%04d-%02d-%02d" % (self.year(), self.month(), self.dayOfMonth())


class Period(ql.Period): # make it hashable
    class Units:
        Months = ql.Months
        Years = ql.Years
        Days = ql.Days
        Weeks = ql.Weeks

    def __init__(self, *args, **kwargs):
        super(Period, self).__init__(*args, **kwargs)
        self.__hash = hash(str(self))

    def __ge__(self, x): # ql.Period from Python SWIG has no '>=' and '<='
        return not self < x

    def __le__(self, x):
        return not self > x

    def __hash__(self):
        return self.__hash

    def __sub__(self, p):
        return self + (-p)

    @staticmethod
    def __parse__(p1, p2):
        assert {p1.units(), p2.units()} <= {Period.Units.Months, Period.Units.Years} # a subset of "year" and "month" 
        l1 = p1.length() * 12 if p1.units() == Period.Units.Years else p1.length()
        l2 = p2.length() * 12 if p2.units() == Period.Units.Years else p2.length()
        return l1, l2

    def __add__(self, p):
        l1, l2 = self.__parse__(self, p)
        return self.__class__(l1 + l2, Period.Units.Months) 
    
    def __truediv__(self, p):
        l1, l2 = self.__parse__(self, p)
        assert l1 // l2 != 0 and l1 % l2 == 0
        return l1 // l2  


class Schedule(ql.Schedule):
    DateGeneration = ql.DateGeneration
    def __init__(self, effdate, matdate, freq, calendar, dayroll, rollrule, endmonth):
        super(Schedule, self).__init__(effdate, matdate, freq, calendar, dayroll, dayroll, rollrule, endmonth)

    def dates(self):
        return np.array([Date.convert(d) for d in self]) # np.hstack(map(Date.convert, self))



class FormatPrint:
    def __init__(self, format='{0:.2f}'):
        self.format = format
        return

    def __call__(self, *args, **kwargs):
        args = (self.format.format(a) if isinstance(a, float) else a for a in args)
        kwargs = {k:self.format.format(v) if isinstance(v, float) else v for k,v in kwargs.items()}
        print args, kwargs


def convert_to_interpolator(size=300, ns=4.5, kind='linear'):
    def decorate(fn):
        @wraps(fn) 
        def interpolator(x):
            stdev = np.std(x)
            if stdev == 0:
                return fn(np.mean(x))
            else:
                xv = np.linspace(-stdev * ns, stdev * ns, size)
                xv[0] = np.min(x)
                xv[-1] = np.max(x)
                yv = [fn(z) for z in xv]             
                return interp1d(x=xv, y=yv, kind=kind)(x)
        return interpolator
    return decorate 


def time_this(fn):
    """
    decorator that reports the execution time.
    """
    # use @wraps(fn) to expose the function name and docstring to the caller of
    # the decorated function (otherwise, we would see the function name and
    # docstring for the decorator, not the function it decorates).
    @wraps(fn) 
    def wrapper(*args, **kwargs):
        function_name = fn.__name__
        print function_name + ' starts ...'
        start = time.time()
        result = fn(*args, **kwargs)
        print function_name + ' finished in ' + '{0:.2f}'.format(time.time() - start), 'seconds\n'
        return result
    return wrapper 


#def cache_function(order): # similar to functools "@lru_cache(maxsize=None)"
#    def decorate(fn):
#        cache = {}
#        @wraps(fn) 
#        def wrapper(*args, **kwargs):
#            try:
#                return cache[args[order]]
#            except:
#                cache[args[order]] = fn(*args, **kwargs)
#                return cache[args[order]]
#        return wrapper
#    return decorate 

def print_self(indent=2, length=8, linespace=0): # similar to functools "@lru_cache(maxsize=None)"
    def decorate(fn):
        @wraps(fn) 
        def wrapper(self):
            fn(self)
            d = vars(self)
            res = (k + ' ' * (length - len(k)) + ': ' + str(d[k]) for k in sorted(d))
            newline = '\n' + ' ' * indent
            return newline + newline.join(res) + newline * linespace
        return wrapper
    return decorate 

def print_results(pv_pde=None, pv_mc=None):
    if pv_pde is not None:
        print 'PV(PDE): ' + '%s' % pv_pde
    if pv_mc is not None:
        print 'PV(MC ): ' + '%s' % pv_mc
    if pv_pde is not None and pv_mc is not None:
        print 'diff.% : ' + '%s%%' % '{0:.6f}'.format(log(pv_pde / pv_mc) * 100.0)


if __name__ == '__main__':
    pass
