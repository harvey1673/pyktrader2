#-*- coding:utf-8 -*-

from math import log, exp 
from misc import *  
from scipy.interpolate import interp1d
import numpy as np
import pandas  
from functools import lru_cache  

class Curve:
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

    @lru_cache(maxsize=None)
    def __call__(self, t): # t can be float or numpy.arrays
        return self.__discount_factor(t) / self.__df_t0

    def forward(self, t, dt=3e-3): # instantaneous forward rate
        return (self(t - dt) / self(t + dt) - 1) / dt / 2

    @classmethod 
    def load(cls, filename, sheetname, t0=None):
        sheet = pandas.read_excel(filename, sheetname)
        tenors = np.array([Date.from_timestamp(d).t for d in sheet['dates']])
        discounts = np.array(sheet['discounts'].tolist())
        return cls.from_array(tenors, discounts, t0)


class CompositeCurve(Curve):      
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


if __name__ == '__main__':
    pass