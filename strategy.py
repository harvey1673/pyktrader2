#-*- coding:utf-8 -*-
from base import *
from misc import *
from eventType import *
from eventEngine import Event
import data_handler
import trade
from trade_executor import *
import copy
import datetime
import csv
import json
import os
import sec_bits
import logging

tradepos_header = ['insts', 'vols', 'pos', 'direction', 'entry_price', 'entry_time', 'entry_target', 'entry_tradeid',
                   'exit_price', 'exit_time', 'exit_target', 'exit_tradeid', 'profit', 'is_closed', 'multiple', 'reset_margin', 'trailing']

class TrailLossType:
    Ratio, Level = range(2)

class TradePos(object):
    def __init__(self, insts, vols, pos, entry_target, exit_target, multiple = 1, reset_margin = 0):
        self.insts = insts
        self.volumes = vols
        self.multiple = multiple
        self.pos = pos
        self.direction = 1 if pos > 0 else -1
        self.entry_target = entry_target
        self.entry_price = 0
        self.entry_time = NO_ENTRY_TIME
        self.entry_tradeid = 0
        self.exit_target = exit_target
        self.exit_price = 0
        self.exit_time = NO_ENTRY_TIME
        self.exit_tradeid = 0
        self.is_closed = False
        self.profit = 0.0
        self.reset_margin = reset_margin
        self.trailing = False
        self.close_comment = ''

    def check_exit(self, curr_price, margin):
        if self.direction * (self.exit_target - curr_price) >= margin:
            return True
        return False

    def set_exit(self, exit_p):
        self.exit_target = exit_p

    def update_price(self, curr_price):
        if (curr_price - self.exit_target) * self.direction > 0:
            self.exit_target = curr_price
            return True
        return False

    def update_bar(self, curr_bar):
        if self.direction > 0:
            curr_price = curr_bar.high
        else:
            curr_price = curr_bar.low
        return self.update_price(curr_price)

    def check_profit(self, curr_price, margin):
        if (curr_price - self.entry_price) * sign(margin) * self.direction >= abs(margin):
            return True
        else:
            return False

    def open(self, price, vol, start_time):
        self.entry_price = price
        self.pos = vol
        self.entry_time = start_time
        self.is_closed = False

    def cancel_open(self):
        self.entry_tradeid = 0
        self.is_closed = True

    def close(self, price, end_time):
        self.exit_time = end_time
        self.exit_price = price
        self.profit = (self.exit_price - self.entry_price) *  self.pos * self.multiple
        self.is_closed = True
        return self

    def partial_close(self, price, vol, end_time):
        if vol != 0:
            close_pos = copy.copy(self)
            close_pos.pos = vol
            close_pos.close(price, end_time)
            self.pos -= vol
            self.exit_tradeid = 0
            return close_pos
        else:
            return None
            
class ParSARTradePos(TradePos):
    def __init__(self, insts, vols, pos, entry_target, exit_target, multiple = 1, reset_margin = 10, af = 0.02, incr = 0.02, cap = 0.2):
        TradePos.__init__(self, insts, vols, pos, entry_target, exit_target - pos * reset_margin, multiple, reset_margin)
        self.af = af
        self.af_incr = incr
        self.af_cap = cap
        self.ep = entry_target

    def update_price(self, curr_ep):
        self.exit_target = self.exit_target + self.af_incr * (self.ep - self.exit_target)
        if (curr_ep - self.ep) * self.direction > 0:
            self.af = max(self.af_cap, self.af + self.af_incr)
            self.ep = curr_ep

class ParSARProfitTrig(TradePos):
    def __init__(self, insts, vols, pos, entry_target, exit_target, multiple = 1, reset_margin = 10, af = 0.02, incr = 0.02, cap = 0.2):
        TradePos.__init__(self, insts, vols, pos, entry_target, exit_target, multiple, reset_margin)
        self.af = af
        self.af_incr = incr
        self.af_cap = cap
        self.ep = entry_target

    def check_exit(self, curr_price, margin = 0):
        if self.trailing and (self.direction * (self.exit_target - curr_price) >= margin):
            return True
        else:
            return False

    def update_price(self, curr_ep):
        if self.trailing:
            self.exit_target = self.exit_target + self.af_incr * (self.ep - self.exit_target)
            if (curr_ep - self.ep) * self.direction > 0:
                self.af = max(self.af_cap, self.af + self.af_incr)
                self.ep = curr_ep
        else:
            if self.check_profit(curr_ep, self.reset_margin):
                self.trailing = True
                self.exit_target = curr_ep

class TargetTrailTradePos(TradePos):
    def __init__(self, insts, vols, pos, entry_target, exit_target, multiple = 1, reset_margin = 10):
        TradePos.__init__(self, insts, vols, pos, entry_target, exit_target, multiple, reset_margin)

    def update_price(self, curr_price):
        if self.trailing:
            super(TargetTrailTradePos, self).update_price(curr_price)
        else:
            if self.check_profit(curr_price, self.reset_margin):
                self.trailing = True
                self.exit_target = curr_price

def tradepos2dict(tradepos):
    trade = {}
    trade['insts'] = ' '.join(tradepos.insts)
    trade['vols'] = ' '.join([str(v) for v in tradepos.volumes])
    trade['pos'] = tradepos.pos
    trade['direction'] = tradepos.direction
    trade['entry_target'] = tradepos.entry_target
    trade['exit_target'] = tradepos.exit_target
    trade['entry_tradeid'] = tradepos.entry_tradeid
    trade['exit_tradeid'] = tradepos.exit_tradeid
    trade['entry_price'] = tradepos.entry_price
    trade['exit_price'] = tradepos.exit_price
    if tradepos.entry_time != '':
        trade['entry_time'] = tradepos.entry_time.strftime('%Y%m%d %H:%M:%S %f')
    else:
        trade['entry_time'] = ''
    if tradepos.exit_time != '':
        trade['exit_time'] = tradepos.exit_time.strftime('%Y%m%d %H:%M:%S %f')
    else:
        trade['exit_time'] = ''
    trade['profit'] = tradepos.profit
    trade['multiple'] = tradepos.multiple
    trade['is_closed'] = 1 if tradepos.is_closed else 0
    trade['reset_margin'] = tradepos.reset_margin
    trade['trailing'] = 1 if tradepos.trailing else 0
    return trade

class Strategy(object):
    common_params = {'name': 'test_strat', 'email_notify':'', 'data_func': [], 'pos_scaler': 1.0, \
                     'daily_close_buffer': 3, 'pos_class': 'TradePos', 'pos_args': {},\
                     'exec_class': 'ExecAlgo1DFixT', 'is_disabled': False}
    asset_params = {'underliers': [], 'volumes': [], 'trade_unit': 1,  'alloc_w': 0.01, 'price_unit': None, \
                    'close_tday': False, 'last_min_id': 2057, 'trail_loss': 0, \
                    'exec_args': {'max_vol': 20, 'time_period': 600, 'price_type': OPT_LIMIT_ORDER, \
                                  'tick_num': 1, 'order_type': '', 'inst_order': None} }
    def __init__(self, config, agent = None):
        self.load_config(config)
        num_assets = len(self.underliers)
        self.instIDs = self.dep_instIDs()
        self.tradables = self.underliers
        self.underlying = [None] * num_assets
        self.positions  = dict([(idx, []) for idx in range(num_assets)])
        self.submitted_trades = dict([(idx, []) for idx in range(num_assets)])
        self.agent = agent
        self.folder = ''
        self.inst2idx = {}
        self.under2idx = {}
        self.num_entries = [0] * num_assets
        self.num_exits   = [0] * num_assets
        self.curr_prices = [0.0] * num_assets
        self.run_flag = [1] * num_assets
        self.conv_f = {}
        self.unwind_key = (10000, 'unwind')        
        self.update_trade_unit()

    def save_config(self):
        config = {}
        d = self.__dict__
        for key in self.common_params:
            config[key] = d[key]
        config['assets'] = []
        for idx, under in enumerate(self.underliers):
            asset = {}
            for key in self.asset_params:
                asset[key] = d[key][idx]
            config['assets'].append(asset)
        fname = self.folder + 'config.json'
        with open(fname, 'w') as ofile:
            json.dump(config, ofile)        
    
    def load_config(self, config):
        d = self.__dict__
        for key in self.common_params:
            d[key] = config.get(key, self.common_params[key])
        for key in self.asset_params:
            d[key] = []
        for asset in config['assets']:
            for key in self.asset_params:
                d[key].append(asset.get(key, self.asset_params[key]))
        
    def dep_instIDs(self):
        return list(set().union(*self.underliers))

    def set_agent(self, agent):
        self.agent = agent
        self.folder = self.agent.folder + self.name + '_'
        self.inst2idx = {}
        for idx, under in enumerate(self.tradables):             
            under_key = '_'.join(under)
            self.under2idx[under_key] = idx
            if len(under) > 1:
                self.underlying[idx] = self.agent.add_spread(under, self.volumes[idx], self.price_unit[idx])
            else:
                self.underlying[idx] = self.agent.instruments[under[0]]
            for inst in under:
                if inst not in self.inst2idx:
                    self.inst2idx[inst] = []
                self.inst2idx[inst].append(idx)
        self.conv_f = dict([(inst, self.agent.instruments[inst].multiple) for inst in self.instIDs])
        self.register_func_freq()
        self.register_bar_freq()

    def register_func_freq(self):
        pass

    def register_bar_freq(self):
        pass

    def initialize(self):
        self.load_state()
        self.update_trade_unit()
    
    def on_log(self, text, level = logging.INFO, args = {}):    
        event = Event(type=EVENT_LOG)
        event.dict['data'] = text
        event.dict['owner'] = "strategy_" + self.name
        event.dict['level'] = level
        self.agent.eventEngine.put(event)

    def add_unwind(self, pair, book=''):
        instID = pair[0]
        vol = pair[1]
        price = pair[2]
        idx = self.unwind_key[0]
        multiple = self.agent.instruments[instID].multiple
        tradepos = eval(self.pos_class)([instID], [1], vol, price, price, multiple, **self.pos_args)
        tradepos.entry_tradeid = idx
        self.positions[idx].append(tradepos)
        tradepos.open(price, vol, datetime.datetime.now())               
        self.close_tradepos(idx, tradepos, price)        
        
    def on_trade(self, xtrade):
        save_status = False        
        if xtrade.book == str(self.unwind_key[0]):
            idx = self.unwind_key[0]
        else:
            under_key = '_'.join(xtrade.instIDs)
            idx = self.under2idx[under_key]
        entry_ids = [ tp.entry_tradeid for tp in self.positions[idx]]
        exit_ids = [tp.exit_tradeid for tp in self.positions[idx]]
        i = 0
        if xtrade.id in entry_ids:
            i = entry_ids.index(xtrade.id)
            is_entry = True
        elif xtrade.id in exit_ids:
            i = exit_ids.index(xtrade.id)
            is_entry = False
        else:
            self.on_log('the trade %s is in status = %s but not found in the strat=%s tradepos table' % (xtrade.id, xtrade.status, self.name), \
                                                                            level = logging.WARNING)
            xtrade.status = trade.TradeStatus.StratConfirm
            return
        tradepos = self.positions[idx][i]        
        traded_price = xtrade.filled_price
        if is_entry:
            if xtrade.filled_vol != 0:
                tradepos.open( traded_price, xtrade.filled_vol, datetime.datetime.now())
                self.on_log('strat %s successfully opened a position on %s after tradeid=%s is done, trade status is changed to confirmed' %
                            (self.name, '_'.join(tradepos.insts), xtrade.id), level = logging.INFO)
                self.num_entries[idx] += 1
            else:
                tradepos.cancel_open()
                self.on_log('strat %s cancelled an open position on %s after tradeid=%s is cancelled. Both trade and position will be removed.' %
                                (self.name, '_'.join(tradepos.insts), xtrade.id), level = logging.INFO)
            xtrade.status = trade.TradeStatus.StratConfirm    
        else:
            if xtrade.filled_vol == xtrade.vol:
                save_pos = tradepos.close( traded_price, datetime.datetime.now())
            else:
                save_pos = tradepos.partial_close( traded_price, xtrade.filled_vol, datetime.datetime.now())
            if save_pos != None:
                self.save_closed_pos(save_pos)
                self.on_log('strat %s closed a position on %s after tradeid=%s (filled = %s, full = %s) is done, the closed trade position is saved' %
                            (self.name, '_'.join(tradepos.insts), xtrade.id, xtrade.filled_vol, xtrade.vol), level = logging.INFO)
            xtrade.status = trade.TradeStatus.StratConfirm
            self.num_exits[idx] += 1
        self.positions[idx] = [ tradepos for tradepos in self.positions[idx] if not tradepos.is_closed]
        self.submitted_trades[idx] = [xtrade for xtrade in self.submitted_trades[idx] if xtrade.status!= trade.TradeStatus.StratConfirm]
        self.save_state()

    def liquidate_tradepos(self, idx):
        save_status = False
        if len(self.positions[idx]) > 0:
            for pos in self.positions[idx]:
                if (pos.entry_time > NO_ENTRY_TIME) and (pos.exit_tradeid == 0):
                    self.on_log( 'strat=%s is liquidating underliers = %s' % ( self.name,   '_'.join(pos.insts)), level = logging.INFO)
                    self.close_tradepos(idx, pos, self.curr_prices[idx])
                    save_status = True
        return save_status

    def add_live_trades(self, xtrade):
        if xtrade.book == str(self.unwind_key[0]):
            idx = int(xtrade.book)
        else:
            trade_key = '_'.join(xtrade.instIDs)
            idx = self.under2idx[trade_key]
        for cur_trade in self.submitted_trades[idx]:
            if xtrade.id == cur_trade.id:
                self.on_log('trade_id = %s is already in the strategy= %s list' % (xtrade.id, self.name), level = logging.DEBUG)
                return False
        self.on_log('trade_id = %s is added to the strategy= %s list' % (xtrade.id, self.name), level= logging.INFO)
        self.submit_trade(idx, xtrade)
        return True

    def day_finalize(self):
        self.on_log('strat %s is finalizing the day - update trade unit, save state' % self.name, level = logging.INFO)
        self.update_trade_unit()
        self.num_entries = [0] * len(self.underliers)
        self.num_exits = [0] * len(self.underliers)
        self.save_state()
        self.initialize()

    def calc_curr_price(self, idx):
        self.curr_prices[idx] = self.underlying[idx].mid_price

    def run_tick(self, ctick):
        if self.is_disabled: return
        save_status = False
        inst = ctick.instID
        idx_list = self.inst2idx[inst]
        for idx in idx_list:
            self.calc_curr_price(idx)
            if self.run_flag[idx] == 1:
                save_status = save_status or self.on_tick(idx, ctick)
            elif self.run_flag[idx] == 2:
                save_status = save_status or self.liquidate_tradepos(idx)
        if save_status:
            self.save_state()

    def run_min(self, inst, freq):
        if self.is_disabled: return
        save_status = False
        idx_list = self.inst2idx[inst]
        for idx in idx_list:
            if self.run_flag[idx] == 1:
                save_status = save_status or self.on_bar(idx, freq)
        if save_status:
            self.save_state()

    def on_tick(self, idx, ctick):
        return False

    def on_bar(self, idx, freq):
        return False

    def open_tradepos(self, idx, direction, price, volume = 0):
        tunit = self.trade_unit[idx] if volume == 0 else volume
        start_time = self.agent.tick_id
        xtrade = trade.XTrade( self.tradables[idx], self.volumes[idx], direction * tunit, price, price_unit = self.price_unit[idx], strategy=self.name,
                                book= str(idx), agent = self.agent, start_time = start_time)
        exec_algo = eval(self.exec_class)(xtrade, **self.exec_args[idx])
        xtrade.set_algo(exec_algo)
        tradepos = eval(self.pos_class)(self.tradables[idx], self.volumes[idx], direction * tunit, \
                                price, price, self.underlying[idx].multiple, **self.pos_args)
        tradepos.entry_tradeid = xtrade.id
        self.submit_trade(idx, xtrade)
        self.positions[idx].append(tradepos)        

    def submit_trade(self, idx, xtrade):
        xtrade.book = str(idx)
        self.submitted_trades[idx].append(xtrade)
        self.agent.submit_trade(xtrade)

    def close_tradepos(self, idx, tradepos, price):
        start_time = self.agent.tick_id
        xtrade = trade.XTrade( tradepos.insts, tradepos.volumes, -tradepos.pos, price, price_unit = self.price_unit[idx], strategy=self.name,
                                book= str(idx), agent = self.agent, start_time = start_time)
        exec_algo = eval(self.exec_class)(xtrade, **self.exec_args[idx])
        xtrade.set_algo(exec_algo)
        tradepos.exit_tradeid = xtrade.id
        self.submit_trade(idx, xtrade)

    def update_trade_unit(self):
        self.trade_unit = [ int(self.pos_scaler * self.alloc_w[idx] + 0.5) for idx in range(len(self.underliers))]

    def status_notifier(self, msg):
        self.on_log(msg, level = logging.INFO)
        if len(self.email_notify) > 0:
            send_mail(sec_bits.EMAIL_HOTMAIL, self.email_notify, '%s trade signal' % (self.name), msg)

    def save_local_variables(self, file_writer):
        pass

    def load_local_variables(self, row):
        pass

    def save_state(self):
        filename = self.folder + 'strat_status.csv'
        self.on_log('save state for strat = %s' % self.name, level = logging.DEBUG)
        with open(filename,'wb') as log_file:
            file_writer = csv.writer(log_file, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
            for key in sorted(self.positions.keys()):
                if key == self.unwind_key[0]:
                    header = self.unwind_key[1]
                else:
                    header = 'tradepos'
                for tradepos in self.positions[key]:
                    tradedict = tradepos2dict(tradepos)
                    row = [header] + [tradedict[itm] for itm in tradepos_header]
                    file_writer.writerow(row)
            self.save_local_variables(file_writer)

    def load_state(self):
        logfile = self.folder + 'strat_status.csv'
        positions  = dict([(idx, []) for idx in range(len(self.underliers))])
        if not os.path.isfile(logfile):
            self.positions  = positions
            return
        self.on_log('load state for strat = %s' % self.name, level = logging.DEBUG)
        with open(logfile, 'rb') as f:
            reader = csv.reader(f)
            for row in reader:
                if row[0] in ['tradepos', 'unwind']:
                    insts = row[1].split(' ')
                    vols = [ int(n) for n in row[2].split(' ')]
                    pos = int(row[3])
                    #direction = int(row[3])
                    entry_target = float(row[7])
                    exit_target = float(row[11])
                    multiple = float(row[15])
                    if len(row) > 16:
                        reset_margin = float(row[16])
                    else:
                        reset_margin = 0
                    if len(row) > 17:
                        trailing = True if float(row[17]) > 0 else False
                    else:
                        trailing = False
                    tradepos = eval(self.pos_class)(insts, vols, pos, entry_target, exit_target, multiple, reset_margin, **self.pos_args)
                    if row[6] in ['', '19700101 00:00:00 000000']:
                        entry_time = NO_ENTRY_TIME
                        entry_price = 0
                    else:
                        entry_time = datetime.datetime.strptime(row[6], '%Y%m%d %H:%M:%S %f')
                        entry_price = float(row[5])
                        tradepos.open(entry_price, pos, entry_time)
                    tradepos.entry_tradeid = int(row[8])
                    tradepos.trailing = trailing
                    tradepos.exit_tradeid = int(row[12])
                    if row[10] in ['', '19700101 00:00:00 000000']:
                        exit_time = NO_ENTRY_TIME
                        exit_price = 0
                    else:
                        exit_time = datetime.datetime.strptime(row[10], '%Y%m%d %H:%M:%S %f')
                        exit_price = float(row[9])
                        tradepos.close(exit_price, exit_time)
                    is_added = False
                    if row[0] == 'unwind':
                        idx = self.unwind_key[0]
                    else:
                        for i, under in enumerate(self.tradables):
                            if set(under) == set(insts):
                                idx = i
                                is_added = True
                                break
                        if not is_added:
                            self.on_log('underlying = %s is missing in strategy=%s, put it in undwind' % (insts, self.name), level = logging.INFO)
                            idx = self.unwind_key[0]
                    positions[idx].append(tradepos)
                else:
                    self.load_local_variables(row)
        self.positions = positions

    def save_closed_pos(self, tradepos):
        logfile = self.folder + 'hist_tradepos.csv'
        with open(logfile,'a') as log_file:
            file_writer = csv.writer(log_file, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
            tradedict = tradepos2dict(tradepos)
            file_writer.writerow([tradedict[itm] for itm in tradepos_header])

    def risk_agg(self, risk_list):
        sum_risk = {}
        inst_risk = {}
        for inst in self.instIDs:
            inst_risk[inst] = dict([(risk, 0) for risk in risk_list])
            sum_risk[inst] = dict([(risk, 0) for risk in risk_list])
            for risk in risk_list:
                try:
                    prisk = risk[1:]
                    inst_risk[inst][risk] = getattr(self.agent.instruments[inst], prisk)
                except:
                    continue
        for idx, under in enumerate(self.tradables):
            pos = sum([tp.pos for tp in self.positions[idx]])
            for instID, v in zip(self.tradables[idx], self.volumes[idx]):
                for risk in risk_list:
                    sum_risk[instID][risk] += pos * v * inst_risk[instID][risk]
        return sum_risk
