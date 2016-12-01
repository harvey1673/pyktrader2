from misc import *  
from utilities import *
from curve import *
from cashflow import *
import os


def calibrate_ycurve(instrument_dict):
    pass
    
def calc_irs():
    today = Date.set_origin(21, 3, 2016)
    libor_fac = LiborIndexFactory('3M', Calendar.US_UK, DayCount.ACT360)
    spotdate = libor_fac.roll_date(today, 'spot')
    flt_fac = LegFactory('3M', Calendar.US_UK, DayCount.ACT360, index_fac=libor_fac)
    fix_fac = LegFactory('6M', Calendar.US_UK, DayCount._30E360, index_fac=FixedIndexFactory())
    swap_fac = InterestRateSwapFactory(rleg_fac=flt_fac, pleg_fac=fix_fac)
    irs = swap_fac.create(spotdate, tenor=Period('5Y'))
    pv = irs.value()
