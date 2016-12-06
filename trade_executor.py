#-*- coding:utf-8 -*-
import logging
from base import *
from misc import *
import datetime
import trade

class TradeExecBase(object):
    def __init__(self, etrade):
        self.etrade = etrade        

    def update_status(self, status):
        self.etrade.status = status

    def unwind(self):
        pass
    
    def update(self):
        self.etrade.update()
    
    def resume(self):
        pass
    
    def suspend(self):
        pass       
    
        
