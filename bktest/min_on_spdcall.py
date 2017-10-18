from scipy.integrate import dblquad, quad
import scipy.stats
import numpy as np

def test_price1(F1, F2, dv1, dv2, rho, K1, K2, T):
    v1 = dv1 * np.sqrt(T)
    v2 = dv2 * np.sqrt(T)
    var = scipy.stats.multivariate_normal(mean=[F1,F2], cov=[[v1*v2,v1*v2*rho],[v1*v2*rho,v2*v2]])
    def int_func1(x, y):
        return var.pdf([x,y])*(y-K2)

    def int_func2(x, y):
        return var.pdf([x,y])*(x-K1)

    res1 = dblquad(int_func1, K2, np.inf, lambda x: x-K2+K1, lambda x: np.inf)
    res2 = dblquad(int_func2, K2, np.inf, lambda x: K1, lambda x: x-K2+K1)
    return res1[0] + res2[0]

def min_on_call(F1, F2, dv1, dv2, rho, K1, K2, T):
    v1 = dv1 * np.sqrt(T)
    v2 = dv2 * np.sqrt(T)
    def int_func1(x):
        return  scipy.stats.norm.cdf(((F1-K1)-(F2-K2) + (v1 * rho - v2) * x)/(v1 * np.sqrt(1-rho**2))) \
                        * (v2 * x + F2- K2) * scipy.stats.norm.pdf(x)

    def int_func2(x):
        return  scipy.stats.norm.cdf(((F2-K2)-(F1-K1) + (v2 * rho - v1) * x)/(v2 * np.sqrt(1-rho**2))) \
                        * (v1 * x + F1- K1) * scipy.stats.norm.pdf(x)
    res1 = quad(int_func1, (K2-F2)/v2, np.inf)
    res2 = quad(int_func2, (K1-F1)/v1, np.inf)
    return res1[0] + res2[0]

