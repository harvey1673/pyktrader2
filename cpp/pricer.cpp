#include "pricer.h"

#define PRICE_EPS 0.005
#define VOL_EPS 0.01

double Pricer::delta()
{
	double fwd = this->fwd_();
	double eps = this->priceTweak();
	double ufwd = (1 + eps)*fwd;
	this->setFwd(ufwd);
	double uprice = this->price();

	double dfwd = (1 - eps)*fwd;
	this->setFwd(dfwd);
	double dprice = this->price();

	this->setFwd(fwd);

	return (uprice - dprice)/(ufwd - dfwd);
}

double Pricer::gamma()
{
	double fwd = this->fwd_();
	double price = this->price();
	double eps = this->priceTweak();
	double ufwd = (1 + eps)*fwd;
	this->setFwd(ufwd);
	double uprice = this->price();

	double dfwd = (1 - eps)*fwd;
	this->setFwd(dfwd);
	double dprice = this->price();

	this->setFwd(fwd);

	return (uprice + dprice - 2*price)/(eps*eps*fwd*fwd);
}

double Pricer::vega()
{
	VolNode* vol = this->vol_();
	double atmvol = vol->atmVol_();
	double eps = this->volTweak();

	double uvol = (1 + eps) * atmvol;
	vol->setAtm(uvol);
	double uprice = this->price();

	double dvol = (1 - eps) * atmvol;
	vol->setAtm(dvol);
	double dprice = this->price();

	vol->setAtm(atmvol);

	return (uprice - dprice)/(uvol - dvol);
}

double Pricer::theta()
{
	double price = this->price();
	double dtoday = this->dtoday_();
	double dexp = this->dexp_();

	if (dtoday >= dexp)
		return 0.0;
	
	VolNode *vol = this->vol_();
	double dnext = vol->nextwkday_(dtoday); 
	dnext = (dexp < dnext)? dexp: dnext;
	this->setToday(dnext);
	double nextprice = this->price();
	this->setToday(dtoday);
	return nextprice - price;
}

double BlackPricer::price()
{
	VolNode *vol = this->vol_(); 
	double fwd = this->fwd_();
	double dtoday = this->dtoday_();
	double dexp = this->dexp_();
	double strike = this->strike_();
	double strikeVol = vol->GetVolByMoneyness( std::log(strike/fwd), dexp);
	double tExp = vol->time2expiry_(dtoday, dexp);
	double df = std::exp(-this->irate_()*(dexp - dtoday)/365.0);
	std::string PutCall = this->otype_();

	return BlackPrice(fwd, strike, strikeVol, tExp,df, PutCall);
}

double AmericanFutPricer::price()
{
	VolNode *vol = this->vol_(); 
	double fwd = this->fwd_();
	double dtoday = this->dtoday_();
	double dexp = this->dexp_();
	double strike = this->strike_();
	double strikeVol = vol->GetVolByMoneyness( std::log(strike/fwd), dexp);
	double tExp = vol->time2expiry_(dtoday, dexp);
	double df = std::exp(-this->irate_()*(dexp - dtoday)/365.0);
	std::string PutCall = this->otype_();
	return AmericanOptFutPrice(fwd, strike, strikeVol, tExp,df, PutCall);
}

double DigitalPricer::price()
{
	VolNode *vol = this->vol_(); 
	double fwd = this->fwd_();
	double strike = this->strike_();	
	double dtoday = this->dtoday_();
	double dexp = this->dexp_();
	double tExp = vol->time2expiry_(dtoday, dexp);
	double df = std::exp(-this->irate_()*(dexp - dtoday)/365.0);
	std::string PutCall = this->otype_();

	double lowStrike  = strike * (1 - _sprdwidth);
	double lowVol = vol->GetVolByMoneyness( std::log(lowStrike/fwd), this->dexp_());
	double highStrike = strike * (1 + _sprdwidth);
	double highVol = vol->GetVolByMoneyness( std::log(highStrike/fwd), this->dexp_());

	double lowPrice = BlackPrice(fwd, lowStrike, lowVol, tExp,df, PutCall);
	double highPrice = BlackPrice(fwd, highStrike, highVol, tExp,df, PutCall);

	double binPrice;

	if ((PutCall == "C") || (PutCall =="c"))
		binPrice = (lowPrice - highPrice)/(highStrike - lowStrike);
	else
		binPrice = (highPrice - lowPrice)/(highStrike - lowStrike);

	return binPrice;
}

double BachelierPricer::price()
{
	VolNode *vol = this->vol_(); 
	double fwd = this->fwd_();
	double strike = this->strike_();
	double dtoday = this->dtoday_();
	double dexp = this->dexp_();
	double strikeVol = vol->GetVolByMoneyness( std::log(strike/fwd), dexp);
	double tExp = vol->time2expiry_(dtoday, dexp);
	double df = std::exp(-this->irate_()*(dexp - dtoday)/365.0);
	std::string PutCall = this->otype_();

	return BachelierPrice( fwd, strike, strikeVol, tExp,df, PutCall); 
}



BlackStripPricer::BlackStripPricer( 
		const double dtoday, 
		const double startDate, 
		const double endDate, 
		const double fwd, 
		VolNode *vol,
		const double strike, 
		const double ir, 
		const std::string otype, 
		const DblVector &hols ) : 
		Pricer( dtoday, endDate, fwd, vol, strike, ir, otype ), 
		_hols(hols), _sDate(startDate), _eDate(endDate)
{
	_bdays = businessDays(startDate, endDate, hols); 
	for (size_t i = 0; i < _bdays.size(); ++i)
		_pvec.push_back(BlackPricer(dtoday, _bdays[i], fwd, vol, strike, ir, otype));
}

double BlackStripPricer::price()
{
	double psum = 0.0;
	if (_pvec.size() == 0)
		return 0.0;
	else {
		for (size_t i=0; i< _pvec.size(); ++i )
			psum += _pvec[i].price();

		return psum/_pvec.size();
	}
}

void BlackStripPricer::setFwd(const double fwd)
{
	Pricer::setFwd(fwd);
	for (size_t i=0; i< _pvec.size(); ++i ) 
		_pvec[i].setFwd(fwd);
}

void BlackStripPricer::setVol(VolNode *vol)
{ 
	Pricer::setVol(vol);
	for (size_t i=0; i< _pvec.size(); ++i ) 
		_pvec[i].setVol(vol);
}

void BlackStripPricer::setIR(const double ir)
{ 
	Pricer::setIR(ir);
	for (size_t i=0; i< _pvec.size(); ++i ) 
		_pvec[i].setIR(ir);
}

void BlackStripPricer::setToday(const double dtoday)
{ 
	Pricer::setToday(dtoday);
	for (size_t i=0; i< _pvec.size(); ++i ) 
		_pvec[i].setToday(dtoday);
}



DigitalStripPricer::DigitalStripPricer( 
		const double dtoday, 
		const double startDate, 
		const double endDate, 
		const double fwd, 
		VolNode *vol,
		const double strike, 
		const double ir, 
		const std::string otype, 
		const DblVector &hols ) : 
		Pricer( dtoday, endDate, fwd, vol, strike, ir, otype ), 
		_hols(hols), _sDate(startDate), _eDate(endDate)
{
	_bdays = businessDays(startDate, endDate, hols); 
	for (size_t i = 0; i < _bdays.size(); ++i)
		_pvec.push_back(DigitalPricer(dtoday, _bdays[i], fwd, vol, strike, ir, otype));
}

double DigitalStripPricer::price()
{
	double psum = 0.0;
	if (_pvec.size() == 0)
		return 0.0;
	else {
		for (size_t i=0; i< _pvec.size(); ++i )
			psum += _pvec[i].price();

		return psum/_pvec.size();
	}
}

void DigitalStripPricer::setFwd(const double fwd)
{
	Pricer::setFwd(fwd);
	for (size_t i=0; i< _pvec.size(); ++i ) 
		_pvec[i].setFwd(fwd);
}

void DigitalStripPricer::setVol(VolNode *vol)
{ 
	Pricer::setVol(vol);
	for (size_t i=0; i< _pvec.size(); ++i ) 
		_pvec[i].setVol(vol);
}

void DigitalStripPricer::setIR(const double ir)
{ 
	Pricer::setIR(ir);
	for (size_t i=0; i< _pvec.size(); ++i ) 
		_pvec[i].setIR(ir);
}

void DigitalStripPricer::setToday(const double dtoday)
{ 
	Pricer::setToday(dtoday);
	for (size_t i=0; i< _pvec.size(); ++i ) 
		_pvec[i].setToday(dtoday);
}

double BarrierPricer::price()
{
	VolNode *volnode = this->vol_();
	double fwd = this->fwd_();
	double strike = this->strike_();	
	double barrier = this->barrier_();
	double dtoday = this->dtoday_();
	double dexp = this->dexp_();
	double tExp = volnode->time2expiry_(dtoday, dexp);
	double df = std::exp(-this->irate_()*(dexp-dtoday)/365.0);
	std::string otype = this->otype_();
	std::string btype = this->btype_();
	std::string mtype = this->mtype_();

	double vol = volnode->GetVolByMoneyness( 0, dexp);

	if ( mtype == "d" ) {
		double discreteAdj = std::exp( 0.5826 * vol / std::sqrt(245.0));
		if ( fwd > barrier )
		{
			barrier = barrier / discreteAdj;
		}
		else if ( fwd < barrier )
		{
			barrier = barrier * discreteAdj;
		}
	}

	double price = -1;

	if ((btype == "do") || (btype == "DO")) 
	{
		if (( otype == "c" ) || (otype =="C"))
			price = BarrierSingleFull_doc( fwd, vol, tExp, strike, barrier, df );
		else
			price = BarrierSingleFull_dop( fwd, vol, tExp, strike, barrier, df );
	}
	else if ((btype == "di") || (btype == "DI")) 
	{
		if (( otype == "c" ) || (otype =="C"))
			price = BarrierSingleFull_dic( fwd, vol, tExp, strike, barrier, df );
		else
			price = BarrierSingleFull_dip( fwd, vol, tExp, strike, barrier, df );
	}
	else if ((btype == "uo") || (btype == "UO")) 
	{
		if (( otype == "c" ) || (otype =="C"))
			price = BarrierSingleFull_uoc( fwd, vol, tExp, strike, barrier, df );
		else
			price = BarrierSingleFull_uop( fwd, vol, tExp, strike, barrier, df );
	}
	else if ((btype == "ui") || (btype == "UI")) 
	{
		if (( otype == "c" ) || (otype =="C"))
			price = BarrierSingleFull_uic( fwd, vol, tExp, strike, barrier, df );
		else
			price = BarrierSingleFull_uip( fwd, vol, tExp, strike, barrier, df );
	}

	return price;
}

BarrierStripPricer::BarrierStripPricer( const double dtoday, 
		const double startDate, const double endDate, 
		const double fwd, VolNode *vol, const double strike, 
		const double barrier, const std::string btype,
		const double ir, std::string otype, const std::string mtype,
		const DblVector &hols ): 
		Pricer( dtoday, endDate, fwd, vol, strike, ir, otype ), 
		_barrier(barrier), _btype(btype), _mtype(mtype),
		_hols(hols), _sDate(startDate), _eDate(endDate)
{
	_bdays = businessDays(startDate, endDate, hols); 
	for (size_t i = 0; i < _bdays.size(); ++i)
		_pvec.push_back(BarrierPricer(dtoday, _bdays[i], fwd, vol, strike, barrier, btype, ir, otype, mtype));
}

double BarrierStripPricer::price()
{
	double psum = 0.0;
	if (_pvec.size() == 0)
		return 0.0;
	else {
		for (size_t i=0; i< _pvec.size(); ++i )
			psum += _pvec[i].price();

		return psum/_pvec.size();
	}
}

void BarrierStripPricer::setFwd(const double fwd)
{
	Pricer::setFwd(fwd);
	for (size_t i=0; i< _pvec.size(); ++i ) 
		_pvec[i].setFwd(fwd);
}

void BarrierStripPricer::setVol(VolNode *vol)
{ 
	Pricer::setVol(vol);
	for (size_t i=0; i< _pvec.size(); ++i ) 
		_pvec[i].setVol(vol);
}

void BarrierStripPricer::setIR(const double ir)
{ 
	Pricer::setIR(ir);
	for (size_t i=0; i< _pvec.size(); ++i ) 
		_pvec[i].setIR(ir);
}

void BarrierStripPricer::setToday(const double dtoday)
{ 
	Pricer::setToday(dtoday);
	for (size_t i=0; i< _pvec.size(); ++i ) 
		_pvec[i].setToday(dtoday);
}