#-*- coding:utf-8 -*-
import logging
from base import *
from misc import *

class Position(object):
    def __init__(self, instrument, gateway = 'CTP'):
        self.instrument = instrument
        self.gateway = gateway
        self.orders = []    #元素为Order
        
    def re_calc(self):
        pass

    def __str__(self):
        return unicode(self).encode('utf-8')
    
    def __unicode__(self):
        return '%s' % (self.instrument.name)
        
class GrossPosition(Position):
    def __init__(self, instrument, gateway = 'CTP', intraday_close_ratio = 1):
        super(GrossPosition, self).__init__(instrument, gateway)
        self.tday_pos = BaseObject(long=0, short=0) 
        self.tday_avp = BaseObject(long=0.0, short=0.0)        
        self.pos_tday = BaseObject(long=0, short=0)
        self.pos_yday = BaseObject(long=0, short=0) # yday's overnight position        
        self.curr_pos = BaseObject(long=0, short=0)
        self.locked_pos = BaseObject(long=0, short=0)
        self.can_yclose = BaseObject(long=0, short=0)
        self.can_close  = BaseObject(long=0, short=0)
        self.can_open = BaseObject(long=0, short=0)
        self.intraday_close_ratio = intraday_close_ratio
    
    def set_intraday_close_ratio(self, ratio):
        self.intraday_close_ratio = ratio
    
    def update_can_close(self, tday_opened, tday_c_locked, yday_c_locked):
        self.can_yclose.long  = 0
        self.can_yclose.short = 0
        self.can_close.long  = max(self.pos_yday.short + int(tday_opened.short * self.intraday_close_ratio) - tday_c_locked.long, 0) 
        self.can_close.short = max(self.pos_yday.long  + int(tday_opened.long * self.intraday_close_ratio)  - tday_c_locked.short,0) 
        
    def re_calc(self): #
        tday_opened = BaseObject(long=0, short=0)
        tday_o_locked = BaseObject(long=0, short=0)
        tday_closed = BaseObject(long=0,short=0)
        tday_c_locked = BaseObject(long=0,short=0)
        yday_closed = BaseObject(long=0,short=0)
        yday_c_locked = BaseObject(long=0,short=0)

        for mo in self.orders:
            logging.debug(str(mo))
            if mo.action_type == OF_OPEN:
                if mo.direction == ORDER_BUY:
                    tday_opened.long += mo.filled_volume
                    tday_o_locked.long += mo.volume
                else:
                    tday_opened.short += mo.filled_volume
                    tday_o_locked.short += mo.volume            
            elif (mo.action_type == OF_CLOSE) or (mo.action_type == OF_CLOSE_TDAY):
                if mo.direction == ORDER_BUY:
                    tday_closed.long  += mo.filled_volume
                    tday_c_locked.long += mo.volume
                else: 
                    tday_closed.short += mo.filled_volume
                    tday_c_locked.short += mo.volume
            elif mo.action_type == OF_CLOSE_YDAY:
                if mo.direction == ORDER_BUY:
                    yday_closed.long  += mo.filled_volume
                    yday_c_locked.long += mo.volume
                else:
                    yday_closed.short += mo.filled_volume
                    yday_c_locked.short += mo.volume

        self.update_can_close(tday_opened, tday_c_locked, yday_c_locked)
        self.tday_pos.long  = tday_opened.long + tday_closed.long + yday_closed.long
        self.tday_pos.short = tday_opened.short + tday_closed.short + yday_closed.short

        if self.tday_pos.long > 0:
            self.tday_avp.long = sum([o.filled_price*o.filled_volume for o in self.orders if o.direction == ORDER_BUY])/self.tday_pos.long
        else:
            self.tday_avp.long = 0.0
        if self.tday_pos.short > 0:
            self.tday_avp.short= sum([o.filled_price*o.filled_volume for o in self.orders if o.direction == ORDER_SELL])/self.tday_pos.short
        else:
            self.tday_avp.short = 0.0

        self.curr_pos.long = tday_opened.long - tday_closed.short + self.pos_yday.long - yday_closed.short
        self.curr_pos.short =tday_opened.short- tday_closed.long  + self.pos_yday.short- yday_closed.long
        self.locked_pos.long = self.pos_yday.long -yday_closed.short+ tday_o_locked.long - tday_closed.short
        self.locked_pos.short =self.pos_yday.short-yday_closed.long + tday_o_locked.short- tday_closed.long
        self.can_open.long  = max(self.instrument.max_holding[0] - self.locked_pos.long,0)
        self.can_open.short = max(self.instrument.max_holding[1] - self.locked_pos.short,0)

    def get_open_volume(self):
        return (self.can_open.long, self.can_open.short)
    
    def get_close_volume(self):
        return (self.can_close.long, self.can_close.short)
    
    def get_yclose_volume(self):
        return (self.can_yclose.long, self.can_yclose.short)

####头寸
class SHFEPosition(GrossPosition):
    def __init__(self, instrument, gateway = 'CTP', intraday_close_ratio = 1):
        super(SHFEPosition, self).__init__(instrument, gateway, intraday_close_ratio)
    
    def update_can_close(self, tday_opened, tday_c_locked, yday_c_locked):
        self.can_yclose.long  = max(self.pos_yday.short - yday_c_locked.long, 0)
        self.can_yclose.short = max(self.pos_yday.long  - yday_c_locked.short,0)
        self.can_close.long  = max(int(tday_opened.short * self.intraday_close_ratio) - tday_c_locked.long, 0) 
        self.can_close.short = max(int(tday_opened.long * self.intraday_close_ratio) - tday_c_locked.short, 0)   
