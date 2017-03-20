#-*- coding:utf-8 -*-
import Tkinter as tk
import numpy as np
import ttk
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
from matplotlib.figure import Figure
import pyktlib
import instrument
import math
from misc import *
from gui_misc import *

class OptVolgridGui(object):
    def __init__(self, vg, app, master):
        all_insts = app.agent.instruments
        self.root = master
        self.name = vg.name
        self.app = app
        self.option_style = 'EU' if self.name in product_code['CFFEX'] else 'AM'
        if self.option_style == 'EU':
            self.iv_func = pyktlib.BlackImpliedVol
        else:
            self.iv_func = pyktlib.AmericanImpliedVol
        self.iv_steps = 40
        self.iv_tol = 1e-5
        self.expiries = vg.underlier.keys()
        self.expiries.sort()
        self.underliers = [vg.underlier[expiry] for expiry in self.expiries]
        opt_insts = list(set().union(*vg.option_insts.values()))
        self.option_insts = {}
        for inst in opt_insts:
            self.option_insts[inst] = (all_insts[inst].cont_mth, all_insts[inst].otype, all_insts[inst].strike)
        self.spot_model = vg.spot_model
        self.cont_mth = list(set([ all_insts[inst].cont_mth for inst in self.option_insts]))
        self.cont_mth.sort()
        self.strikes = [list(set([ all_insts[inst].strike for inst in vg.option_insts[expiry]])) for expiry in self.expiries]
        for idx in range(len(self.strikes)):
            self.strikes[idx].sort()
        self.opt_dict = {v: k for k, v in self.option_insts.iteritems()}
        self.volgrid = instrument.copy_volgrid(vg)
        self.rf = app.agent.irate.get(vg.ccy, 0.0)

        self.canvas = None
        self.pos_canvas = None
        self.frame = None
        self.pos_frame = None
        self.vm_frame = {}
        self.vm_canvas = {}
        self.vm_figure = {}
        self.vm_ax = {}
        self.vm_lines = {}

        self.otype_selector = {}
        self.strike_selector = {}
        self.calib_inputs = {}
        self.bid_vol = {}
        self.ask_vol = {}
        self.stringvars = {'Insts': {}, 'Volgrid': {}, 'NewVolParam': {}, 'TheoryVol': {}, 'NewVol': {}, 'DiffVol': {}}
        self.new_volnode = {}
        self.curr_insts = {}
        self.entries = {}
        self.option_map = {}
        self.group_risk = {}

        inst_labels = ['Name', 'Price', 'BidPrice', 'BidVol', 'BidIV', 'AskPrice','AskVol','AskIV', 'MidIV', 'TheoryVol', 'Intrinsic', \
                        'Volume', 'OI', 'Updated', 'PV', 'Delta', 'Gamma','Vega', 'Theta', 'RiskPrice', 'RiskUpdated']
        inst_types  = ['string', 'float', 'float', 'int', 'float', 'float', 'int', 'float', 'float', 'float', 'float', \
                        'int', 'int', 'int', 'float', 'float', 'float', 'float', 'float', 'float', 'float']
        for inst in self.option_insts:
            if inst not in self.stringvars:
                self.stringvars[inst] = {}
            for lbl, itype in zip(inst_labels, inst_types):
                self.stringvars[inst][lbl] = get_type_var(itype)
        under_labels = ['Name', 'Price','BidPrice','BidVol','AskPrice','AskVol','UpLimit','DownLimit', 'Volume', 'OI', 'Updated']
        under_types = ['string', 'float', 'float', 'int', 'float', 'int', 'float', 'float',  'int', 'int', 'int']
        for inst in list(set(self.underliers)):
            if inst not in self.stringvars:
                self.stringvars[inst] = {}
            for ulbl, utype in zip(under_labels, under_types):
                self.stringvars[inst][ulbl] = get_type_var(utype)
        vol_labels = ['Expiry', 'Under', 'Df', 'Fwd', 'Atm', 'V90', 'V75', 'V25', 'V10', 'T2expiry', 'Updated' ]
        vol_types =  ['string', 'string', 'float', 'float', 'float', 'float', 'float', 'float', 'float', 'float', 'float']
        for strikes, expiry in zip(self.strikes, self.expiries):
            self.stringvars['Volgrid'][expiry] = {}
            self.stringvars['NewVolParam'][expiry] = {}
            self.stringvars['TheoryVol'][expiry] = {}
            self.stringvars['NewVol'][expiry] = {}
            self.stringvars['DiffVol'][expiry] = {}
            self.otype_selector[expiry] = {}
            self.strike_selector[expiry] = {}
            self.bid_vol[expiry] = [0.05] * len(strikes)
            self.ask_vol[expiry] = [0.50] * len(strikes)
            self.calib_inputs[expiry] = {'strike': [], 'vol': []}
            vn = self.volgrid.volnode[expiry]
            self.new_volnode[expiry] = pyktlib.Delta5VolNode(vn.expiry_(), vn.fwd_(), vn.atmVol_(), vn.d90Vol_(), vn.d75Vol_(), vn.d25Vol_(), vn.d10Vol_(), vn.accrual_())
            for vlbl, vtype in zip(vol_labels, vol_types):
                self.stringvars['Volgrid'][expiry][vlbl] = get_type_var(vtype)
            for vlbl in ['Atm', 'V90', 'V75', 'V25', 'V10']:
                val = self.stringvars['Volgrid'][expiry][vlbl].get()
                self.stringvars['NewVolParam'][expiry][vlbl] = get_type_var('float')
                self.stringvars['NewVolParam'][expiry][vlbl].set(keepdigit(val,4))
            fwd = vn.fwd_()
            for strike in strikes:
                self.otype_selector[expiry][strike] = tk.BooleanVar()
                self.strike_selector[expiry][strike] = tk.BooleanVar()
                if fwd < strike:
                    self.otype_selector[expiry][strike].set(True)
                    self.strike_selector[expiry][strike].set(True)
                else:
                    self.otype_selector[expiry][strike].set(False)
                    self.strike_selector[expiry][strike].set(True)
                iv = self.volgrid.volnode[expiry].GetVolByStrike(strike)
                self.stringvars['TheoryVol'][expiry][strike] = get_type_var('float')
                self.stringvars['TheoryVol'][expiry][strike].set(keepdigit(iv, 4))
                self.stringvars['NewVol'][expiry][strike] = get_type_var('float')
                self.stringvars['NewVol'][expiry][strike].set(keepdigit(iv, 4))
                self.stringvars['DiffVol'][expiry][strike] = get_type_var('float')
                self.stringvars['DiffVol'][expiry][strike].set(0.0)

    def get_T_table(self, expiry):
        # update all the related instrument prices
        under = self.volgrid.underlier[expiry]
        insts = [under] + self.volgrid.option_insts[expiry]
        params = self.app.get_agent_params(['.'.join(['Insts'] + insts)])
        for inst in params['Insts']:
            self.curr_insts[inst] = params['Insts'][inst]
        inst_labels = ['Name', 'Price','BidPrice', 'BidVol','AskPrice', 'AskVol', 'Volume', 'OI', 'Updated', \
                        'PV', 'Delta', 'Gamma','Vega', 'Theta', 'RiskPrice', 'RiskUpdated']
        under_labels = ['Name', 'Price','BidPrice','BidVol','AskPrice','AskVol', 'Volume', 'OI', 'Updated', 'UpLimit','DownLimit']
        for instlbl in under_labels:
            value = self.curr_insts[under][instlbl]
            self.stringvars[under][instlbl].set(keepdigit(value,4))
        for inst in self.volgrid.option_insts[expiry]:
            for instlbl in inst_labels:
                value = self.curr_insts[inst][instlbl]
                self.stringvars[inst][instlbl].set(keepdigit(value,4))
        # update the volgrid info
        vol_labels = ['Expiry', 'Under', 'Df', 'Fwd', 'Atm', 'V90', 'V75', 'V25', 'V10', 'T2expiry', 'Updated']
        params = self.app.get_agent_params(['Volgrids.'+self.name])
        results = params['Volgrids'][self.name]
        if expiry in self.stringvars['Volgrid']:
            for vlbl in vol_labels:
                if vlbl == 'Expiry':
                    value = expiry
                else:
                    value = results[expiry][vlbl]
                self.stringvars['Volgrid'][expiry][vlbl].set(keepdigit(value,5))
        last_update = results[expiry]['Updated']
        t2expiry = results[expiry]['T2expiry']
        vn = self.volgrid.volnode[expiry]
        vn.setFwd(results[expiry]['Fwd'])
        vn.setTime2Exp((t2expiry-last_update)/BDAYS_PER_YEAR)
        vn.setD90Vol(results[expiry]['V90'])
        vn.setD75Vol(results[expiry]['V75'])
        vn.setD25Vol(results[expiry]['V25'])
        vn.setD10Vol(results[expiry]['V10'])
        vn.setAtm(results[expiry]['Atm'])
        # vn.initialize()
        for inst in self.volgrid.option_insts[expiry]:
            bid_price = self.curr_insts[inst]['BidPrice']
            ask_price = self.curr_insts[inst]['AskPrice']
            key = self.option_insts[inst]
            fwd = ( self.curr_insts[under]['BidPrice'] + self.curr_insts[under]['AskPrice'])/2.0
            strike = key[2]
            otype = key[1]
            Texp =  self.volgrid.volnode[expiry].expiry_()
            intrinsic = max(fwd - strike, 0) if otype in ['c', 'C'] else max(strike-fwd, 0)
            self.stringvars[inst]['BidIV'].set(keepdigit(intrinsic,4))
            self.curr_insts[inst]['Intrinsic'] = intrinsic
            theo_vol = vn.GetVolByStrike(strike)
            self.stringvars[inst]['TheoryVol'].set(keepdigit(theo_vol,4))
            self.curr_insts[inst]['TheoryVol'] = theo_vol
            bid_iv_args = (bid_price, fwd, strike, self.rf, Texp, otype, self.iv_tol)
            ask_iv_args = (ask_price, fwd, strike, self.rf, Texp, otype, self.iv_tol)
            if self.option_style == 'AM':
                bid_iv_args = tuple(list(bid_iv_args) + [self.iv_steps])
                ask_iv_args = tuple(list(ask_iv_args) + [self.iv_steps])
            bvol = self.iv_func(*bid_iv_args) if bid_price > intrinsic else np.nan
            avol = self.iv_func(*ask_iv_args) if ask_price > intrinsic else np.nan
            self.stringvars[inst]['BidIV'].set(keepdigit(bvol,4))
            self.curr_insts[inst]['BidIV'] = bvol            
            self.stringvars[inst]['AskIV'].set(keepdigit(avol,4))
            self.curr_insts[inst]['AskIV'] = avol
            self.stringvars[inst]['MidIV'].set(keepdigit((avol+bvol)/2.0,4))
    
    def update_approx_risks(self):
        insts = list(set().union(self.underliers))
        params = self.app.get_agent_params(['.'.join(['Insts'] + insts)])
        for inst in params['Insts']:
            self.curr_insts[inst] = params['Insts'][inst]
        for expiry in self.expiries:
            under = self.volgrid.underlier[expiry]
            fwd = ( self.curr_insts[under]['BidPrice'] + self.curr_insts[under]['AskPrice'])/2.0
            for inst in self.volgrid.option_insts[expiry]:
                prev_price = self.curr_insts[inst]['RiskPrice']
                diff_price = fwd - prev_price
                new_pv = self.curr_insts[inst]['PV'] + self.curr_insts[inst]['Delta'] * diff_price + \
                         self.curr_insts[inst]['Gamma'] * diff_price * diff_price/2.0
                self.stringvars[inst]['PV'].set(keepdigit(new_pv,4))
                self.curr_insts[inst]['PV'] = new_pv
                new_delta = self.curr_insts[inst]['Delta'] + self.curr_insts[inst]['Gamma'] * diff_price
                self.stringvars[inst]['Delta'].set(keepdigit(new_delta,4))
                self.curr_insts[inst]['Delta'] = new_delta

    def vol_marker(self, expiry):
        vol_labels = ['Expiry', 'Under', 'Df', 'Fwd', 'Atm', 'V90', 'V75', 'V25', 'V10','Updated']
        vol_params = ['Atm', 'V90', 'V75', 'V25', 'V10']
        vol_types =  ['string', 'string', 'float','float','float','float','float','float','float','float']        
        self.vm_frame = tk.Toplevel(self.frame)
        # self.vm_canvas = tk.Canvas(vw_win)
        row_id = col_id = 0
        for idx, vlbl in enumerate(vol_labels):
            ttk.Label(self.vm_frame, text=vlbl).grid(row=row_id, column=idx)
            ttk.Label(self.vm_frame, textvariable = self.stringvars['Volgrid'][expiry][vlbl]).grid(row=row_id+1, column=idx)
            if vlbl in vol_params:
                ttk.Entry(self.vm_frame, width = 7, textvariable = self.stringvars['NewVolParam'][expiry][vlbl]).grid(row=row_id+2, column=idx)
        tk.Button(self.vm_frame, text='Plot', command=lambda: self.refresh_vm_figure(expiry) ).grid(row=row_id+2, column=0)
        tk.Button(self.vm_frame, text='Fit', command=lambda: self.fit_volparam(expiry)).grid(row=row_id + 2, column=1)
        tk.Button(self.vm_frame, text='Mark', command=lambda: self.remark_volgrid(expiry)).grid(row=row_id+2, column=2)
        row_id += 3
        fields = ['Strike', 'C-BidIV', 'C-MidIV', 'C-AskIV', 'P-BidIV', 'P-MidIV', 'P-AskIV', 'UseCall', 'UseCalib','TheoryVol', 'NewVol', 'DiffVol']
        for idx, f in enumerate(fields):
            ttk.Label(self.vm_frame, text = f).grid(row=row_id, column=idx)
        row_id += 1
        ix = self.expiries.index(expiry)
        cont_mth = self.cont_mth[ix]
        for idy, strike in enumerate(self.strikes[ix]):
            ttk.Label(self.vm_frame, text = str(strike)).grid(row=row_id+idy, column=0)
            idx = 0
            for otype in ['C', 'P']:                
                for vlbl in ['BidIV', 'MidIV', 'AskIV']:
                    inst_key = (cont_mth, otype, strike)
                    op_inst = self.opt_dict[inst_key]                
                    idx += 1
                    ttk.Label(self.vm_frame, textvariable = self.stringvars[op_inst][vlbl]).grid(row=row_id+idy, column=idx)
            idx += 1
            ttk.Checkbutton(self.vm_frame, variable = self.otype_selector[expiry][strike], \
                                            onvalue = True, offvalue = False).grid(row=row_id+idy, column = idx)
            idx += 1
            ttk.Checkbutton(self.vm_frame, variable = self.strike_selector[expiry][strike], \
                                            onvalue = True, offvalue = False).grid(row=row_id+idy, column = idx)
            idx += 1
            ttk.Label(self.vm_frame, textvariable = self.stringvars['TheoryVol'][expiry][strike]).grid(row=row_id+idy, column = idx)
            idx += 1
            ttk.Entry(self.vm_frame, width = 7, textvariable = self.stringvars['NewVol'][expiry][strike]).grid(row=row_id+idy, column=idx)
            idx += 1
            ttk.Label(self.vm_frame, textvariable = self.stringvars['DiffVol'][expiry][strike]).grid(row=row_id+idy, column = idx)
        row_id += len(self.strikes[ix])
        self.vm_figure = Figure(figsize=(8,8))
        self.vm_ax = self.vm_figure.add_subplot(111)
        for field, lstyle in zip(['TheoryVol', 'NewVol'], ['b-', 'r-']):
            xdata, ydata = self.get_stringvar_field(expiry, field)
            self.vm_lines[field], = self.vm_ax.plot(xdata, ydata, lstyle)
        stk_list, bid_list, ask_list = self.get_fig_volcurve(expiry, )
        self.vm_lines['BidVol'], = self.vm_ax.plot(stk_list, bid_list, '^')
        self.vm_lines['AskVol'], = self.vm_ax.plot(stk_list, ask_list, 'v')
        self.vm_canvas = FigureCanvasTkAgg(self.vm_figure, master=self.vm_frame)
        self.vm_canvas.show()
        self.vm_canvas.get_tk_widget().grid(column=1, row=row_id, rowspan=1, columnspan = 10, sticky="nesw")
        #self.vm_toolbar = NavigationToolbar2TkAgg(self.vm_canvas, self.vm_frame)
        #self.vm_toolbar.grid(row = 1, sticky = tk.W)
        #self.vm_toolbar.update()

    def get_fig_volcurve(self, expiry):
        idx = self.expiries.index(expiry)
        stk_list = []
        bid_list = []
        ask_list = []
        cont_mth = self.cont_mth[idx]
        for strike in self.strikes[idx]:
            if self.strike_selector[expiry][strike]:
                stk_list.append(strike)
                if self.otype_selector[expiry][strike]:
                    key = (cont_mth,  'C', strike)
                else:
                    key = (cont_mth, 'P', strike)
                inst = self.opt_dict[key]
                bid_list.append(self.stringvars[inst]['BidIV'].get())
                ask_list.append(self.stringvars[inst]['AskIV'].get())
        return stk_list, bid_list, ask_list

    def get_stringvar_field(self, expiry, field, selector = None):
        idx = self.expiries.index(expiry)
        if selector == None:
            selector = [True] * len(self.strikes[idx])
        else:
            selector = [selector[expiry][strike] for strike in self.strikes[idx]]
        ydata = [ self.stringvars[field][expiry][strike].get() \
                 for strike, flag in zip(self.strikes[idx], selector) if flag ]
        xdata = [ strike for strike, flag in zip(self.strikes[idx], selector) if flag ]
        return xdata, ydata

    def refresh_vm_figure(self, expiry):
        new_vn = self.new_volnode[expiry]
        vn = self.volgrid.volnode[expiry]
        for vlbl, func in zip(['V90', 'V75', 'V25', 'V10', 'Atm'], \
                        ['setD90Vol', 'setD75Vol', 'setD25Vol', 'setD10Vol', 'setAtm']):
            val = self.stringvars['NewVolParam'][expiry][vlbl].get()
            getattr(new_vn, func)(val)
        idx = self.expiries.index(expiry)
        for strike in self.strikes[idx]:
            theo_vol = vn.GetVolByStrike(strike)
            new_vol = new_vn.GetVolByStrike(strike)
            self.stringvars['TheoryVol'][expiry][strike].set(keepdigit(theo_vol, 4))
            self.stringvars['NewVol'][expiry][strike].set(keepdigit(new_vol, 4))
            self.stringvars['DiffVol'][expiry][strike].set(keepdigit(new_vol - theo_vol, 4))
        for field in ['TheoryVol', 'NewVol']:
            xdata, ydata = self.get_stringvar_field(expiry, field)
            self.vm_lines[field].set_xdata(xdata)
            self.vm_lines[field].set_ydata(ydata)
        stk_list, bid_list, ask_list = self.get_fig_volcurve(expiry)
        for field, ylist in zip(['BidVol', 'AskVol'], [bid_list, ask_list]):
            self.vm_lines[field].set_xdata(stk_list)
            self.vm_lines[field].set_ydata(ylist)

    def fit_volparam(self, expiry):
        under = self.volgrid.underlier[expiry]
        fwd = (self.curr_insts[under]['BidPrice'] + self.curr_insts[under]['AskPrice']) / 2.0
        tick_id = self.curr_insts[under]['Updated']
        idx = self.expiries.index(expiry)
        strike_list = []
        vol_list = []
        for strike in self.strikes[idx]:
            if self.strike_selector[expiry][strike]:
                strike_list.append(strike)
                vol_list.append(self.stringvars['NewVol'][expiry][strike].get())
        params = (self.name, expiry, fwd, strike_list, vol_list, tick_id)
        vol_params = self.app.run_agent_func('fit_volgrid', params)
        for val, vlbl in zip(vol_params, ['Atm', 'V90', 'V75', 'V25', 'V10']):
            self.stringvars['NewVolParam'][expiry][vlbl].set(keepdigit(val, 4))
        new_vn = self.new_volnode[expiry]
        new_vn.setFwd(fwd)
        new_vn.setAtm(vol_params[0])
        new_vn.setD90Vol(vol_params[1])
        new_vn.setD75Vol(vol_params[2])
        new_vn.setD25Vol(vol_params[3])
        new_vn.setD10Vol(vol_params[4])

    def remark_volgrid(self, expiry):
        vol_labels = ['Atm', 'V90', 'V75', 'V25', 'V10']
        vol_params = []
        for vlbl in vol_labels:
            vol_params.append(self.stringvars['NewVolParam'][expiry][vlbl].get())
        under = self.volgrid.underlier[expiry]
        fwd = (self.curr_insts[under]['BidPrice'] + self.curr_insts[under]['AskPrice'])/2.0
        tick_id = self.curr_insts[under]['Updated']
        param = (self.name, expiry, fwd, vol_params, tick_id)
        self.app.run_agent_func('set_volgrids', param)

    def recalc_risks(self, expiry):        
        params = (self.name, expiry, True)
        self.app.run_agent_func('calc_volgrid', params)

    def show_risks(self):
        pos_win   = tk.Toplevel(self.frame)        
        self.pos_frame = tk.Frame(pos_win)
        pos_vsby = tk.Scrollbar(pos_win, orient="vertical", command=self.pos_canvas.yview)
        pos_vsbx = tk.Scrollbar(pos_win, orient="horizontal", command=self.pos_canvas.xview)
        self.pos_canvas.configure(yscrollcommand=pos_vsby.set, xscrollcommand=pos_vsbx.set)
        pos_vsbx.pack(side="bottom", fill="x")
        pos_vsby.pack(side="right", fill="y")
        self.pos_canvas.pack(side="left", fill="both", expand=True)
        self.pos_canvas.create_window((4,4), window=self.pos_frame, anchor="nw", tags="self.pos_frame")
        self.pos_frame.bind("<Configure>", self.OnPosFrameConfigure)
        fields = ['Name', 'Underlying', 'Contract', 'Otype', 'Stike', 'Price', 'BidPrice', 'BidIV', 'AskPrice', 'AskIV', 'PV', 'Delta','Gamma','Vega', 'Theta']
        for idx, field in enumerate(fields):
            tk.Label(self.pos_frame, text = field).grid(row=0, column=idx)
        idy = 0
        for i, cmth in enumerate(self.cont_mth):
            for strike in self.strikes[i]:
                for otype in ['C','P']:
                    key = (cmth, otype, strike)
                    if key in self.opt_dict:
                        idy += 1
                        inst = self.opt_dict[key]
                        for idx, field in enumerate(fields):
                            if idx == 0:
                                txt = inst
                            elif idx == 1:
                                txt = self.underliers[i]
                            elif idx in [2, 3, 4]: 
                                txt = key[idx-2]
                            else:
                                factor = 1
                                if field in ['delta', 'gamma', 'BidIV', 'AskIV']: 
                                    factor = 100
                                txt = self.curr_insts[inst][field]*factor
                            tk.Label(self.pos_frame, text = keepdigit(txt,3)).grid(row=idy, column=idx)
        
    def load_volgrids(self):
        self.app.run_agent_func('load_volgrids', ())
    
    def save_volgrids(self):
        self.app.run_agent_func('save_volgrids', ())
        
    def OnPosFrameConfigure(self, event):
        '''Reset the scroll region to encompass the inner frame'''
        self.pos_canvas.configure(scrollregion=self.pos_canvas.bbox("all"))
    
    def set_frame(self, root):
        self.canvas = tk.Canvas(root)
        self.frame = tk.Frame(self.canvas)
        self.vsby = tk.Scrollbar(root, orient="vertical", command=self.canvas.yview)
        self.vsbx = tk.Scrollbar(root, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.vsby.set, xscrollcommand=self.vsbx.set)
        self.vsbx.pack(side="bottom", fill="x")
        self.vsby.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.create_window((4,4), window=self.frame, anchor="nw", tags="self.frame")
        self.frame.bind("<Configure>", self.OnFrameConfigure)
        self.populate()

    def populate(self):
        vol_labels = ['Expiry', 'Under', 'Df', 'Fwd', 'Atm', 'V90', 'V75', 'V25', 'V10','Updated']
        vol_types =  ['string', 'string', 'float','float','float','float','float','float','float','float']
        inst_labels = ['Name', 'Price', 'BidPrice', 'BidVol', 'BidIV', 'AskPrice','AskVol','AskIV', 'Volume', 'OI']
        under_labels = ['Name', 'Price','BidPrice','BidVol','AskPrice','AskVol','UpLimit','DownLimit', 'Volume', 'OI']
        row_id = 0
        col_id = 0
        for under_id, (expiry, strikes, cont_mth, under) in enumerate(zip(self.expiries, self.strikes, self.cont_mth, self.underliers)):
            col_id = 0
            for idx, vlbl in enumerate(vol_labels):
                tk.Label(self.frame, text=vlbl).grid(row=row_id, column=col_id + idx)
                tk.Label(self.frame, textvariable = self.stringvars['Volgrid'][expiry][vlbl]).grid(row=row_id+1, column=col_id + idx)
                
            ttk.Button(self.frame, text='Refresh', command= lambda: self.get_T_table(expiry)).grid(row=row_id, column=10, columnspan=2)
            ttk.Button(self.frame, text='CalcRisk', command= lambda: self.recalc_risks(expiry)).grid(row=row_id+1, column=10, columnspan=2) 
            ttk.Button(self.frame, text='MarkVol', command= lambda: self.vol_marker(expiry)).grid(row=row_id, column=12, columnspan=2)
            ttk.Button(self.frame, text='ApproxRisk', command= self.update_approx_risks).grid(row=row_id+1, column=12, columnspan=2)
            ttk.Button(self.frame, text='Load', command= self.load_volgrids).grid(row=row_id+2, column=10, columnspan=2)
            ttk.Button(self.frame, text='Save', command= self.save_volgrids).grid(row=row_id+2, column=12, columnspan=2)
            row_id += 2
            col_id = 0
            inst = self.underliers[under_id]
            for idx, ulbl in enumerate(under_labels):
                tk.Label(self.frame, text=ulbl).grid(row=row_id, column=col_id + idx)
                tk.Label(self.frame, textvariable = self.stringvars[inst][ulbl]).grid(row=row_id+1, column=col_id + idx)
            row_id += 2
            col_id = 0
            for idx, instlbl in enumerate(inst_labels + ['strike']):
                tk.Label(self.frame, text=instlbl).grid(row=row_id, column=col_id+idx)
                if instlbl != 'strike':
                    tk.Label(self.frame, text=instlbl).grid(row=row_id, column=col_id+2*len(inst_labels)-idx)
                for idy, strike in enumerate(strikes):
                    if instlbl == 'strike':
                        tk.Label(self.frame, text = str(strike), padx=10).grid(row=row_id+1+idy, column=col_id+idx)
                    else:
                        key1 = (cont_mth, 'C', strike)
                        if key1 in self.opt_dict:
                            inst1 = self.opt_dict[key1]
                            tk.Label(self.frame, textvariable = self.stringvars[inst1][instlbl], padx=10).grid(row=row_id+1+idy, column=col_id + idx)

                        key2 = (cont_mth, 'P', strike)
                        if key1 in self.opt_dict:
                            inst2 = self.opt_dict[key2]                            
                            tk.Label(self.frame, textvariable = self.stringvars[inst2][instlbl], padx=10).grid(row=row_id+1+idy, column=col_id+2*len(inst_labels)-idx)
            row_id = row_id + len(strikes) + 2
            self.get_T_table(expiry)

    def OnFrameConfigure(self, event):
        '''Reset the scroll region to encompass the inner frame'''
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
