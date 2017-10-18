import numpy as np
import bsopt
import workdays
import datetime
import misc


def delta_to_logratio(delta, vol, time2mat):
    return vol * (0.5 * vol - np.sqrt(time2mat) * bsopt.cnorminv(delta))

def ExpIntegral(b, tau):
    if (b == 0) or (tau ==0):
        return 1.0
    else:
        return (1 - np.exp(-b*tau))/(b*tau)

def SamuelsonFactor1(a, b, t2T, t2mat):
    factor1 = np.sqrt(1 + 2 * a * ExpIntegral(b, t2T) + a * a * ExpIntegral( 2 * b, t2T))
    tdiff = t2T- t2mat
    factor2 = np.sqrt(1 + 2 * a * np.exp(-tdiff * b) * ExpIntegral(b, t2mat) \
                      + a * a * np.exp( - 2 * b * tdiff) * ExpIntegral( 2 * b, t2mat))
    return factor2/factor1

def SamuelsonFactor2(a, b, t, T, mat):
    return SamuelsonFactor1(a, b, T - t, mat - t)

def FitDelta5VolParams(t2exp, fwd, strike_list, vol_list):
    xi = [ np.log(strike/fwd) for strike in strike_list]
    intp = ConvInterp(xi, vol_list, 0.75)
    atm = intp.value(0.0)
    volparams = [atm]
    for d in [0.9, 0.75, 0.25, 0.1]:
        volparams.append(delta_to_logratio(d, atm, t2exp))
    return volparams

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

    def calc_texp(self, exp_date):
        hols = misc.Holiday_Map.get(self.calendar, [])
        return misc.conv_expiry_date(self.value_date, exp_date, self.accrual, hols = [])

    def initialize(self):
        self.time2exp = self.calc_texp(self.exp_date)
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
        return delta_to_logratio(delta, self.atm, self.time2exp)

    def GetVolByMoneyness(self, xr, mat_date = None):
        return self._interp.value(xr)

    def GetVolByStrike(self, strike, mat_date = None):
        return self.GetVolByMoneyness( np.log(strike/self.fwd), mat_date)

    def GetVolByDelta(self, delta, mat_date = None):
        xr = self.delta2logratio(delta)
        return self.GetVolByMoneyness(xr, mat_date)

class AsianDelta5VolNode(Delta5VolNode):
    def __init__(self, vdate, exp_date, fwd, atm, v90, v75, v25, v10, accrual='act365', calendar='PLIO'):
        super(AsianDelta5VolNode, self).__init__(vdate, exp_date, fwd, atm, v90, v75, v25, v10, accrual, calendar)

    def delta2logratio(self, delta):
        return self.vol_adj * (0.5 * self.vol_adj - np.sqrt(self.time2exp) * bsopt.cnorminv(delta))

    def initialize(self):
        self.tau = max(0.0, self.calc_texp(datetime.date(self.exp_date.year, self.exp_date.month, 1) \
                                      - datetime.timedelta(days=1)))
        self.vol_adj = bsopt.asian_vol_adj(self.atm, self.time2exp, self.tau)
        super(AsianDelta5VolNode, self).initialize()

class SamuelDelta5VolNode(Delta5VolNode):
    def __init__(self, vdate, exp_date, fwd, atm, v90, v75, v25, v10, alpha, beta, accrual='act365', calendar='PLIO'):
        super(SamuelDelta5VolNode, self).__init__(vdate, exp_date, fwd, atm, v90, v75, v25, v10, accrual, calendar)
        self.alpha = alpha
        self.beta = beta

    def GetVolByMoneyness(self, xr, mat_date):
        imp_vol = super(SamuelDelta5VolNode, self).GetVolByMoneyness(xr, mat_date)
        t2T = self.calc_texp(self.exp_date)
        t2mat = self.calc_texp(mat_date)
        if t2T <= 0:
            return imp_vol
        else:
            return imp_vol * SamuelsonFactor1(self.alpha, self.beta, t2T, t2mat)

    def GetInstVol(self, mat_date):
        t2T = self.calc_texp(self.exp_date)
        t2mat = self.calc_texp(mat_date)
        a = self.alpha
        b = self.beta
        if (t2T <= 0):
            return self.atm
        else:
            factor = np.sqrt(1 + 2 * a * ExpIntegral(b, t2T - t2mat) + \
                             a * a * ExpIntegral(2*b, t2T - t2mat))
            return self.atm/ factor * (1 + a * np.exp(-b*(t2T - t2mat)))
