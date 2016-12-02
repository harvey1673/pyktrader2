from QuantLib import *
import misc
import utilities 
import curve
import cashflow
import os
import json

def calibrate_ycurve(market_data):
    today = Date(market_data['TradeDate'], "YYYYMMDD")
    quotes = market_data['IR']['YCurve_usd3m']
    calib_helpers = []
    calendar = misc.Calendar.US_UK
    dayroll = misc.DayRoll.ModifiedFollowing
    daycount = misc.DayCount.ACT360
    for quote in quotes:
        inst_name, inst_tenor = quote[0].split('_')
        inst_mark = float(quote[1])
        if inst_name == "CD":
            tenor = Date(
            ratehelper = DepositRateHelper(QuoteHandle(inst_mark), misc.Period(tenor), 2,
                                     calendar, dayroll,
                                     False, daycount)
            
        elif inst_name == "IRF":
            ratehelper = FuturesRateHelper(QuoteHandle(inst_mark),
                                     misc.Date(tenor, "YYYYMMDD"), 3,
                                     calendar, dayroll,
                                     True, daycount,
                                     QuoteHandle(SimpleQuote(0.0)))
        elif inst_name == "IRS":
            ratehelper = SwapRateHelper(QuoteHandle(inst_mark),
                               Period(tenor), calendar,
                               Semiannual, Unadjusted,
                               misc.DayCount._30360US, USDLibor(Period('3M')))
        else:
            raise NameError('The instrument name %s is not supported' % inst_name)
        
        calib_helpers.append(ratehelper)
    libor_fac = rate_index.LiborIndexFactory('3M', misc.Calendar.US_UK, misc.DayCount.ACT360)
    spotdate = libor_fac.roll_date(today, 'spot')    
    yield_curve = PiecewiseLinearForward(spotdate, calib_helpers, misc.DayCount.ACT360)
    return yield_curve

def str2tenor(input):
    if input == None:
        return None
    if len(input) == 8:
        tenor = misc.Date("input", "YYYYMMDD")
    else:
        tenor = misc.Period(input)
    return tenor
    
def create_rateswap(spot_date, trade_data):    
    margin = trade_data.get('margin', 0.0)
    lev = trade_data.get('leverage', 1.0)
    strike = trade_data['strike']
    start = str2tenor(trade_data.get('start_date', None))
    expiry = str2tenor(trade_data.get('expiry', None))
    tenor = str2tenor(trade_data.get('tenor', None))
    libor_fac = rate_index.LiborIndexFactory('3M', Calendar.US_UK, DayCount.ACT360)
    spotdate = libor_fac.roll_date(today, 'spot') 
    flt_fac = cashflow.LegFactory('3M', misc.Calendar.US_UK, misc.DayCount.ACT360, index_fac=libor_fac, rate_spread=margin, 
                    rate_leverage= lev)
    fix_fac = cashflow.LegFactory('6M', misc.Calendar.US_UK, misc.DayCount._30E360, index_fac=FixedIndexFactory(strike))    
    swap_fac = cashflow.InterestRateSwapFactory(rleg_fac=flt_fac, pleg_fac=fix_fac)
    swap = swap_fac.create(spotdate, expiry=expiry, start=start, tenor=tenor)
    return swap
    
def price_irs(swap, indexcurve, disccurve = None):
    if oiscurve == None:
        disccurve = indexcurve
    return swap.value(indexcurve.discount, indexcurve.discount, disccurve)
    
def riskcalc(market_input, trade_input, req_results):
    yield_curve = calibrate_ycurve(market_data)
    market_data = json.load(market_input)
    trade_data = json.load(trade_input)

    
    libor_fac = LiborIndexFactory('3M', Calendar.US_UK, DayCount.ACT360)
    spotdate = libor_fac.roll_date(today, 'spot')
    flt_fac = LegFactory('3M', Calendar.US_UK, DayCount.ACT360, index_fac=libor_fac)
    fix_fac = LegFactory('6M', Calendar.US_UK, DayCount._30E360, index_fac=FixedIndexFactory())
    swap_fac = InterestRateSwapFactory(rleg_fac=flt_fac, pleg_fac=fix_fac)
    irs = swap_fac.create(spotdate, tenor=Period('5Y'))
    pv = irs.value()
        
