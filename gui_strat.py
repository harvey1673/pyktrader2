#-*- coding:utf-8 -*-
import Tkinter as tk
import ttk
from gui_agent import *

class StratGui(object):
    def __init__(self, strat, app, master):
        self.root = master
        self.name = strat.name
        self.app = app
        self.underliers = strat.underliers
        self.entries = {}
        self.stringvars = {}
        self.entry_fields = []
        self.status_fields = []
        self.shared_fields = []
        self.field_types = {}
        self.lblframe = None
        self.canvas = None
        self.vsby = None
        self.vsbx = None
                
    def get_params(self):
        fields = self.entry_fields + self.status_fields
        params = self.app.get_strat_params(self.name, fields)
        for field in fields:
            if field in self.shared_fields:
                value = params[field]
                if field in self.entry_fields:
                    ent = self.entries[field]
                    ent.delete(0, tk.END)
                    ent.insert(0, value)
                elif field in self.status_fields:
                    self.stringvars[field].set(keepdigit(value, 4))
            else:
                for idx, underlier in enumerate(self.underliers):
                    under_key = ','.join(underlier)
                    value = params[field][idx]
                    if type(value).__name__ in ['float', 'float64']:
                        value = round(value, 2)
                    vtype = self.field_types[field]
                    value = type2str(value, vtype)
                    if field in self.entry_fields:
                        ent = self.entries[under_key][field]
                        ent.delete(0, tk.END)
                        ent.insert(0, value)
                    elif field in self.status_fields:
                        self.stringvars[under_key][field].set(keepdigit(value, 4))
        
    def set_params(self):
        params = {}
        for field in self.entry_fields:
            if field in self.shared_fields:
                ent = self.entries[field]
                value = ent.get()
                vtype = self.field_types[field]
                value = str2type(value, vtype)
                params[field] = value
            else:
                params[field] = []
                for underlier in self.underliers:
                    under_key = ','.join(underlier)
                    ent = self.entries[under_key][field]
                    value = ent.get()
                    vtype = self.field_types[field]
                    value = str2type(value, vtype)
                    params[field].append(value)
        self.app.set_strat_params(self.name, params)

    def OnFrameConfigure(self, event):
        '''Reset the scroll region to encompass the inner frame'''
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
    def set_frame(self, root):
        self.canvas = tk.Canvas(root)
        self.lblframe = tk.Frame(self.canvas)
        self.vsby = tk.Scrollbar(root, orient="vertical", command=self.canvas.yview)
        self.vsbx = tk.Scrollbar(root, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.vsby.set, xscrollcommand=self.vsbx.set)
        self.vsbx.pack(side="bottom", fill="x")
        self.vsby.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.create_window((4,4), window=self.lblframe, anchor="nw", tags="self.lblframe")
        self.lblframe.bind("<Configure>", self.OnFrameConfigure)        
        #self.lblframe = ttk.Frame(root)        
        #self.lblframe.grid_columnconfigure(1, weight=1)     
        entries = {}
        stringvars = {}
        row_id = 0
        set_btn = ttk.Button(self.lblframe, text='Set', command=self.set_params)
        set_btn.grid(row=row_id, column=3, sticky="ew")
        refresh_btn = ttk.Button(self.lblframe, text='Refresh', command=self.get_params)
        refresh_btn.grid(row=row_id, column=4, sticky="ew")
        recalc_btn = ttk.Button(self.lblframe, text='Recalc', command=self.recalc)
        recalc_btn.grid(row=row_id, column=5, sticky="ew")
        save_btn = ttk.Button(self.lblframe, text='SaveConfig', command=self.save_config)
        save_btn.grid(row=row_id, column=6, sticky="ew")
        row_id += 1
        for idx, field in enumerate(self.shared_fields):
            lbl = ttk.Label(self.lblframe, text = field, anchor='w', width = 8)
            lbl.grid(row=row_id, column=idx+2, sticky="ew")
            if field in self.entry_fields:
                ent = ttk.Entry(self.lblframe, width=4)
                ent.grid(row=row_id+1, column=idx+2, sticky="ew")
                ent.insert(0, "0")
                entries[field] = ent
            elif field in self.status_fields:
                v= get_type_var(self.field_types[field])
                lab = ttk.Label(self.lblframe, textvariable = v, anchor='w', width = 8)
                lab.grid(row=row_id+1, column=idx+2, sticky="ew")
                v.set('0')
                stringvars[field] = v                   
        row_id += 2
        local_entry_fields = [ f for f in self.entry_fields if f not in self.shared_fields]
        local_status_fields = [ f for f in self.status_fields if f not in self.shared_fields]
        fields = ['assets'] + local_entry_fields + local_status_fields
        for idx, field in enumerate(fields):
            lbl = ttk.Label(self.lblframe, text = field, anchor='w', width = 8)
            lbl.grid(row=row_id, column=idx, sticky="ew")
        row_id += 1
        for underlier in self.underliers:
            under_key = ','.join(underlier)
            inst_lbl = ttk.Label(self.lblframe, text=under_key, anchor="w", width = 8)
            inst_lbl.grid(row=row_id, column=0, sticky="ew")
            col_id = 1
            entries[under_key] = {}
            for idx, field in enumerate(local_entry_fields):
                ent = ttk.Entry(self.lblframe, width=5)
                ent.grid(row=row_id, column=col_id+idx, sticky="ew")
                ent.insert(0, "0")
                entries[under_key][field] = ent
            col_id += len(local_entry_fields)
            stringvars[under_key] = {}            
            for idx, field in enumerate(local_status_fields):
                v= get_type_var(self.field_types[field])
                lab = ttk.Label(self.lblframe, textvariable = v, anchor='w', width = 8)
                lab.grid(row=row_id, column=col_id+idx, sticky="ew")
                v.set('0')
                stringvars[under_key][field] = v       
            row_id +=1
        self.entries = entries
        self.stringvars = stringvars        
        #self.lblframe.pack(side="top", fill="both", expand=True, padx=10, pady=10)
        self.get_params()
    
    def recalc(self):
        self.app.run_strat_func(self.name, 'initialize')

    def save_config(self):
        self.app.run_strat_func(self.name, 'save_config')

class DTStratGui(StratGui):
    def __init__(self, strat, app, master):
        StratGui.__init__(self, strat, app, master)
        self.entry_fields = ['PosScaler', 'RunFlag', 'Freq', 'AllocW', 'Lookbacks', 'Ratios', 'MaWin', 'Factors', 'CloseTday']
        self.status_fields = ['TradeUnit', 'TdayOpen', 'CurrPrices', 'CurRng', 'CurMa']
        self.shared_fields = ['PosScaler']
        self.field_types = {'RunFlag':'int',
                            'TradeUnit':'int',
                            'Lookbacks':'int', 
                            'Ratios': 'float',
                            'Factors': 'float',
                            'CloseTday': 'bool',
                            'TdayOpen': 'float',
                            'CurrPrices': 'float',
                            'CurRng':'float',
                            'CurMa': 'float',
                            'MaWin': 'int',
                            'MinRng': 'float',
                            'AllocW': 'float',
                            'PosScaler': 'float',
                            'Freq': 'int'}

class DTSplitDChanStratGui(StratGui):
    def __init__(self, strat, app, master):
        StratGui.__init__(self, strat, app, master)
        self.entry_fields = ['PosScaler', 'RunFlag', 'Freq', 'AllocW', 'Channels', 'Lookbacks', 'Ratios', 'CloseTday']
        self.status_fields = ['TdayOpen', 'OpenIdx', 'TradeUnit', 'CurrPrices', 'CurRng', 'ChanHigh', 'ChanLow']
        self.shared_fields = ['PosScaler']
        self.field_types = {'RunFlag':'int',
                            'TradeUnit':'int',
                            'Lookbacks':'int',
                            'Ratios': 'float',
                            'CloseTday': 'bool',
                            'TdayOpen': 'float',
                            'OpenIdx': 'int',
                            'CurrPrices': 'float',
                            'CurRng':'float',
                            'ChanHigh': 'float',
                            'ChanLow': 'float',
                            'Channels': 'int',
                            'MinRng': 'float',
                            'AllocW': 'float',
                            'PosScaler': 'float',
                            'Freq': 'int',
                            }

class DTSplitChanAddonStratGui(StratGui):
    def __init__(self, strat, app, master):
        StratGui.__init__(self, strat, app, master)
        self.entry_fields = ['PosScaler', 'RunFlag', 'Freq', 'AllocW', 'Channels', 'Lookbacks', 'Ratios', 'PriceMode', 'CloseTday']
        self.status_fields = ['TdayOpen', 'OpenIdx', 'VolRatio', 'TradeUnit', 'CurrPrices', 'CurRng', 'ChanHigh', 'ChanLow']
        self.shared_fields = ['PosScaler']
        self.field_types = {'RunFlag':'int',
                            'TradeUnit':'int',
                            'Lookbacks':'int',
                            'Ratios': 'float',
                            'VolRatio': 'floatlist',
                            'PriceMode': 'str',
                            'CloseTday': 'bool',
                            'TdayOpen': 'float',
                            'OpenIdx': 'int',
                            'CurrPrices': 'float',
                            'CurRng':'float',
                            'ChanHigh': 'float',
                            'ChanLow': 'float',
                            'Channels': 'int',
                            'MinRng': 'float',
                            'AllocW': 'float',
                            'PosScaler': 'float',
                            'Freq': 'int',
                            }

class BBandPChanStratGui(StratGui):   
    def __init__(self, strat, app, master):
        StratGui.__init__(self, strat, app, master)
        self.entry_fields = ['PosScaler', 'RunFlag', 'AllocW',  'Ratios', 'CloseTday']
        self.status_fields = ['TradeUnit', 'Freq', 'CurrPrices', 'BandWin', 'UpperBand', 'MidBand', 'LowerBand', 'Channels', 'ChanHigh', 'ChanLow']
        self.shared_fields = ['PosScaler']
        self.field_types = {'RunFlag':'int',
                            'TradeUnit':'int',
                            'Ratios': 'float',
                            'CloseTday': 'bool',
                            'CurrPrices': 'float',
                            'MidBand': 'float',
                            'UpperBand': 'float',
                            'LowerBand': 'float',
                            'BandWin': 'int',
                            'ChanHigh': 'float',
                            'ChanLow': 'float',
                            'Channels': 'int',
                            'AllocW': 'float',
                            'PosScaler': 'float',
                            'Freq': 'int',
                            }

class MASystemStratGui(StratGui):
    def __init__(self, strat, app, master):
        StratGui.__init__(self, strat, app, master)
        self.entry_fields = ['PosScaler', 'RunFlag', 'AllocW', 'CloseTday']
        self.status_fields = ['TradeUnit', 'Freq', 'CurrPrices', 'MaWin', 'MaFast', 'MaMedm', 'MaSlow', 'Channels', 'ChanHigh', 'ChanLow']
        self.shared_fields = ['PosScaler']
        self.field_types = {'RunFlag':'int',
                            'TradeUnit':'int',
                            'Ratios': 'float',
                            'CloseTday': 'bool',
                            'CurrPrices': 'float',
                            'MaWin': 'intlist',
                            'MaFast': 'float',
                            'MaMedm': 'float',
                            'MaSlow': 'float',
                            'ChanHigh': 'float',
                            'ChanLow': 'float',
                            'Channels': 'int',
                            'AllocW': 'float',
                            'PosScaler': 'float',
                            'Freq': 'int',
                            }

class AsctrendStratGui(StratGui):
    def __init__(self, strat, app, master):
        StratGui.__init__(self, strat, app, master)
        self.entry_fields = ['PosScaler', 'RunFlag', 'AllocW', 'CloseTday']
        self.status_fields = ['TradeUnit', 'Freq', 'CurrPrices', 'RsiWin', 'RsiLevel', 'WprWin', 'WprLevel', \
                              'SarParam', ]
        self.shared_fields = ['PosScaler']
        self.field_types = {'RunFlag':'int',
                            'TradeUnit':'int',
                            'Ratios': 'float',
                            'CloseTday': 'bool',
                            'CurrPrices': 'float',
                            'RsiWin': 'int',
                            'RsiLevel': 'intlist',
                            'WprWin': 'int',
                            'WprLevel': 'intlist',
                            'SarParam': 'floatlist',
                            'AllocW': 'float',
                            'PosScaler': 'float',
                            'Freq': 'int',
                            }

class RBStratGui(StratGui):
    def __init__(self, strat, app, master):
        StratGui.__init__(self, strat, app, master)
        self.root = master
        self.entry_fields = ['PosScaler', 'RunFlag', 'EntryLimit', 'DailyCloseBuffer', 'AllocW', 'MinRng', 'TrailLoss', 'Ratios', 'StartMinId']
        self.status_fields = ['TradeUnit', 'CurrPrices', 'Sbreak', 'Bsetup', 'Benter', 'Senter', 'Ssetup', 'Bbreak']
        self.shared_fields = ['PosScaler', 'EntryLimit', 'DailyCloseBuffer']
        self.field_types = {'RunFlag':'int',
                            'AllocW': 'float',
                            'PosScaler': 'float',
                            'TradeUnit':'int',
                            'MinRng':'float', 
                            'Ratios': 'floatlist', 
                            'StartMinId': 'int',
                            'CurrPrices': 'float',
                            'Sbreak': 'float', 
                            'Bbreak':'float',
                            'Bsetup':'float', 
                            'Benter':'float', 
                            'Senter':'float', 
                            'Ssetup':'float',
                            'TrailLoss':'float',
                            'EntryLimit': 'int',
                            'DailyCloseBuffer': 'int'}

class TLStratGui(StratGui):
    def __init__(self, strat, app, master):
        StratGui.__init__(self, strat, app, master)
        self.root = master
        self.entry_fields = ['PosScaler', 'RunFlag', 'AllocW', 'Channels', 'MaxPos', 'TrailLoss']
        self.status_fields = ['TradingFreq', 'TradeUnit', 'CurrPrices', 'CurrAtr', 'EntryHigh', 'EntryLow', 'ExitHigh', 'ExitLow']
        self.shared_fields = ['PosScaler']
        self.field_types = {'RunFlag':'int',
                            'TradeUnit':'int',
                            'TradingFreq': 'str',
                            'TrailLoss': 'float',
                            'MaxPos': 'int',
                            'Channels': 'intlist',
                            'CurrPrices': 'float',
                            'CurrAtr':  'float',
                            'EntryHigh':'float',
                            'EntryLow': 'float',
                            'ExitHigh': 'float',
                            'ExitLow':  'float',
                            'AllocW': 'float',
                            'PosScaler': 'float'}

class OptionArbStratGui(StratGui):
    def __init__(self, strat, app, master):
        StratGui.__init__(self, strat, app, master)
        self.root = master
        self.entry_fields = ['RunFlag', 'ProfitRatio', 'ExitRatio']
        self.status_fields = ['TradeUnit', 'BidPrices', 'AskPrices', 'DaysToExpiry', 'TradeMargin'] 
        self.shared_fields = ['ProfitRatio', 'ExitRatio']
        self.field_types = {'RunFlag':'int',
                           'TradeUnit':'int',
                            'BidPrices': 'float',
                            'AskPrices': 'float',
                            'DaysToExpiry':'int',
                            'TradeMargin':'floatlist',
                            'ProfitRatio': 'float',
                            'ExitRatio': 'float'}
