import cmqlib as qlib
import datetime
from cmq_inst import CMQInstrument  
import cmq_utils
import cmq_curve
import misc

class CMQFXOption(CMQInstrument):
    class_params = dict(CMQInstrument.class_params, **{ 'ccypair':'EURUSD', 'otype': 'C', \
                                                        'expiry': datetime.date.today(), 'strike': 0.0})
    def __init__(self, trade_data, market_data = {}, model_settings = {}):
        super(CMQFXOption, self).__init__(trade_data, market_data, model_settings)
    
    def set_market_data(self, market_data):
        self.today = misc.datetime2xl(datetime.datetime.strptime(market_data['MarketDate'], '%Y-%m-%d'))
        cmq_utils.Date.set_origin(*[int(s) for s in market_data['MarketDate'].split('-')][::-1])
        super(CMQFXOption, self).set_market_data(market_data)
        fwd_quotes = market_data["FXFwd_" + self.ccypair]
        fwdtenors = [misc.datetime2xl(datetime.datetime.strptime(knot[2], '%Y-%m-%d')) for knot in fwd_quotes]
        spot_date = cmq_utils.Date(str(market_data['MarketDate']))
        fwds = [knot[1] for knot in fwd_quotes]
        self.fx_spot = fwds[0]
        fwdcurve = cmq_curve.ForwardCurve.from_array(fwdtenors, fwds)
        self.fx_fwd = fwdcurve(self.expiry)
        vol_field = "FXVOL_" + self.ccypair
        calendar = cmq_utils.Calendar.US
        voltenors = [ float(calendar.advance(spot_date, cmq_utils.Period(str(knot[0]))) - spot_date) for knot in market_data[vol_field]['ATM']]
        volmark = {}
        volmark['tenor'] = voltenors
        for field in ['ATM', 'RRd25', 'RRd10', 'BFd25', 'BFd10']:
            volmark[field] = [market_data[vol_field][field][i][1] for i in range(len(voltenors))]
        tom = self.expiry - self.today
        volpts = {}
        for field in ['ATM', 'RRd25', 'RRd10', 'BFd25', 'BFd10']:
            if field == 'ATM':
                mode = cmq_curve.VolCurve.InterpMode.LinearTime
            else:
                mode = cmq_curve.VolCurve.InterpMode.SqrtTime
            vcurve = cmq_curve.VolCurve.from_array( volmark['tenor'], volmark[field], interp_mode = mode )
            volpts[field] = vcurve(tom)
        self.atm = volpts['ATM']
        self.v10 = volpts['BFd10'] + volpts['RRd10']/2.0    
        self.v90 = volpts['BFd10'] - volpts['RRd10']/2.0 
        self.v25 = volpts['BFd25'] + volpts['RRd25']/2.0
        self.v75 = volpts['BFd25'] - volpts['RRd25']/2.0
        self.volnode = qlib.Delta5VolNode(self.today, self.expiry, self.fx_fwd, self.atm, self.v90, self.v75, self.v25, self.v10, "act365")
    
    def set_trade_data(self, trade_data):
        super(CMQFXOption, self).set_trade_data(trade_data)
        self.expiry = misc.datetime2xl(datetime.datetime.strptime(trade_data['expiry'], '%Y-%m-%d'))
        self.set_inst_key()

    def set_inst_key(self):
        self.inst_key = [self.__class__.__name__, self.ccypair, self.otype, self.strike, self.expiry, self.pricing_ccy, self.notional]
        
    def price(self):
        vol = self.volnode.GetVolByStrike(self.strike)
        fp = qlib.BlackPrice(self.fx_fwd, self.strike, vol, (self.expiry - self.today)/365.0, 1.0, self.otype)
        ccy1 = self.ccypair[:3]
        ccy2 = self.ccypair[-3:]        
        if self.pricing_ccy == ccy2:
            mtm = fp * self.notional
        else:
            mtm = fp * self.notional/self.fx_spot
        return mtm
