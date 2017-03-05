#-*- coding:utf-8 -*-
import datetime
import pyktlib
import mysqlaccess
import copy
from misc import * 

class ProductType:
    Future, Stock, Option = range(3)

class VolGrid(object):
    def __init__(self, name, accrual = 'COM', tday = datetime.date.today(), is_spot = False, ccy = 'CNY'):
        self.name = name
        self.accrual = accrual
        self.ccy = ccy
        self.dtoday = date2xl(tday)
        self.df = {}
        self.fwd = {}
        self.volnode = {}
        self.volparam = {}
        self.underlier = {}
        self.dexp = {}
        self.main_cont = ''
        self.option_insts = {}
        self.spot_model = is_spot

def copy_volgrid(vg):
    volgrid = VolGrid(vg.name, accrual = vg.accrual, is_spot = vg.spot_model)
    volgrid.main_cont = vg.main_cont
    volgrid.dtoday = vg.dtoday
    for expiry in vg.option_insts:
        volgrid.df[expiry] = vg.df[expiry]
        volgrid.fwd[expiry] = vg.fwd[expiry]
        volgrid.volnode[expiry] = pyktlib.Delta5VolNode(vg.dtoday, vg.dexp[expiry],
                                                          vg.fwd[expiry],
                                                          vg.volparam[expiry][0],
                                                          vg.volparam[expiry][1],
                                                          vg.volparam[expiry][2],
                                                          vg.volparam[expiry][3],
                                                          vg.volparam[expiry][4],
                                                          vg.accrual)
        volgrid.volparam[expiry] = copy.copy(vg.volparam[expiry])
        volgrid.underlier[expiry] = copy.copy(vg.underlier[expiry])
        volgrid.dexp[expiry] = vg.dexp[expiry]
        volgrid.option_insts[expiry] = copy.copy(vg.option_insts[expiry])
    return volgrid

class Instrument(object):
    def __init__(self,name):
        self.name = name
        self.exchange = 'CFFEX'
        self.ptype = ProductType.Future
        self.product = 'IF'
        self.ccy = 'CNY'
        self.broker_fee = 0.0
        self.marginrate = (0,0) 
        self.multiple = 0
        self.pos = 1
        self.tick_base = 0  
        self.start_tick_id = 0
        self.last_tick_id = 0
        # market snapshot
        self.price = 0.0
        self.prev_close = 0.0
        self.volume = 0
        self.open_interest = 0
        self.last_update = 0
        self.ask_price1 = 0.0
        self.ask_vol1 = 0
        self.bid_price1 = 0.0
        self.bid_vol1 = 0
        self.ask_price2 = 0.0
        self.ask_vol2 = 0
        self.bid_price2 = 0.0
        self.bid_vol2 = 0
        self.ask_price3 = 0.0
        self.ask_vol3 = 0
        self.bid_price3 = 0.0
        self.bid_vol3 = 0
        self.ask_price4 = 0.0
        self.ask_vol4 = 0
        self.bid_price4 = 0.0
        self.bid_vol4 = 0
        self.ask_price5 = 0.0
        self.ask_vol5 = 0
        self.bid_price5 = 0.0
        self.bid_vol5 = 0        
        self.up_limit = 1e10
        self.down_limit = -1e10
        self.last_traded = 0
        self.max_holding = (500, 500)
        self.mid_price = 0.0
        self.cont_mth = 205012 # only used by option and future
        self.expiry = datetime.date(2050,12,31)
        self.day_finalized = False
    
    def shift_price(self, direction, tick_num = 0, price_level = '1'):
        price_str = 'bid_price' + str(price_level) if direction > 0 else 'ask_price' + str(price_level)
        base_price = getattr(self, price_str)
        if direction > 0:
            return min(base_price + tick_num * self.tick_base, self.up_limit)
        else:
            return max(base_price - tick_num * self.tick_base, self.down_limit)

    def check_price_limit(self, num_tick = 0):        
        tick_base = self.tick_base
        if (self.ask_price1 >= self.up_limit - num_tick * tick_base) or (self.bid_price1 <= self.down_limit + num_tick * tick_base):
            return True
        else:
            return False
            
    def fair_price(self):
        self.mid_price = (self.ask_price1 + self.bid_price1)/2.0
        return self.mid_price

    def initialize(self):
        pass
    
    def update_param(self, tday):
        pass

    def calc_margin_amount(self, direction, price = 0.0):
        my_marginrate = self.marginrate[0] if direction == ORDER_BUY else self.marginrate[1]
        return self.price * self.multiple * my_marginrate

class SpreadInst(object):
    def __init__(self, inst_data, instIDs, weights, multiple = None):
        self.instIDs = instIDs
        self.name = '_'.join([str(s) for s in instIDs + weights])
        self.inst_objs = [inst_data[inst] for inst in instIDs]
        self.weights = weights
        self.conv_factor = [ inst_obj.multiple for inst_obj in self.inst_objs ]
        self.tick_base = [inst_obj.tick_base for inst_obj in self.inst_objs]
        self.multiple = multiple if multiple != None else self.conv_factor[-1]
        self.last_update = [inst_obj.last_update for inst_obj in self.inst_objs]
        self.ask_price1 = 0.0
        self.ask_vol1 = 0
        self.bid_price1 = 0.0
        self.bid_vol1 = 0
        self.mid_price = 0
        
    def update(self):
        self.bid_price1 = self.price('bid')
        self.ask_price1 = self.price('ask')
        self.mid_price = (self.ask_price1 + self.bid_price1)/2.0
        self.bid_vol1 = min([inst_obj.bid_vol1 if w > 0 else inst_obj.ask_vol1 for inst_obj, w in zip(self.inst_objs, self.weights)])
        self.ask_vol1 = min([inst_obj.ask_vol1 if w > 0 else inst_obj.bid_vol1 for inst_obj, w in zip(self.inst_objs, self.weights)])

    def shift_price(self, direction, tick_num = 0, price_level = '1'):
        price_str = 'bid_price' + str(price_level) if direction > 0 else 'ask_price' + str(price_level)
        base_price = getattr(self, price_str)
        return base_price + sign(direction) * tick_num * sum([abs(tb) for tb in self.tick_base])

    def price(self, direction = 'mid', prices = None):
        if prices == None:
            if direction == 'bid':
                fields = ['bid_price1', 'ask_price1']
            elif direction == 'ask':
                fields = ['ask_price1', 'bid_price1']
            else:
                fields = ['mid_price', 'mid_price']
            prices = [getattr(inst_obj, fields[0]) if w>0 else getattr(inst_obj, fields[1]) for inst_obj, w in zip(self.inst_objs, self.weights)]
        return sum([ p * w * cf for (p, w, cf) in zip(prices, self.weights, self.conv_factor)])/self.multiple
        
class Stock(Instrument):
    def __init__(self,name):
        Instrument.__init__(self, name)
        self.initialize()
        
    def initialize(self):
        self.product = self.name
        self.ptype = ProductType.Stock
        self.start_tick_id = 1530000
        self.last_tick_id  = 2130000
        self.multiple = 1
        self.tick_base = 0.01
        self.broker_fee = 0    
        self.marginrate = (1,0)
        if self.name in CHN_Stock_Exch['SZE']:
            self.exchange = 'SZE'
        else:
            self.exchange = 'SSE'
        return

class Future(Instrument):
    def __init__(self,name):
        Instrument.__init__(self, name)
        self.initialize()
        
    def initialize(self):
        self.ptype = ProductType.Future
        self.product = inst2product(self.name)
        prod_info = mysqlaccess.load_product_info(self.product)
        self.exchange = prod_info['exch']
        if self.exchange == 'CZCE':
            self.cont_mth = int(self.name[-3:]) + 201000
        else:
            self.cont_mth = int(self.name[-4:]) + 200000
        self.start_tick_id =  prod_info['start_min'] * 1000
        if self.product in night_session_markets:
            self.start_tick_id = 300000
        self.last_tick_id =  prod_info['end_min'] * 1000     
        self.multiple = prod_info['lot_size']
        self.tick_base = prod_info['tick_size']
        self.broker_fee = prod_info['broker_fee']
        return
    
    def update_param(self, tday):
        self.marginrate = mysqlaccess.load_inst_marginrate(self.name)
        
class OptionInst(Instrument):
    def __init__(self,name):
        self.strike = 0.0 # only used by option
        self.otype = 'C'   # only used by option
        self.underlying = ''   # only used by option
        Instrument.__init__(self, name)
        self.pricer = None
        self.pricer_func = pyktlib.BlackPricer
        self.pv = 0.0
        self.delta = 1
        self.theta = 0.0
        self.gamma = 0.0
        self.vega = 0.0
        self.margin_param = [0.15, 0.1]
        self.initialize()
        
    def initialize(self):
        pass

    def update_param(self, tday):
        pass
    
    def set_pricer(self, vg, irate):
        expiry = self.expiry
        dexp = vg.dexp[expiry]
        fwd = vg.fwd[expiry]
        self.pricer = self.pricer_func(vg.dtoday, 
                                       vg.dexp[expiry],
                                       vg.fwd[expiry], 
                                       vg.volnode[expiry], 
                                       self.strike, 
                                       irate, 
                                       self.otype)
    def update_greeks(self):
        self.pv = self.pricer.price() 
        self.delta = self.pricer.delta()
        self.gamma = self.pricer.gamma()
        self.vega  = self.pricer.vega()/100.0
        self.theta = self.pricer.theta()
        
    def calc_risk(self, risk_name, refresh = True):
        if self.pricer == None:
            return None    
        risk_func = risk_name
        if risk_name == 'pv':
            risk_func = 'price'
        if refresh:
            risk = getattr(self.pricer, risk_func)()
            if risk_name == 'vega':
                risk = risk/100
            setattr(self, risk_name, risk)
        else:
            risk = getattr(self, risk_name)
        return risk
       
    def calc_margin_amount(self, direction, price = 0.0):
        my_margin = self.price
        if direction == ORDER_SELL:
            a = self.margin_param[0]
            b = self.margin_param[1]
            if price == 0.0:
                price = self.strike
            if self.otype == 'C':
                my_margin += max(price * a - max(self.strike-price, 0), price * b)
            else:
                my_margin += max(price * a - max(price - self.strike, 0), self.strike * b)
        return my_margin * self.multiple
        
class StockOptionInst(OptionInst):
    def __init__(self,name):    
        OptionInst.__init__(self, name)
        self.margin_param = [0.12, 0.07]
        self.initialize()
        
    def initialize(self):
        self.ptype = ProductType.Option
        prod_info = mysqlaccess.load_stockopt_info(self.name)
        self.exchange = prod_info['exch']
        self.multiple = prod_info['lot_size']
        self.tick_base = prod_info['tick_size']
        self.strike = prod_info['strike']
        self.otype = prod_info['otype']  
        self.underlying = prod_info['underlying']
        self.product = self.underlying
        self.cont_mth = prod_info['cont_mth']
        self.expiry = get_opt_expiry(self.underlying, self.cont_mth)
        return
        
class FutOptionInst(OptionInst):
    def __init__(self,name):    
        OptionInst.__init__(self, name)
        if self.exchange != 'CFFEX':
            self.pricer_func = pyktlib.AmericanFutPricer
            self.margin_param = [0.15, 0.1]
        else:
            self.pricer_func = pyktlib.BlackPricer
            self.margin_param = [0.15, 0.1]            
        self.initialize()
        
    def initialize(self):
        self.ptype = ProductType.Option
        self.product = inst2product(self.name)
        if (self.product[-3:] == 'Opt') and (self.product[:-3] in product_code['CZCE']):
            self.underlying = self.name[:5]
            self.otype = self.name[5]
            self.cont_mth = int(self.underlying[-3:]) + 201000
            self.strike = float(self.name[6:])
            self.product = self.name[:2]
            self.expiry = get_opt_expiry(self.underlying, self.cont_mth)
        else:
            sep_name = self.name.split('-')
            if self.product == 'IO_Opt':
                self.underlying = sep_name[0].replace('IO','IF')
                self.strike = float(sep_name[2])
                self.otype = str(sep_name[1])
                self.cont_mth = int(self.underlying[-4:]) + 200000
                self.expiry = get_opt_expiry(self.underlying, self.cont_mth)
                self.product = 'IO'
            elif '_Opt' in self.product:
                self.underlying = sep_name[0]
                self.strike = float(sep_name[2])
                self.otype = str(sep_name[1])
                self.cont_mth = int(self.underlying[-4:]) + 200000
                self.expiry = get_opt_expiry(self.underlying, self.cont_mth)
                self.product = self.product[:-4]
        prod_info = mysqlaccess.load_product_info(self.product)
        self.exchange = prod_info['exch']
        self.start_tick_id =  prod_info['start_min'] * 1000
        if self.product in night_session_markets:
            self.start_tick_id = 300000
        self.last_tick_id =  prod_info['end_min'] * 1000     
        self.multiple = prod_info['lot_size']
        self.tick_base = prod_info['tick_size']
        self.broker_fee = prod_info['broker_fee']
        return
