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

	return (uprice - dprice)/(uvol - dvol)/100.0;
}

double Pricer::theta()
{	
	double t2exp = this->time2expiry_();	
	if (t2exp <= 0)
		return 0.0;
	double price = this->price();
	VolNode *vol = this->vol_();
	double newt2exp = (t2exp >= 1/Yearly_Accrual_Days)? (t2exp-1/Yearly_Accrual_Days):0;
	this->setT2Exp(newt2exp);
	double nextprice = this->price();
	this->setT2Exp(t2exp);
	return nextprice - price;
}

double BlackPricer::price()
{
	VolNode *vol = this->vol_(); 
	double fwd = this->fwd_();	
	double t2exp = this->time2expiry_();
	double strike = this->strike_();
	double strikeVol = vol->GetVolByMoneyness( std::log(strike/fwd), t2exp);
	double df = std::exp(-this->irate_() * t2exp);
	std::string PutCall = this->otype_();
	return BlackPrice(fwd, strike, strikeVol, t2exp, df, PutCall);
}

double AmericanFutPricer::price()
{
	VolNode *vol = this->vol_(); 
	double fwd = this->fwd_();
	double t2exp = this->time2expiry_();
	double strike = this->strike_();
	double strikeVol = vol->GetVolByMoneyness( std::log(strike/fwd), t2exp );	
	double df = std::exp(-this->irate_() * t2exp);
	std::string PutCall = this->otype_();
	return AmericanOptFutPrice(fwd, strike, strikeVol, t2exp, df, PutCall);
}

double DigitalPricer::price()
{
	VolNode *vol = this->vol_(); 
	double fwd = this->fwd_();
	double strike = this->strike_();	
	double t2exp = this->time2expiry_();	
	double df = std::exp(-this->irate_()*t2exp);
	std::string PutCall = this->otype_();
	double lowStrike  = strike * (1 - _sprdwidth);
	double lowVol = vol->GetVolByMoneyness( std::log(lowStrike/fwd), t2exp );
	double highStrike = strike * (1 + _sprdwidth);
	double highVol = vol->GetVolByMoneyness( std::log(highStrike/fwd), t2exp );
	double lowPrice = BlackPrice(fwd, lowStrike, lowVol, t2exp, df, PutCall);
	double highPrice = BlackPrice(fwd, highStrike, highVol, t2exp, df, PutCall);
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
	double t2exp = this->time2expiry_();
	double strikeVol = vol->GetVolByMoneyness( std::log(strike/fwd), t2exp);	
	double df = std::exp(-this->irate_()*t2exp);
	std::string PutCall = this->otype_();
	return BachelierPrice( fwd, strike, strikeVol, t2exp,df, PutCall); 
}
