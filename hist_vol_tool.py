import bsopt
import copy
import dateutil
import pandas as pd
import math
import mysqlaccess
from scipy.stats import norm
from misc import *

SOLVER_ERROR_EPSILON = 1e-5
ITERATION_NUM = 100
ITERATION_STEP = 0.001
YEARLY_DAYS = 365.25
# Cash flow calculation for delta hedging.
# Inside the period, Vol is constant and hedging frequency is once per ndays
# bussinessDays is number of business days from the startD to expiryT

def delta_cashflow(df, vol, option_input, rehedge_period = 1, column = 'close'):
    CF = 0.0
    strike = option_input['strike']
    otype = option_input.get('otype', 1)
    expiry = option_input['expiry']
    rd = option_input['rd']
    rf = option_input.get('rf', rd)
    dfunc_name = option_input.get('delta_func', 'bsopt.BSDelta')
    delta_func = eval(dfunc_name)
    nlen = len(df.index)
    for pidx in range(int(nlen/rehedge_period)):
        idx = pidx * rehedge_period
        nxt_idx = min((pidx + 1) * rehedge_period, nlen)
        if nxt_idx >= nlen -1:
            break
        tau = (expiry - df.index[idx]).days/YEARLY_DAYS
        opt_delta = delta_func(otype, df[column][idx], strike, vol, tau, rd, rf)
        CF = CF + opt_delta * (df[column][nxt_idx] - df[column][idx])
    return CF

def realized_vol(df, option_input, calib_input, column = 'close'):
    strike = option_input['strike']
    otype = option_input.get('otype', 1)
    expiry = option_input['expiry']
    rd = option_input['rd']
    rf = option_input.get('rf', rd)
    
    ref_vol = calib_input.get('ref_vol', 0.5)
    opt_payoff = calib_input.get('opt_payoff', 0.0)
    rehedge_period = calib_input.get('rehedge_period', 1)
    fwd = df[column][0]
    is_dtime = calib_input.get('is_dtime', False)
    pricer_func = eval(option_input.get('pricer_func', 'bsopt.BSOpt'))

    if expiry < df.index[-1]:
        raise ValueError, 'Expiry time must be no earlier than the end of the time series'
    numTries = 0
    diff = 1000.0
    start_d = df.index[0]
    if is_dtime:
        start_d = start_d.date()
    tau = (expiry - start_d).days/YEARLY_DAYS
    vol = ref_vol
    def func(x):
        return pricer_func(otype, fwd, strike, x, tau, rd, rf) + delta_cashflow(df, x, option_input, rehedge_period, column) - opt_payoff

    while diff >= SOLVER_ERROR_EPSILON and numTries <= ITERATION_NUM:
        current = func(vol)
        high = func(vol + ITERATION_STEP)
        low = func(vol - ITERATION_STEP)
        if high == low:
            volnext = max(vol -ITERATION_STEP, 1e-2)
        else:
            volnext = vol - 2* ITERATION_STEP * current/(high-low)
            if volnext < 1e-2:
                volnext = vol/2.0

        diff = abs(volnext - vol)
        vol = volnext
        numTries += 1

    if diff >= SOLVER_ERROR_EPSILON or numTries > ITERATION_NUM:
        return None
    else :
        return vol

def bs_delta_to_ratio(delta, vol, texp):
    ys = norm.ppf(delta)
    return math.exp((ys - 0.5 * vol * math.sqrt(texp)) * vol * math.sqrt(texp))

def realized_termstruct(option_input, data):
    is_dtime = data.get('is_dtime', False)
    column = data.get('data_column', 'close')
    xs = data.get('xs', [0.5])
    xs_cols = data.get('xs_names', ['atm'])
    xs_func = data.get('xs_func', 'bs_delta_to_ratio')
    xs_func = eval(xs_func)
    term_tenor = data.get('term_tenor', '-1m')
    df = data['dataframe']
    calib_input = {}
    calib_input['rehedge_period'] = data.get('rehedge_period', 1)
    expiry = option_input['expiry']
    otype = option_input.get('otype', 1)
    ref_vol = option_input.get('ref_vol', 0.5)
    rd = option_input['rd']
    rf = option_input.get('rf', rd)
    end_vol = option_input.get('end_vol', 0.0)
    pricer_func = eval(option_input.get('pricer_func', 'bsopt.BSOpt'))
    if is_dtime:
        datelist = df['date']
        dexp = expiry.date()
    else:
        datelist = df.index
        dexp = expiry
    xdf = df[datelist <= dexp]
    datelist = datelist[datelist <= dexp]    
    end_d  = datelist[-1]
    final_value = 0.0
    vol_ts = pd.DataFrame(columns = xs )
    roll_idx = 0
    while end_d > datelist[0]:
        roll_idx += 1
        start_d = day_shift(end_d, term_tenor)
        sub_df = xdf[(datelist <= end_d) & (datelist > start_d)]
        if len(sub_df) < 2:
            break
        vols = []
        for idx, x in enumerate(xs):
            strike = sub_df[column][0]
            texp = (expiry - start_d).days/YEARLY_DAYS
            if idx > 0:
                strike *= xs_func(xs[idx], vols[0], texp)
            option_input['strike'] = strike
            if end_vol > 0:
                tau = (expiry - end_d).days/YEARLY_DAYS
                final_value = pricer_func(otype, sub_df[column][-1], strike, end_vol, tau, rd, rf)
                ref_vol = end_vol
            elif end_vol == 0:
                if otype:
                    final_value = max((sub_df[column][-1] - strike), 0)
                else:
                    final_value = max((strike - sub_df[column][-1]), 0)
            elif end_vol == None:
                raise ValueError, 'no vol is found to match PnL'
            calib_input['ref_vol'] = ref_vol
            calib_input['opt_payoff'] = final_value
            vol = realized_vol(sub_df, option_input, calib_input, column)
            vols.append(vol)
            end_vol = vol
            end_d = start_d
        tenor_str = str(roll_idx * int(term_tenor[-2])) + term_tenor[-1]
        vol_ts[tenor_str] = vols
    return vol_ts

def hist_realized_vol_by_product(prodcode, start_d, end_d, periods = 12, tenor = '-1m', writeDB = False):
    cont_mth, exch = mysqlaccess.prod_main_cont_exch(prodcode)
    contlist = contract_range(prodcode, exch, cont_mth, start_d, end_d)
    exp_dates = [get_opt_expiry(cont, inst2contmth(cont)) for cont in contlist]
    data = {'is_dtime': False,
            'data_column': 'close',
            'xs': [0.5],
            'xs_names': ['atm'],
            'xs_func': 'bs_delta_to_ratio',
            'rehedge_period': 1,
            'term_tenor': '-1m',
            }
    option_input = {'otype': 1,
                    'rd': 0.0,
                    'rf': 0.0,
                    'end_vol': 0.0,
                    'ref_vol': 0.3,
                    'pricer_func': 'bsopt.BSOpt',
                    'delta_func': 'bsopt.BSDelta',
                    }
    for cont, expiry in zip(contlist, exp_dates):
        p_str = '-' + str(int(tenor[1:-1]) * periods) + tenor[-1]
        d_start = day_shift(expiry, p_str)
        df = mysqlaccess.load_daily_data_to_df('fut_daily', cont, d_start, expiry, database = 'hist_data')
        option_input['expiry'] = expiry
        data['dataframe'] = df
        vol_df = realized_termstruct(option_input, data)
        print vol_df

