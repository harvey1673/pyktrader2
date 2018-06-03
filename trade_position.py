from base import *
from misc import *

tradepos_header = ['insts', 'vols', 'pos', 'direction', 'entry_price', 'entry_time', 'entry_target', 'entry_tradeid',
                   'exit_price', 'exit_time', 'exit_target', 'exit_tradeid', 'profit', 'is_closed', 'multiple',
                   'reset_margin', 'trailing']

class TrailLossType:
    Ratio, Level = range(2)


class TradePos(object):
    def __init__(self, **kwargs):
        self.insts = kwargs['insts']
        self.volumes = kwargs['volumes']
        self.multiple = kwargs.get('multiple', 1)
        self.pos = kwargs['pos']
        self.direction = 1 if self.pos > 0 else -1
        self.entry_target = kwargs.get('entry_target', 0.0)
        self.entry_price = kwargs.get('entry_price', 0.0)
        self.entry_time = kwargs.get('entry_time', NO_ENTRY_TIME)
        self.entry_tradeid = kwargs.get('entry_tradeid', 0)
        self.exit_target = kwargs.get('exit_target', 0.0)
        self.exit_price = kwargs.get('exit_price', 0.0)
        self.exit_time = kwargs.get('exit_time', NO_ENTRY_TIME)
        self.exit_tradeid = kwargs.get('exit_tradeid', 0)
        self.is_closed = kwargs.get('is_closed', False)
        self.profit = kwargs.get('profit', 0.0)
        self.reset_margin = kwargs.get('reset_margin', 0.0)
        self.trailing = kwargs.get('trailing', False)
        self.comments = kwargs.get('comments', '')

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

    def close(self, price, end_time, vol = None):
        if vol == None:
            vol = self.pos
        if vol == 0:
            self.exit_tradeid = 0
            return None
        self.pos -= vol
        if self.pos != 0:
            closed_pos = copy.copy(self)
            closed_pos.pos = vol
            self.exit_tradeid = 0
        else:
            self.pos = vol
            closed_pos = self
        closed_pos.exit_price = price
        closed_pos.exit_time = end_time
        closed_pos.profit = (closed_pos.exit_price - closed_pos.entry_price) * closed_pos.pos * closed_pos.multiple
        closed_pos.is_closed = True
        return closed_pos


class ParSARTradePos(TradePos):
    def __init__(self, **kwargs):
        kwargs['exit_target'] -= kwargs['pos'] * kwargs['reset_margin']
        TradePos.__init__(self, **kwargs)
        self.af = kwargs.get('af', 0.02)
        self.af_incr = kwargs.get('incr', 0.02)
        self.af_cap = kwargs.get('cap', 0.2)
        self.ep = kwargs.get('ep', self.entry_target)

    def update_price(self, curr_ep):
        self.exit_target = self.exit_target + self.af_incr * (self.ep - self.exit_target)
        if (curr_ep - self.ep) * self.direction > 0:
            self.af = max(self.af_cap, self.af + self.af_incr)
            self.ep = curr_ep


class ParSARProfitTrig(TradePos):
    def __init__(self, **kwargs):
        TradePos.__init__(self, **kwargs)
        self.af = kwargs.get('af', 0.02)
        self.af_incr = kwargs.get('incr', 0.02)
        self.af_cap = kwargs.get('cap', 0.2)
        self.ep = kwargs.get('ep', self.entry_target)

    def check_exit(self, curr_price, margin=0):
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
    def __init__(self, **kwargs):
        TradePos.__init__(self, **kwargs)

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
