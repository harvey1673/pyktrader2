import numpy as np
import bsopt
import workdays
import misc

class ConvInterp(object):
    def __init__(self, xs, ys, omega = 0.75):
        self._xs = np.array(xs)
        self._ys = np.array(ys)
        self._dim = len(xs)
        self._omega = omega
        xmin = min([ a - b for a, b in zip(xs[1:], xs[:-1])])
        self._stdev = omega * xmin
        self.weights = np.zeros((self._dim, self._dim))
        for idx in range(self._dim):
            self.weights[idx] = self.calc_weight(xs[idx])
        self._y_proxy = np.linalg.solve(self.weights, self._ys)

    def calc_weight(self, xr):
        weight = np.zeros(self._dim)
        xx_adj = xr - self._xs
        npdf = bsopt.pnorm(xx_adj/self._stdev) * self._stdev
        ncdf = bsopt.cnorm(xx_adj / self._stdev)
        diff_pdf = npdf[1:] - npdf[:-1]
        diff_cdf = ncdf[1:] - ncdf[:-1]
        for i in range(1, self._dim-1):
            weight[i] = (-xx_adj[i + 1] * diff_cdf[i] + diff_pdf[i]) / (self._xs[i + 1] - self._xs[i]) \
                            + (xx_adj[i-1] * diff_cdf[i-1] - diff_pdf[i-1]) / (self._xs[i] - self._xs[i-1])
        weight[0] = ncdf[0] + (-xx_adj[1] * diff_cdf[0] + diff_pdf[0] )/(self._xs[1]-self._xs[0])
        weight[self._dim-1] = 1 - ncdf[-1] + ( xx_adj[self._dim-2]*diff_cdf[self._dim-2] - diff_pdf[self._dim-2])/(self._xs[self._dim-1]- self._xs[self._dim-2])
        return weight

    def value(self, xr):
        w = self.calc_weight(xr)
        return (w * self._y_proxy).sum()


class Delta5VolNode(object):
    def __init__(self, vdate, exp_date, fwd, atm, v90, v75, v25, v10, accrual = 'act365', calendar = 'PLIO'):
        self.value_date = vdate
        self.exp_date = exp_date
        self.fwd = fwd
        self.atm = atm
        self.v90 = v90
        self.v75 = v75
        self.v25 = v25
        self.v10 = v10
        self.accrual = accrual
        self.calendar = calendar
        self._interp = None
        self._omega = 0.75
        self.initialize()

    def expiry(self):
        if self.accrual == 'act365':
            return max((self.exp_date - self.value_date).days, 0)/365.25
        else:
            hols = misc.Holiday_Map.get(self.calendar, [])
            return workdays.networkdays(self.value_date, self.exp_date, hols)/252.0

    def initialize(self):
        self.time2mat = self.expiry()
        xs = np.zeros(5)
        ys = np.zeros(5)
        xs[0] = self.delta2logratio(0.9)
        xs[1] = self.delta2logratio(0.75)
        xs[2] = 0.0
        xs[3] = self.delta2logratio(0.25)
        xs[4] = self.delta2logratio(0.10)
        ys[0] = self.atm + self.v90
        ys[1] = self.atm + self.v75
        ys[2] = self.atm
        ys[3] = self.atm + self.v25
        ys[4] = self.atm + self.v10
        self._interp = ConvInterp(xs, ys, self._omega)

    def delta2logratio(self, delta):
        return self.atm * (0.5 * self.atm - np.sqrt(self.time2mat) * bsopt.cnorminv(delta))

    def GetVolByMoneyness(self, xr, mat_date):
        return self._interp.value(xr)

    def GetVolByStrike(self, strike, mat_date):
        return self.GetVolByMoneyness( np.log(strike/self.fwd), mat_date)

    def GetVolByDelta(self, delta, mat_date):
        xr = self.delta2logratio(delta)
        return self.GetVolByMoneyness(xr, mat_date)
