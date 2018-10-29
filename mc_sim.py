import numpy as np
import pandas as pd
import datetime
import scipy
import bsopt

def LogNormalPaths(mu, cov, fwd, numPaths):
    ''' mu and fwd are 1d lists/arrays (1xn); cov is a 2d scipy.array (nxn); numPaths is int '''
    return (fwd*scipy.exp(np.random.multivariate_normal(mu, cov, numPaths) - 0.5*cov.diagonal())).transpose()

def generate_1f_path(fwds, vols, exp_dates, num_steps, num_paths, \
                     start_date=0, end_date = 365.0, \
                     a = 1, b = 0, accr = 365.0):
    dt = (end_date - start_date)/accr/num_steps
    rv = np.random.multivariate_normal(np.zeros(num_steps), np.eye(num_steps), num_paths)
    fwd_path = [ list() for i in range(len(fwds))]
    for idy in range(num_steps):
        curr_date = start_date + (end_date - start_date) /num_steps * (idy+1)
        for idx, (f, v, dexp) in enumerate(zip(fwds, vols, exp_dates)):
            if idy == 0:
                fwd_path[idx].append(np.ones(num_paths) * f)
            prev_f = fwd_path[idx][-1]
            if dexp > curr_date:
                inst_vol = v
                curr_f = prev_f * np.exp( -(inst_vol**2) * dt/2.0 + rv[:, idy] * np.sqrt(dt) * inst_vol)
            else:
                curr_f = prev_f
            fwd_path[idx].append(curr_f)
    return np.dstack(fwd_path)

def calc_port_values(fwd_path, fwds, vols, exp_dates, start_date=0, end_date = 365.0,  \
                     opt_strikes = [63.5, 45.0], a = 1, b = 0, ir = 0.02, accr = 365.0):
    num_steps, num_paths, num_fwds = fwd_path.shape
    opt_values = []
    num_opt = len(opt_strikes)
    for i in range(num_opt):
        opt_values.append(np.zeros(fwd_path.shape))
    for step in range(num_steps):
        curr_date = start_date + (end_date - start_date) /num_steps * step
        for path in range(num_paths):
            for idx, (f, v, dexp) in enumerate(zip(fwds, vols, exp_dates)):
                for idy, s in enumerate(opt_strikes):
                    uv = v
                    if idy == 0:
                        IsCall = True
                    else:
                        IsCall = False
                        uv+= 0.032
                    if dexp <= curr_date:
                        opt_values[idy][step, path, idx] = 0.0
                    else:
                        opt_values[idy][step, path, idx] = bsopt.BSFwd( IsCall, fwd_path[step, path, idx], s, uv, (dexp - curr_date)/accr, ir)
    return opt_values

def test_run():
    num_paths = 500
    num_steps = 48
    df = pd.read_csv('C:\\dev\\data\\mkt_input.csv')
    fwds = df['fwd'].values
    vols = df['vol'].values
    exp_dates = df['expiry'].values
    start_date = 43362.0
    end_date = float(exp_dates[-1])
    accr = 365.0
    opt_strikes = [66, 51.5]
    opt_weights = [-1.0, 2.0]
    pt_list = [1, 5, 10, 25, 50, 75, 90, 95, 99]
    fwd_path = generate_1f_path(fwds, vols, exp_dates, num_steps, num_paths, \
                                start_date, end_date, a = 1, b = 0, accr = accr)
    opt_vals = calc_port_values(fwd_path, fwds, vols, exp_dates, start_date, end_date, \
                     opt_strikes = opt_strikes, a=1, b=0, ir=0.025, accr=accr)
    num_steps += 1
    port_vals = np.zeros((num_steps, num_paths))

    for step in range(num_steps):
        curr_date = start_date + (end_date - start_date) / num_steps * step
        for path in range(num_paths):
            port_vals[step, path] = sum([ w * sum(opt_val[step, path, :]) for w, opt_val in zip(opt_weights, opt_vals)])
        if step == 0:
            fwd_pct = np.percentile(fwd_path[step,:, -1], pt_list)
            port_pct = np.percentile(port_vals[step,:], [ 100 - p for p in pt_list])
        else:
            fwd_pct = np.append(fwd_pct, np.percentile(fwd_path[step,:, -1], pt_list))
            port_pct = np.append(port_pct, np.percentile(port_vals[step, :], [100 - p for p in pt_list]))

    fwd_pct = np.reshape(fwd_pct, (-1, len(pt_list)))
    port_pct = np.reshape(port_pct, (-1, len(pt_list)))
    df = pd.DataFrame(fwd_pct, columns = ['fwd_' + str(p) for p in pt_list])
    writer = pd.ExcelWriter('C:\\dev\\data\\Tacora_port_180919.xlsx')
    df.to_excel(writer, 'fwd')
    df = pd.DataFrame(port_pct, columns = ['port_' + str(p) for p in pt_list])
    df.to_excel(writer, 'port')
    writer.save()
    return fwd_path, opt_vals, port_vals, fwd_pct, port_pct