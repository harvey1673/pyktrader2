#-*- coding:utf-8 -*-
import logging
from base import *
from misc import *
import datetime
import trade

class ExecAlgoBase(object):
    def __init__(self, etrade, agent, min_vol = 1, max_vol = 20, start_time = None, end_time = None, stop_price = None):
        self.etrade = etrade
        self.agent = agent
        self.start_time = start_time
        self.end_time = end_time
        self.min_vol = min_vol
        self.max_vol = max_vol
        self.is_working = True if start_time == None or self.agent.tick_id >= start_time else False    
        
    def unwind(self):
        pass
    
    def update(self):
        self.etrade.update()
        return self.etrade.status
    
    def process(self):
        pass
                                
    def suspend(self):
        pass       

class ExecAlgoFixTimer(ExecAlgoBase):
    def __init__(self, etrade, *args, **kw):
        super(ExecAlgoBasic, self).__init__( *args, **kw)
        
    def process(self):
        
        
        
