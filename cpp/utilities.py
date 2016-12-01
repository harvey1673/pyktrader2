#-*- coding:utf-8 -*-

# from bisect import bisect_left 
# bisect_left: a[:i] < x <= a[i:] or a[i-1] < x <= a[i]
# bisect_right: a[:i] <= x < a[i:] or a[i-1] <= x < a[i]

from math import log
import time
from functools import wraps
import numpy as np
from scipy.interpolate import interp1d 

class FormatPrint:
    def __init__(self, format='{0:.2f}'):
        self.format = format
        return

    def __call__(self, *args, **kwargs):
        args = (self.format.format(a) if isinstance(a, float) else a for a in args)
        kwargs = {k:self.format.format(a) if isinstance(a, float) else a for k,v in kwargs.items()}
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


