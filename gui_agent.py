#-*- coding:utf-8 -*-
import Tkinter as tk
import ttk
import datetime
import re
import math
import json
import pandas as pd
import agent
from gui_option import *
from gui_strat import *

vtype_func_map = {'int':int, 'float':float, 'str': str, 'bool':bool }

def keepdigit(x, p=5):
    out = x
    if isinstance(x, float):
        if x >= 10**p:
            out = int(x)
        elif x>=1:
            n = p + 1 - len(str(int(x)))
            out = int(x*(10**n)+0.5)/float(10**n)
        elif math.isnan(x):
            out = 0
        else:
            out = int(x*10**p+0.5)/1.0/10**p
    return out    

def get_type_var(vtype):
    if vtype == 'int':
        v=tk.IntVar()
    elif vtype == 'float':
        v=tk.DoubleVar()
    else: 
        v=tk.StringVar()
    return v

def type2str(val, vtype):
    ret = val
    if vtype == 'bool':
        ret = '1' if val else '0'
    elif 'list' in vtype:
        ret = ','.join([str(r) for r in val])
    elif vtype == 'date':
        ret = val.strftime('%Y%m%d')
    elif vtype == 'datetime':
        ret = val.strftime('%Y%m%d')
    else:
        ret = str(val)
    return ret

def str2type(val, vtype):
    ret = val
    if vtype == 'str':
        return ret
    elif vtype == 'bool':
        ret = True if int(float(val))>0 else False
    elif 'list' in vtype:
        key = 'float'    
        if len(vtype) > 4:
            key = vtype[:-4]
        func = vtype_func_map[key]
        ret = [func(s) for s in val.split(',')]
    elif vtype == 'date':
        ret = datetime.datetime.strptime(val,'%y%m%d').date()
    elif vtype == 'datetime':
        ret = datetime.datetime.strptime(val,'%y%m%d %H:%M:%S')
    else:
        func = vtype_func_map[vtype]
        ret = func(float(val))
    return ret

def field2variable(name):
    return '_'.join(re.findall('[A-Z][^A-Z]*', name)).lower()

def variable2field(var):
    return ''.join([s.capitalize() for s in var.split('_')])    
    
class Gui(tk.Tk):
    def __init__(self, app = None):
        tk.Tk.__init__(self)       
        self.title(app.name)
        self.app = app
        if app!=None:
            self.app.master = self
        #self.scroll_text = ScrolledText.ScrolledText(self, state='disabled')
        #self.scroll_text.configure(font='TkFixedFont')
        # Create textLogger
        #self.text_handler = TextHandler(self.scroll_text)
        #self.scroll_text.pack()
        self.settings_win = None
        self.status_win = None
        self.pos_frame = None
        self.pos_canvas = None
        self.tp_frame = None
        self.tp_canvas = None
        self.entries = {}
        self.stringvars = {'Insts':{}, 'Account':{}}
        self.status_ents = {}
        self.strat_frame = {}
        self.strat_gui = {}
        self.volgrid_gui = {}
        self.volgrid_frame = {}
        self.account_fields = ['CurrCapital', 'PrevCapital', 'LockedMargin', 'UsedMargin', 'Available', 'PnlTotal']
        self.field_types = {'ScurDay' : 'date',
                            'TickId'  : 'int',
                            'EodFlag' : 'bool',
                            'MarketOrderTickMultiple': 'int', 
                            'CancelProtectPeriod': 'int',
                            'CurrCapital':'float', 
                            'PrevCapital':'float', 
                            'LockedMargin':'float', 
                            'UsedMargin':'float', 
                            'Available':'float', 
                            'PnlTotal':'float',
                            'Initialized': 'bool',
                            'QryInst': 'string',
                            'TotalSubmittedLimit': 'int',
                            'SubmittedLimitPerInst': 'int',
                            'FailedOrderLimit': 'int',
                            'TotalSubmitted': 'int',
                            'TotalCancelled': 'int',
                            }
    
        for strat_name in self.app.agent.strategies:
            strat = self.app.agent.strategies[strat_name]
            if strat.__class__.__name__ in ['DTTrader']:
                self.strat_gui[strat_name] = DTStratGui(strat, app, self)
            elif strat.__class__.__name__ in ['DTSplitDChanFilter']:
                self.strat_gui[strat_name] = DTSplitDChanStratGui(strat, app, self)
            elif strat.__class__.__name__ in ['DTSplitChanAddon']:
                self.strat_gui[strat_name] = DTSplitChanAddonStratGui(strat, app, self)
            elif strat.__class__.__name__ in ['BbandPChanTrader']:
                self.strat_gui[strat_name] = BBandPChanStratGui(strat, app, self)
            elif strat.__class__.__name__ in ['MASystemTrader']:
                self.strat_gui[strat_name] = MASystemStratGui(strat, app, self)
            elif strat.__class__.__name__ in ['AsctrendTrader']:
                self.strat_gui[strat_name] = AsctrendStratGui(strat, app, self)
            elif strat.__class__.__name__ == 'RBreaker':
                self.strat_gui[strat_name] = RBStratGui(strat, app, self)
            elif strat.__class__.__name__ == 'TurtleTrader':
                self.strat_gui[strat_name] = TLStratGui(strat, app, self)
            elif strat.__class__.__name__ == 'OptionArbStrat':
                self.strat_gui[strat_name] = OptionArbStratGui(strat, app, self)
                        
        if ('Option' in app.agent.__class__.__name__) and (len(app.agent.volgrids)>0):
            for prod in app.agent.volgrids:
                self.volgrid_gui[prod] = OptVolgridGui(app.agent.volgrids[prod], app, self)
        self.gateways = self.app.agent.gateways.keys()
        menu = tk.Menu(self)
        toolmenu = tk.Menu(menu, tearoff=0)
        toolmenu.add_command(label = 'MarketViewer', command=self.market_view)
        toolmenu.add_command(label = 'PositionViewer', command=self.position_view)
        toolmenu.add_command(label = 'TradePositionViewer', command=self.tradepos_view)
        menu.add_cascade(label="Tools", menu=toolmenu)
        menu.add_command(label="Reset", command=self.onReset)
        menu.add_command(label="Exit", command=self.onExit)
        self.config(menu=menu)
        self.notebook = ttk.Notebook(self)
        self.settings_win = ttk.Frame(self.notebook)
        self.config_settings()
        self.notebook.add(self.settings_win, text = 'Settings')
        for prod in self.volgrid_gui:
            self.volgrid_frame[prod] = ttk.Frame(self)
            self.volgrid_gui[prod].set_frame(self.volgrid_frame[prod])
            self.notebook.add(self.volgrid_frame[prod], text = 'VG_' + prod)
                    
        for strat_name in self.app.agent.strat_list:
            self.strat_frame[strat_name] = ttk.Frame(self)
            self.strat_gui[strat_name].set_frame(self.strat_frame[strat_name])
            self.notebook.add(self.strat_frame[strat_name], text = strat_name)
        self.notebook.pack(side="top", fill="both", expand=True, padx=10, pady=10)

    def market_view(self):
        pass

    def position_view(self):
        params = self.app.get_agent_params(['Positions'])
        positions = params['Positions']
        pos_win   = tk.Toplevel(self)
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
        
        fields = ['gateway', 'inst', 'currlong', 'currshort', 'locklong', 'lockshort', 'ydaylong', 'ydayshort']
        for idx, field in enumerate(fields):
            row_idx = 0
            tk.Label(self.pos_frame, text = field).grid(row=row_idx, column=idx)
            for gway in positions.keys():
                for inst in positions[gway]:
                    row_idx += 1
                    if field == 'inst':
                        txt = inst
                    elif field == 'gateway':
                        txt = str(gway)
                    else:
                        txt = positions[gway][inst][field]
                    tk.Label(self.pos_frame, text = txt).grid(row=row_idx, column=idx)

    def tradepos_view(self):
        params = self.app.get_agent_params(['Risk.pos'])
        res = params['Risk']
        sum_risk = {}
        sum_risk['total'] = res['total']
        strat_list = res['strats'].keys()
        for strat_name in strat_list:
            sum_risk[strat_name] = res['strats'][strat_name]
        pos_win   = tk.Toplevel(self)
        self.tp_canvas = tk.Canvas(pos_win)
        self.tp_frame = tk.Frame(self.tp_canvas)
        pos_vsby = tk.Scrollbar(pos_win, orient="vertical", command=self.tp_canvas.yview)
        pos_vsbx = tk.Scrollbar(pos_win, orient="horizontal", command=self.tp_canvas.xview)
        self.tp_canvas.configure(yscrollcommand=pos_vsby.set, xscrollcommand=pos_vsbx.set)
        pos_vsbx.pack(side="bottom", fill="x")
        pos_vsby.pack(side="right", fill="y")
        self.tp_canvas.pack(side="left", fill="both", expand=True)
        self.tp_canvas.create_window((4,4), window=self.tp_frame, anchor="nw", tags="self.tp_frame")
        self.tp_frame.bind("<Configure>", self.OnTPFrameConfigure)

        fields = ['inst', 'total'] + strat_list
        for idx, field in enumerate(fields):
            tk.Label(self.tp_frame, text = field).grid(row=0, column=idx)
            for idy, inst in enumerate(sum_risk['total'].keys()):
                if field == 'inst':
                    txt = inst
                else:
                    inst_risk = sum_risk[field].get(inst, {})
                    txt = str(inst_risk.get('pos', 0))
                tk.Label(self.tp_frame, text = txt).grid(row=idy+1, column=idx)

    def OnPosFrameConfigure(self, event):
        '''Reset the scroll region to encompass the inner frame'''
        self.pos_canvas.configure(scrollregion=self.pos_canvas.bbox("all"))

    def OnTPFrameConfigure(self, event):
        '''Reset the scroll region to encompass the inner frame'''
        self.tp_canvas.configure(scrollregion=self.tp_canvas.bbox("all"))

    def qry_agent_inst(self):
        instfield = 'QryInst'
        ent = self.entries[instfield]
        inst = ent.get()
        params = self.app.get_agent_params(['Insts.' + inst])
        inst_fields = ['Price', 'PrevClose', 'Volume', 'OI', 'AskPrice', 'AskVol', 'BidPrice', 'BidVol', 'UpLimit', 'DownLimit']
        for field in inst_fields:
            v = self.stringvars['Insts.'+field]
            v.set(params['Insts'][inst][field])

    def qry_agent_histdata(self):
        instfield = 'QryInst'
        ent = self.entries[instfield]
        inst = ent.get()
        freqfield = 'HistFreq'
        fent = self.entries[freqfield]
        freq = fent.get()
        data = self.app.get_hist_data(inst, freq, nlen = 20)
        if len(data) == 0:
            return
        pos_win = tk.Toplevel(self)
        pos_frame = tk.Frame(pos_win)
        fields = data.dtype.names
        for idx, field in enumerate(fields):
            row_idx = 0
            tk.Label(pos_frame, text=field).grid(row=row_idx, column=idx)
            for i in range(len(data)):
                row_idx += 1
                txt = data[field][i]
                if type(txt).__name__ == "datetime64":
                    if field == "date":
                        txt = pd.to_datetime(str(txt)).strftime("%Y-%m-%d")
                    else:
                        txt = pd.to_datetime(str(txt)).strftime("%Y-%m-%d %H%M%S")
                elif type(txt).__name__ in ['float', 'float64']:
                    txt = round(txt, 2)
                tk.Label(pos_frame, text=txt).grid(row=row_idx, column=idx)
        pos_frame.pack(side="top", fill="both", expand=True, padx=10, pady=10)
        return

    def get_agent_account(self):        
        gway_keys = [ 'Account.' + gway for gway in self.gateways]
        params = self.app.get_agent_params(gway_keys)
        for gway in self.gateways:
            for field in self.account_fields:
                v = self.stringvars['Account'][gway + '.' + field]
                v.set(params['Account'][gway][field])

    def recalc_margin(self, gway):
        params = ()
        self.app.run_gateway_func(gway, 'calc_margin', params)

    def run_eod(self):
        params = ()
        self.app.run_agent_func('run_eod', params)
            
    def config_settings(self):
        entry_fields = []
        label_fields = ['ScurDay', 'TickId', 'EodFlag'] 
        lbl_frame = ttk.Labelframe(self.settings_win)
        row_idx = 0
        for col_idx, field in enumerate(label_fields + entry_fields):
            lab = ttk.Label(lbl_frame, text=field+": ", anchor='w')
            lab.grid(column=col_idx, row=row_idx, sticky="ew")
        col_idx = 0
        row_idx += 1
        for field in label_fields:
            v = tk.IntVar()
            self.stringvars[field] = v
            lab = ttk.Label(lbl_frame, textvariable = v, anchor='w')
            lab.grid(column=col_idx, row=row_idx, sticky="ew")
            col_idx += 1
        for field in entry_fields:
            ent = ttk.Entry(lbl_frame, width=4)
            self.entries[field] = ent
            ent.insert(0,"0")
            ent.grid(column=col_idx, row=row_idx, sticky="ew")
            col_idx += 1
            self.stringvars[field] = v
        row_idx += 1
        #account_fields = ['CurrCapital', 'PrevCapital', 'PnlTotal', 'LockedMargin', 'UsedMargin', 'Available']
        for col_idx, field in enumerate(['gateway'] + self.account_fields):
            lab = ttk.Label(lbl_frame, text=field, anchor='w', width = 9)
            lab.grid(column=col_idx, row=row_idx, sticky="ew")
        col_idx = 0
        row_idx += 1
        for gway in self.gateways:
            lab = ttk.Label(lbl_frame, text=str(gway), anchor='w')
            lab.grid(column = col_idx, row = row_idx, sticky="ew")
            for field in self.account_fields:
                col_idx += 1
                v = tk.DoubleVar()
                key = str(gway) + '.'+ field
                self.stringvars['Account'][key] = v
                lab = ttk.Label(lbl_frame, textvariable = v, anchor='w', width = 7)
                lab.grid(column=col_idx, row=row_idx, sticky="ew")
            row_idx += 1
        agent_fields = entry_fields + label_fields
        setup_qrybtn = ttk.Button(lbl_frame, text='QueryInst', command= self.qry_agent_inst)
        setup_qrybtn.grid(column=0, row=row_idx, sticky="ew")
        setup_histbtn = ttk.Button(lbl_frame, text='QryHist', command= self.qry_agent_histdata)
        setup_histbtn.grid(column=1, row=row_idx, sticky="ew")
        setup_loadbtn = ttk.Button(lbl_frame, text='RunEOD', command= self.run_eod)
        setup_loadbtn.grid(column=2, row=row_idx, sticky="ew")
        setup_setbtn = ttk.Button(lbl_frame, text='SetParam', command= lambda: self.set_agent_params(entry_fields))
        setup_setbtn.grid(column=3, row=row_idx, sticky="ew")
        setup_loadbtn = ttk.Button(lbl_frame, text='LoadParam', command= lambda: self.get_agent_params(agent_fields))
        setup_loadbtn.grid(column=4, row=row_idx, sticky="ew")
        setup_loadbtn = ttk.Button(lbl_frame, text='LoadAccount', command= self.get_agent_account)
        setup_loadbtn.grid(column=5, row=row_idx, sticky="ew")
        col_idx = 6
        for gway in self.gateways:
            setup_loadbtn = ttk.Button(lbl_frame, text='ReCalc_'+gway, command= lambda: self.recalc_margin(gway))
            setup_loadbtn.grid(column=col_idx, row=row_idx, sticky="ew")
            col_idx += 1
        row_idx +=1
        field = 'QryInst'
        lab = ttk.Label(lbl_frame, text= field, anchor='w')
        lab.grid(column=0, row=row_idx, sticky="ew")
        ent = ttk.Entry(lbl_frame, width=4)
        ent.grid(column=0, row=row_idx+1, sticky="ew")
        self.entries[field] = ent
        field = 'HistFreq'
        lab = ttk.Label(lbl_frame, text= field, anchor='w')
        lab.grid(column=1, row=row_idx, sticky="ew")
        freqent = ttk.Entry(lbl_frame, width=4)
        freqent.grid(column=1, row=row_idx+1, sticky="ew")
        self.entries[field] = freqent
        inst_fields = ['Price', 'PrevClose', 'Volume', 'OI', 'AskPrice', 'AskVol', 'BidPrice', 'BidVol', 'UpLimit', 'DownLimit']        
        for idx, field in enumerate(inst_fields):
            lab1 = ttk.Label(lbl_frame, text=field, anchor='w')
            lab1.grid(column=idx+2, row=row_idx, sticky="ew")
            v = tk.DoubleVar()
            lab2 = ttk.Label(lbl_frame, textvariable = v, anchor='w')
            self.stringvars['Insts.' + field] = v
            lab2.grid(column=idx+2, row=row_idx+1, sticky="ew")
        lbl_frame.pack(side="top", fill="both", expand=True, padx=10, pady=10)        
        self.get_agent_params(agent_fields)
        self.get_agent_account()
    
    def set_agent_params(self, fields):
        params = {}
        for field in fields:
            ent = self.entries[field]
            value = ent.get()
            vtype = self.field_types[field]
            params[field] = str2type(value, vtype)
        self.app.set_agent_params(params)
    
    def get_agent_params(self, fields):
        params = self.app.get_agent_params(fields)
        for field in fields:
            vtype = self.field_types[field]
            value = type2str(params[field], vtype)
            if field in self.entries:
                ent = self.entries[field]
                ent.delete(0, tk.END)
                ent.insert(0, value)
            elif field in self.stringvars:
                var = self.stringvars[field]
                var.set(keepdigit(value,4))
        
    def refresh_agent_status(self):
        pass
    
    def make_status_form(self):
        pass
        
    def onStatus(self):
        self.status_win = tk.Toplevel(self)
        self.status_ents = self.make_status_form(self.status_win)
        
    def onReset(self):
        self.app.restart()

    def onExit(self):
        self.app.exit_agent()
        self.destroy()
        
class MainApp(object):
    def __init__(self, name, tday, config_file, agent_class = 'agent.Agent', master = None):
        self.scur_day = tday
        self.name = name
        cls_str = agent_class.split('.')
        config = {}
        with open(config_file, 'r') as infile:
            config = json.load(infile)
        agent_cls = getattr(__import__(str(cls_str[0])), str(cls_str[1]))
        self.agent = agent_cls(name = name, tday = tday, config = config)
        self.master = master
        self.restart()
                        
    def restart(self):
        if self.agent != None:
            self.scur_day = self.agent.scur_day
        self.agent.restart()
    
    def get_agent_params(self, fields):
        res = {}
        for f in fields:
            field_list = f.split('.')
            field = field_list[0]
            if field not in res:
                res[field] = {}
            if field == 'Positions':
                positions = {}
                for gway in self.agent.gateways:
                    gateway = self.agent.gateways[gway]
                    positions[gway] = {}
                for inst in gateway.positions:
                    pos = gateway.positions[inst]
                    positions[gway][inst] = {'currlong' : pos.curr_pos.long,
                                       'currshort': pos.curr_pos.short,
                                       'locklong' : pos.locked_pos.long,
                                       'lockshort': pos.locked_pos.short,
                                       'ydaylong':  pos.pos_yday.long,
                                       'ydayshort': pos.pos_yday.short}
                res[field] = positions
            elif field == 'Risk':
                risk_list = field_list[1:]
                sum_risk, risk_dict = self.agent.risk_by_strats(risk_list)
                res[field] = {'total': sum_risk, 'strats': risk_dict }
            elif field == 'Account':
                gateway = self.agent.gateways[field_list[1]]
                res[field][gateway.gatewayName] = dict([(variable2field(var), gateway.account_info[var]) for var in gateway.account_info])
            elif field ==' Orderstats':
                gateway = self.agent.gateways[field_list[1]]
                res[field][gateway.gatewayName] = dict([(variable2field(var), gateway.order_stats[var]) for var in gateway.order_stats])
            elif field == 'Orders':
                order_list = []
                gateway = self.agent.gateways[field_list[1]]
                for o in gateway.id2order.values():
                    inst = o.position.instrument.name
                    order_list.append([o.order_ref, o.sys_id, inst, o.diretion, o.volume, o.filled_volume,  o.limit_price, o.status])
                res[field][gateway.gatewayName] = order_list
            elif field == 'Trades':
                trade_list = []
                for etrade in self.agent.etrades:
                    insts = ' '.join(etrade.instIDs)
                    volumes = ' '.join([str(i) for i in etrade.volumes])
                    filled_vol = ' '.join([str(i) for i in etrade.filled_vol])
                    filled_price = ' '.join([str(i) for i in etrade.filled_price])
                    trade_list.append([etrade.id, insts, volumes, filled_vol, filled_price, etrade.limit_price, etrade.valid_time,
                                  etrade.strategy, etrade.book, etrade.status])
                res[field] = trade_list
            elif field == 'Insts':
                if len(field_list) > 1:
                    insts = field_list[1:]
                else:
                    insts = self.agent.instruments.keys()
                inst_dict = {}
                for inst in insts:
                    inst_obj = self.agent.instruments[inst]
                    inst_dict[inst] = {'Name': inst, 'Price': inst_obj.price, 
                                 'BidPrice': inst_obj.bid_price1, 'BidVol': inst_obj.bid_vol1, 
                                 'AskPrice': inst_obj.ask_price1, 'AskVol': inst_obj.ask_vol1, 
                                 'PrevClose': inst_obj.prev_close, 'MarginRate': inst_obj.marginrate, 
                                 'Updated': inst_obj.last_update, 'Traded': inst_obj.last_traded,
                                 'UpLimit': inst_obj.up_limit, 'DownLimit': inst_obj.down_limit,
                                 'Volume': inst_obj.volume, 'OI': inst_obj.open_interest }
                    if 'Option' in inst_obj.__class__.__name__:
                        inst_dict[inst]['PV'] = inst_obj.pv
                        inst_dict[inst]['Delta'] = inst_obj.delta
                        inst_dict[inst]['Gamma'] = inst_obj.gamma
                        inst_dict[inst]['Vega']  = inst_obj.vega
                        inst_dict[inst]['Theta'] = inst_obj.theta
                        inst_dict[inst]['Otype'] = inst_obj.otype
                        inst_dict[inst]['Strike'] = inst_obj.strike
                        inst_dict[inst]['Underlying'] = inst_obj.underlying
                        inst_dict[inst]['RiskPrice'] = inst_obj.risk_price
                        inst_dict[inst]['RiskUpdated'] = inst_obj.risk_updated
                res[field] = inst_dict
            elif field == 'Volgrids':
                prod = field_list[1]
                vg_param = {}
                if prod in self.agent.volgrids:
                    vg = self.agent.volgrids[prod]
                    for expiry in vg.volnode:
                        vg_param[expiry] = {}
                        vg_param[expiry]['Fwd'] = vg.fwd[expiry]
                        vg_param[expiry]['LastUpdate'] = vg.last_update[expiry]
                        vg_param[expiry]['T2expiry'] = vg.t2expiry[expiry]
                        vg_param[expiry]['Under'] = vg.underlier[expiry]
                        vg_param[expiry]['Df'] = vg.df[expiry]
                        vol_param = vg.volparam[expiry]
                        vg_param[expiry]['Atm'] = vol_param[0]
                        vg_param[expiry]['V90'] = vol_param[1]
                        vg_param[expiry]['V75'] = vol_param[2]
                        vg_param[expiry]['V25'] = vol_param[3]
                        vg_param[expiry]['V10'] = vol_param[4]
                res[field] = {prod: vg_param}
            else:
                var = field2variable(field)
                res[field] = getattr(self.agent, var)
        return res

    def set_agent_params(self, params):
        for field in params:
            var = field2variable(field)
            value = params[field]
            setattr(self.agent, var, value)

    def set_gateway_params(self, gway, params):
        gateway = self.agent.gateways[gway]
        for field in params:
            var = field2variable(field)
            value = params[field]
            setattr(gateway, var, value)

    def get_strat_params(self, strat_name, fields):
        params = {}
        strat = self.agent.strategies[strat_name]
        for field in fields:
            var = field2variable(field)
            params[field] = getattr(strat, var)
        return params
    
    def set_strat_params(self, strat_name, params):
        strat = self.agent.strategies[strat_name]
        for field in params:
            var = field2variable(field)
            value = params[field]
            setattr(strat, var, value)
    
    def run_strat_func(self, strat_name, func_name):
        strat = self.agent.strategies[strat_name]
        getattr(strat, func_name)()

    def run_agent_func(self, func_name, params):
        getattr(self.agent, func_name)(*params)

    def run_gateway_func(self, gway, func_name, params):
        gateway = self.agent.gateways[gway]
        getattr(gateway, func_name)(*params)

    def get_hist_data(self, inst, freq, nlen = 20):
        data = []
        if freq in ['D', 'd']:
            if inst in self.agent.day_data:
                data = self.agent.day_data[inst].data[-nlen:]
        elif ('m' in freq) or ('M' in freq):
            f = int(freq[:-1])
            if (inst in self.agent.min_data) and (f in self.agent.min_data[inst]):
                data = self.agent.min_data[inst][f].data[-nlen:]
        return data

    def exit_agent(self):
        if self.agent != None:
            self.agent.exit()
