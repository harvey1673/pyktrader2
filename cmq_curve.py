#-*- coding:utf-8 -*-
from math import log, exp 
from scipy.interpolate import interp1d
import numpy as np
import pandas as pd

class DiscountCurve(object):
    class InterpMode:
        LinearZero = 0 # linear on zero rates
        LinearLogDiscount = 1 # linear on log discounts
    def __init__(self, t0, fn):
        self.t0 = t0
        self.__df_t0 = fn(t0)
        self.__discount_factor = fn
            
    @classmethod       
    def from_array(cls, tenors, dfs, t0=None, interp_mode=InterpMode.LinearZero): ######################
        """Create a Curve object: tenors (floats), dfs (floats), interp_mode"""
        if t0 is None:
            t0 = tenors[0]        
        assert len(tenors) == len(dfs)       
        if interp_mode == cls.InterpMode.LinearZero: 
            y = -np.log(dfs[1:]) / (tenors[1:] - tenors[0])            
            linzero = interp1d(tenors[1:], y, kind='linear', bounds_error=False, fill_value=(y[0], y[-1]))
            return cls(t0, lambda t: np.exp(-linzero(t) * t))    
        elif interp_mode == cls.InterpMode.LinearLogDiscount:
            linlogdisc = interp1d(tenors, np.log(dfs), kind='linear', bounds_error=False, fill_value='extrapolate')           
            return cls(t0, lambda t: np.exp(linlogdisc(t)))           
        else: 
            raise BaseException('invalid curve interpolation mode ...')       
            
    @classmethod       
    def from_fn(cls, t0, fn):
        return cls(t0, fn)

    def __call__(self, t): # t can be float or numpy.arrays
        if hasattr(t, "__iter__"):
            return np.array([ self.__discount_factor(float(s)) / self.__df_t0 for s in t])
        else:
            return self.__discount_factor(t) / self.__df_t0
            
    def forward(self, t, dt=3e-3): # instantaneous forward rate
        return (self(t - dt) / self(t + dt) - 1) / dt / 2
        
    @classmethod 
    def load(cls, filename, sheetname, t0=None):
        sheet = pd.read_excel(filename, sheetname)
        tenors = np.array([d for d in sheet['dates']])
        discounts = np.array(sheet['discounts'].tolist())
        return cls.from_array(tenors, discounts, t0)
        
class CompositeCurve(DiscountCurve):
    def __init__(self, c1, c2, c3):   
        """ 
        Create a Composite Curve object:
        c1, c2, c3: three standalone curves
        return: c1(t) / c2(t) * c3(t) 
        """
        self.c1 = c1
        self.c2 = c2
        self.c3 = c3
        
    def __call__(self, t): 
        return self.c1(t) / self.c2(t) * self.c3(t)
        
class ForwardCurve(object):
    class InterpMode:
        PiecewiseConst = 0
        Linear = 1  # linear on zero rates
        LinearLog = 2  # linear on log discounts
        
    def __init__(self, t0, fn):
        self.t0 = t0
        self.__fwdcurve = fn
        
    @classmethod
    def from_array(cls, tenors, forwards, t0=None, interp_mode=InterpMode.PiecewiseConst):
        """Create a Curve object: tenors (floats), fwds (floats), interp_mode"""
        if t0 is None:
            t0 = tenors[0]
        assert len(tenors) == len(forwards)
        if interp_mode == cls.InterpMode.PiecewiseConst:
            interpfwd = interp1d(tenors, forwards, kind='zero', bounds_error=False, fill_value='extrapolate')
            return cls(t0, lambda t: interpfwd(t))
        elif interp_mode == cls.InterpMode.Linear:
            interpfwd = interp1d(tenors, forwards, kind='linear', bounds_error=False, fill_value='extrapolate')
            return cls(t0, lambda t: interpfwd(t))
        elif interp_mode == cls.InterpMode.LinearLog:
            linzero = interp1d(tenors, np.log(forwards), kind='linear', bounds_error=False, fill_value='extrapolate')
            return cls(t0, lambda t: np.exp(linzero(t)))
        else:
            raise BaseException('invalid curve interpolation mode ...')
            
    @classmethod
    def from_fn(cls, t0, fn):
        return cls(t0, fn)

    def __call__(self, t):  # t can be float or numpy.arrays
        if hasattr(t, "__iter__"):
            return np.array([self.__fwdcurve(float(s)) for s in t])
        else:
            return self.__fwdcurve(t)
            
    def forward(self, t):
        return self(t)
        
    @classmethod
    def load(cls, filename, sheetname, t0=None):
        sheet = pd.read_excel(filename, sheetname)
        tenors = np.array([d for d in sheet['dates']])
        forwards = np.array(sheet['forwards'].tolist())
        return cls.from_array(tenors, forwards, t0)

class VolCurve(object):
    class InterpMode:
        LinearTime = 0  # linear on zero rates
        SqrtTime = 1  # linear on log discounts
        
    def __init__(self, t0, fn):
        self.t0 = t0
        self.__fwdcurve = fn
        
    @classmethod
    def from_array(cls, tenors, vols, t0=None, interp_mode=InterpMode.LinearTime):
        """Create a Curve object: tenors (floats), fwds (floats), interp_mode"""
        if t0 is None:
            t0 = tenors[0]
        assert len(tenors) == len(vols)
        if interp_mode == cls.InterpMode.LinearTime:
            volsq_time = [ v * v * t for t, v in zip(tenors, vols) ]
            interpvol = interp1d(tenors, volsq_time, kind='linear', bounds_error=False, fill_value=(volsq_time[0], volsq_time[-1]))
            return cls(t0, lambda t: (interpvol(t)/t)**0.5)
        elif interp_mode == cls.InterpMode.SqrtTime:
            tsqrt = [ t**0.5 for t in tenors]
            interpvol = interp1d(tsqrt, vols, kind='linear', bounds_error=False, fill_value=(vols[0], vols[-1]))
            return cls(t0, lambda t:  interpvol(t**0.5))
        else:
            raise BaseException('invalid curve interpolation mode ...')
            
    @classmethod
    def from_fn(cls, t0, fn):
        return cls(t0, fn)

    def __call__(self, t):  # t can be float or numpy.arrays
        if hasattr(t, "__iter__"):
            return np.array([self.__fwdcurve(float(s)) for s in t])
        else:
            return self.__fwdcurve(t)
            
    def forward(self, t):
        return self(t)
        
    @classmethod
    def load(cls, filename, sheetname, t0=None):
        sheet = pd.read_excel(filename, sheetname)
        tenors = np.array([d for d in sheet['dates']])
        forwards = np.array(sheet['forwards'].tolist())
        return cls.from_array(tenors, forwards, t0)
        
if __name__ == '__main__':
    pass
