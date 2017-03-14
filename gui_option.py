#-*- coding:utf-8 -*-
import Tkinter as tk
import numpy as np
import ttk
import pyktlib
import instrument
import math
from misc import *
from gui_agent import *

class OptVolgridGui(object):
    def __init__(self, vg, app, master):
        all_insts = app.agent.instruments
        self.root = master
        self.name = vg.name
        self.app = app
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
        self.canvas = None
        self.pos_canvas = None
        self.frame = None
        self.pos_frame = None

        #vol_labels = ['Expiry', 'Under', 'Df', 'Fwd', 'Atm', 'V90', 'V75', 'V25', 'V10', 'Updated']
        self.volgrid = instrument.copy_volgrid(vg)
        self.curr_insts = {}
        self.rf = app.agent.irate.get(vg.ccy, 0.0)
        self.entries = {}
        self.option_map = {}
        self.group_risk = {}
        self.stringvars = {'Insts':{}, 'Volgrid':{}}
        self.entry_fields = []
        self.status_fields = [] 
        self.field_types = {}
        inst_labels = ['Name', 'Price', 'BidPrice', 'BidVol', 'BidIV', 'AskPrice','AskVol','AskIV', 'TheoryVol', 'Intrinsic', \
                        'Volume', 'OI', 'Updated', 'PV', 'Delta', 'Gamma','Vega', 'Theta', 'RiskPrice', 'RiskUpdated']
        inst_types  = ['string', 'float', 'float', 'int', 'float', 'float', 'int', 'float', 'float', 'float', \
                        'int', 'int', 'int', 'float', 'float', 'float', 'float', 'float', 'float', 'float']
        for inst in self.option_insts:
            if inst not in self.root.stringvars:
                self.root.stringvars[inst] = {}
            for lbl, itype in zip(inst_labels, inst_types):
                self.root.stringvars[inst][lbl] = get_type_var(itype)                
        under_labels = ['Name', 'Price','BidPrice','BidVol','AskPrice','AskVol','UpLimit','DownLimit', 'Volume', 'OI', 'Updated']
        under_types = ['string', 'float', 'float', 'int', 'float', 'int', 'float', 'float',  'int', 'int', 'int']
        for inst in list(set(self.underliers)):
            if inst not in self.root.stringvars:
                self.root.stringvars[inst] = {}
            for ulbl, utype in zip(under_labels, under_types):
                self.root.stringvars[inst][ulbl] = get_type_var(utype)                 
        vol_labels = ['Expiry', 'Under', 'Df', 'Fwd', 'Atm', 'V90', 'V75', 'V25', 'V10', 'T2Expiry', 'LastUpdate' ]
        vol_types =  ['string', 'string', 'float', 'float', 'float', 'float', 'float', 'float', 'float', 'float', 'float']
        for expiry in self.expiries:
            self.stringvars['Volgrid'][expiry] = {}
            for vlbl, vtype in zip(vol_labels, vol_types):
                self.stringvars['Volgrid'][expiry][vlbl] = get_type_var(vtype)
                       
    def get_T_table(self, expiry):
        under = self.volgrid.underlier[expiry]
        insts = [under] + self.volgrid.option_insts[expiry]
        params = self.app.get_agent_params('.'.join(['Insts'] + insts))
        for inst in params['Insts']:
            self.curr_insts[inst] = params['Insts'][inst]
        inst_labels = ['Name', 'Price','BidPrice', 'BidVol','AskPrice', 'AskVol', 'Volume', 'OI', 'Updated', \
                        'PV', 'Delta', 'Gamma','Vega', 'Theta', 'RiskPrice', 'RiskUpdated']
        under_labels = ['Name', 'Price','BidPrice','BidVol','AskPrice','AskVol', 'Volume', 'OI', 'Updated', 'UpLimit','DownLimit']
        for instlbl in under_labels:
            value = self.curr_insts[under][instlbl]
            self.root.stringvars[under][instlbl].set(keepdigit(value,4))
        for inst in self.volgrid.option_insts[expiry]:
            for instlbl in inst_labels:
                value = self.curr_insts[inst][instlbl]
                self.root.stringvars[inst][instlbl].set(keepdigit(value,4))
        vol_labels = ['Expiry', 'Under', 'Df', 'Fwd', 'Atm', 'V90', 'V75', 'V25', 'V10', 'T2expiry', 'LastUpdated']
        params = self.app.get_agent_params(['Volgrids.'+self.name])
        results = params['Volgrids'][self.name]
        if expiry in self.stringvars['Volgrid']:
            for vlbl in vol_labels:
                value = results[expiry][vlbl]
                self.stringvars['Volgrid'][expiry][vlbl].set(keepdigit(value,5))
        last_update = results[expiry]['LastUpdate']
        t2expiry = results[expiry]['T2expiry']
        vn = self.volgrid.volnode[expiry]
        vn.setFwd(results[expiry]['Fwd'])
        vn.setTime2Expiry((t2expiry-last_update)/BDAYS_PER_YEAR)
        vn.setAtm(results[expiry]['Atm'])
        vn.setD90Vol(results[expiry]['V90'])
        vn.setD75Vol(results[expiry]['V75'])
        vn.setD25Vol(results[expiry]['V25'])
        vn.setD10Vol(results[expiry]['V10'])
        vn.initialize()
        for inst in self.volgrid.option_insts[expiry]:
            bid_price = self.curr_insts[inst]['BidPrice']
            ask_price = self.curr_insts[inst]['AskPrice']
            key = self.option_insts[inst]
            fwd = ( self.curr_insts[under]['BidPrice'] + self.curr_insts[under]['AskPrice'])/2.0
            strike = key[2]
            otype = key[1]
            Texp =  self.volgrid.volnode[expiry].expiry_()
            intrinsic = max(fwd - strike, 0) if otype in ['c', 'C'] else max(strike-fwd, 0)
            self.root.stringvars[inst]['BidIV'].set(keepdigit(intrinsic,4))
            self.curr_insts[inst]['Intrinsic'] = intrinsic
            theo_vol = vn.GetVolByStrike(strike)
            self.root.stringvars[inst]['TheoryVol'].set(keepdigit(theo_vol,4))
            self.curr_insts[inst]['TheoryVol'] = theo_vol
            bvol = pyktlib.BlackImpliedVol(bid_price, fwd, strike, self.rf, Texp, otype) if bid_price > intrinsic else np.nan
            avol = pyktlib.BlackImpliedVol(ask_price, fwd, strike, self.rf, Texp, otype) if ask_price > intrinsic else np.nan            
            self.root.stringvars[inst]['BidIV'].set(keepdigit(bvol,4))
            self.curr_insts[inst]['BidIV'] = bvol            
            self.root.stringvars[inst]['AskIV'].set(keepdigit(avol,4))
            self.curr_insts[inst]['AskIV'] = avol
    
    def update_approx_risks(self):
        insts = list(set().union(self.underliers))
        params = self.app.get_agent_params('.'.join(['Insts'] + insts))
        for expiry in self.expiries:
            under = self.volgrid.underlier[expiry]
            fwd = ( self.curr_insts[under]['BidPrice'] + self.curr_insts[under]['AskPrice'])/2.0
            for inst in self.volgrid.option_insts[expiry]:
                prev_price = self.curr_insts[inst]['RiskPrice']
                diff_price = fwd - prev_price
                new_pv = self.curr_insts[inst]['PV'] + self.curr_insts[inst]['Delta'] * diff_price + \
                         self.curr_insts[inst]['Gamma'] * diff_price * diff_price/2.0
                self.root.stringvars[inst]['PV'].set(keepdigit(new_pv,4))
                self.curr_insts[inst]['PV'] = new_pv
                new_delta = self.curr_insts[inst]['Delta'] + self.curr_insts[inst]['Gamma'] * diff_price
                self.root.stringvars[inst]['Delta'].set(keepdigit(new_delta,4))
                self.curr_insts[inst]['Delta'] = new_delta
        
    def calib_volgrids(self, expiry):
        vol_labels = ['Expiry', 'Under', 'Df', 'Fwd', 'Atm', 'V90', 'V75', 'V25', 'V10','Updated']
        vol_types =  ['string', 'string', 'float','float','float','float','float','float','float','float']
        pos_win   = tk.Toplevel(self.frame)
        row_id = col_id = 0
        for idx, vlbl in enumerate(vol_labels):
            tk.Label(self.frame, text=vlbl).grid(row=row_id, column=col_id + idx)
            tk.Label(self.frame, textvariable = self.stringvars['Volgrid'][expiry][vlbl]).grid(row=row_id+1, column=col_id + idx)
    
    def recalc_risks(self, expiry):        
        params = (self.name, expiry, True)
        self.app.run_agent_func('calc_volgrid', params)

    def show_risks(self):
        pos_win   = tk.Toplevel(self.frame)
        self.pos_canvas = tk.Canvas(pos_win)
        self.pos_frame = tk.Frame(self.pos_canvas)
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
            ttk.Button(self.frame, text='ApproxRisk', command= self.approx_risks).grid(row=row_id+1, column=12, columnspan=2)
            ttk.Button(self.frame, text='CalibVol', command= lambda: self.calib_volgrids(expiry)).grid(row=row_id, column=12, columnspan=2)
            row_id += 2
            col_id = 0
            inst = self.underliers[under_id]
            for idx, ulbl in enumerate(under_labels):
                tk.Label(self.frame, text=ulbl).grid(row=row_id, column=col_id + idx)
                tk.Label(self.frame, textvariable = self.root.stringvars[inst][ulbl]).grid(row=row_id+1, column=col_id + idx)              
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
                            tk.Label(self.frame, textvariable = self.root.stringvars[inst1][instlbl], padx=10).grid(row=row_id+1+idy, column=col_id + idx)

                        key2 = (cont_mth, 'P', strike)
                        if key1 in self.opt_dict:
                            inst2 = self.opt_dict[key2]                            
                            tk.Label(self.frame, textvariable = self.root.stringvars[inst2][instlbl], padx=10).grid(row=row_id+1+idy, column=col_id+2*len(inst_labels)-idx)
            row_id = row_id + len(strikes) + 2
            self.get_T_table(expiry)

    def OnFrameConfigure(self, event):
        '''Reset the scroll region to encompass the inner frame'''
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
