from QuantLib import *
import copy
import os
import json
from cmq_inst import CMQInstrument
import cmq_utils
import cmq_curve
import cmq_cashflow
import cmq_rate_index

def calibrate_ycurve(market_data, field='IRYCurve_usd3m'):
    today = Date(str(market_data['MarketDate']), "YYYY-MM-DD")
    Settings.instance().evaluationDate = today
    quotes = market_data[field]
    calib_helpers = []
    calendar = cmq_utils.Calendar.US_UK
    dayroll = cmq_utils.DayRoll.ModifiedFollowing
    daycount = cmq_utils.DayCount.ACT360
    for quote in quotes:
        inst_name, inst_tenor = quote[0].split('_')
        if inst_name == "CD":
            ratehelper = DepositRateHelper(QuoteHandle(SimpleQuote(float(quote[1]))), \
                                           cmq_utils.Period(str(inst_tenor)), 2,
                                           calendar, dayroll, False, daycount)
        elif inst_name == "IRF":
            ratehelper = FuturesRateHelper(QuoteHandle(SimpleQuote(100 - float(quote[1]) * 100)),
                                           cmq_utils.Date(str(inst_tenor)), 3,
                                           calendar, dayroll, True, daycount,
                                           QuoteHandle(SimpleQuote(0.0)))
        elif inst_name == "IRS":
            ratehelper = SwapRateHelper(QuoteHandle(SimpleQuote(float(quote[1]))),
                                        cmq_utils.Period(str(inst_tenor)), calendar,
                                        Semiannual, cmq_utils.DayRoll.Unadjusted,
                                        cmq_utils.DayCount._30360US, USDLibor(Period(3, Months)))
        else:
            raise NameError('The instrument name %s is not supported' % inst_name)
        calib_helpers.append(ratehelper)
    # libor_fac = cmq_rate_index.LiborIndexFactory('3M', calendar, daycount)
    spotdate = today
    yield_curve = PiecewiseFlatForward(spotdate, calib_helpers, daycount)
    return yield_curve


class CMQRateSwap(CMQInstrument):
    def __init__(self, trade_data, market_data):
        super(CMQRateSwap, self).__init__(trade_data, market_data)

    def set_market_data(self, market_data):
        cmq_utils.Date.set_origin(*[int(s) for s in market_data['MarketDate'].split('-')][::-1])
        super(CMQRateSwap, self).set_market_data(market_data)
        self.index_curve = calibrate_ycurve(market_data, 'IRYCurve_usd3m')
        self.disc_curve = self.index_curve

    def set_trade_data(self, trade_data):
        self.calendar = cmq_utils.Calendar.US_UK
        self.fix_freq = '6M'
        self.flt_freq = '3M'
        self.flt_daycount = cmq_utils.DayCount.ACT360
        self.fix_daycount = cmq_utils.DayCount._30360US
        margin = trade_data.get('Margin', 0.0)
        lev = trade_data.get('Leverage', 1.0)
        notional = trade_data.get('Notional', 1e6)
        strike = trade_data['Strike']
        start_date = cmq_utils.str2tenor(trade_data.get('StartDate', None))
        end_date = cmq_utils.str2tenor(trade_data.get('EndDate', None))
        tenor = cmq_utils.Period("%sM" % (int((end_date - start_date) / 365.0 * 12)))
        libor_fac = cmq_rate_index.LiborIndexFactory(self.flt_freq, self.calendar, self.flt_daycount)
        flt_fac = cmq_cashflow.LegFactory(self.flt_freq, self.calendar, self.flt_daycount, libor_fac,
                                          notl_base=notional,
                                          rate_spread=margin,
                                          rate_leverage=lev)
        fix_fac = cmq_cashflow.LegFactory(self.fix_freq, self.calendar, self.fix_daycount,
                                          index_fac=cmq_rate_index.FixedIndexFactory(strike))
        swap_fac = cmq_cashflow.InterestRateSwapFactory(rleg_fac=flt_fac, pleg_fac=fix_fac)
        self.swap = swap_fac.create(start=start_date, tenor=tenor)

    def clean_price(self):
        disc = cmq_curve.DiscountCurve(0, self.index_curve.discount)
        return self.swap.value(disc, disc, disc)


class CMQIRSwap(CMQInstrument):
    def __init__(self, trade_data, market_data):
        self.index = None
        self.swap_engine = None
        super(CMQIRSwap, self).__init__(trade_data, market_data)

    def set_market_data(self, market_data):
        cmq_utils.Date.set_origin(*[int(s) for s in market_data['MarketDate'].split('-')][::-1])
        super(CMQIRSwap, self).set_market_data(market_data)
        ycurve = calibrate_ycurve(market_data, 'IRYCurve_usd3m')
        self.index_curve = RelinkableYieldTermStructureHandle()
        self.index_curve.linkTo(ycurve)
        self.swap_engine = DiscountingSwapEngine(self.index_curve)
        self.disc_curve = self.index_curve

    def set_trade_data(self, trade_data):
        super(CMQIRSwap, self).set_trade_data(trade_data)
        calendar = UnitedStates()
        fix_tenor = Period(6, Months)
        fix_adj = Unadjusted
        fix_daycount = Thirty360()
        self.index = USDLibor(Period(3, Months), self.index_curve)
        flt_tenor = Period(3, Months)
        flt_adj = ModifiedFollowing
        flt_daycount = self.index.dayCounter()
        margin = trade_data.get('Margin', 0.0)
        notional = trade_data.get('Notional', 1000000)
        strike = trade_data['Strike']
        start_date = cmq_utils.str2tenor(trade_data.get('StartDate', None))
        end_date = cmq_utils.str2tenor(trade_data.get('EndDate', None))
        stype_in = trade_data.get("SwapType", "Payer")
        if stype_in == "Payer":
            swapType = VanillaSwap.Payer
        else:
            swapType = VanillaSwap.Receiver

        fix_schd = Schedule(start_date, end_date,
                            fix_tenor, calendar,
                            fix_adj, fix_adj,
                            DateGeneration.Backward, False)
        flt_schd = Schedule(start_date, end_date,
                            flt_tenor, calendar,
                            flt_adj, flt_adj,
                            DateGeneration.Backward, False)
        self.swap = VanillaSwap(swapType, notional,
                                fix_schd, strike, fix_daycount,
                                flt_schd, self.index, margin,
                                flt_daycount)

    def price(self):
        self.set_trade_data(self.trade_data)
        self.swap.setPricingEngine(self.swap_engine)
        return self.swap.NPV()


class CMQIRBermSwaption(CMQIRSwap):
    def __init__(self, trade_data, market_data):
        self.exercise_dates = []
        self.swaption = None
        self.swap = None
        super(CMQIRBermSwaption, self).__init__(trade_data, market_data)

    def set_market_data(self, market_data):
        super(CMQIRBermSwaption, self).set_market_data(market_data)

    def calibrate_swnvol(self, market_data):
        today = Settings.instance().evaluationDate
        calendar = UnitedStates()
        spotdate = calendar.advance(today, Period(2, Days))
        swnvols = market_data["SWNVOL_usd3m"]
        swn_tenors = [ten for ten, quote in swnvols]
        swn_quote = [quote for ten, quote in swnvols]
        berm_dates = [calendar.advance(spotdate, Period(ten[0], Months)) for ten in swn_tenors]
        exercise = BermudanExercise(berm_dates[:-1], False)
        self.swaption = Swaption(self.swap, exercise)
        self.exercise_dates = berm_dates[:-1]
        helpers = [SwaptionHelper(Period(ten[0], Months), Period(ten[1], Months), \
                                  QuoteHandle(SimpleQuote(vol)), self.index, \
                                  self.index.tenor(), self.index.dayCounter(), \
                                  self.index.dayCounter(), self.index_curve) for ten, vol in swnvols]
        sigmas = [QuoteHandle(SimpleQuote(0.01))] * (len(self.exercise_dates) + 1)
        reversion = [QuoteHandle(SimpleQuote(0.01))]
        gsr = Gsr(self.index_curve, self.exercise_dates, sigmas, reversion, 20.0)
        swaption_engine = Gaussian1dSwaptionEngine(gsr, 64, 7.0, True, False, self.disc_curve)
        for h in helpers:
            h.setPricingEngine(swaption_engine)
        method = LevenbergMarquardt()
        ec = EndCriteria(1000, 10, 1E-8, 1E-8, 1E-8)
        gsr.calibrateVolatilitiesIterative(helpers, method, ec)
        self.swaption.setPricingEngine(swaption_engine)

    def set_trade_data(self, trade_data):
        super(CMQIRBermSwaption, self).set_trade_data(trade_data)

    def price(self):
        self.calibrate_swnvol(self.market_data, self.trade_data)
        return self.swaption.NPV()
