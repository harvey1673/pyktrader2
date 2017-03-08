#include "mcpricer.h"

MCBarrierPricer::MCBarrierPricer( double dtoday, double dexp, 
			double fwd, VolNode *vol, double strike, 
			double barrier, std::string btype, double ir, 
			std::string otype, std::string mtype, DblVector hols, 
			int nPath = 5000, bool useAntithetic = true )
			: BarrierPricer( dtoday, dexp, fwd, vol, strike, 
			barrier, btype, ir, otype, mtype)
{
	_mc = new MCSmilePathGen(nPath, dtoday, dexp, hols, fwd, vol, useAntithetic, 6.0, 600);
	_mc->genRandNumber();
	_isValid = false;
}

MCBarrierPricer::~MCBarrierPricer()
{
	delete _mc;
}

void MCBarrierPricer::setFwd( const double fwd )
{
	Pricer::setFwd(fwd);
	_mc->setFwd(fwd);
	_isValid = false;
}

void MCBarrierPricer::setVol( VolNode *vol)
{
	Pricer::setVol(vol);
	_mc->setVol(vol);
}

void MCBarrierPricer::setToday( const double dtoday)
{
	Pricer::setToday(dtoday);
	_mc->setStart(dtoday);
}

double MCBarrierPricer::theta()
{
	double price = this->price();
	double dtoday = this->dtoday_();
	double dexp = this->dexp_();

	if (dtoday >= dexp)
		return 0.0;

	double dnext = this->mc_()->simDays_()[1];
	this->setToday(dnext);
	double nextprice = this->price();

	this->setToday(dtoday);
	return nextprice - price;
}

double MCBarrierPricer::price()
{
	_mc->calcPaths();

	int nPaths = _mc->nPaths_();
	int nDays = _mc->nDays_();
	std::string btype = this->btype_();
	std::string otype = this->otype_();
	double barrier = this->barrier_();
	char ud = btype.at(0);
	char io = btype.at(1);
	double ir = this->irate_();

	double sum_p = 0.0;

	for (int i = 0; i < nPaths; ++i)
	{
		bool isPayoff, isHit = false;
		double payout = 0.0;

		if (io == 'i')
			isPayoff = false;
		else
			isPayoff = true;

		for (int j = 0; j < nDays; ++j)
		{
			if (!isHit)
			{
				if ((((*_mc)(i,j) <= barrier) && (ud == 'd')) || (((*_mc)(i,j) >= barrier) && (ud == 'u')))
				{
					isHit = true;
					isPayoff = !isPayoff;
				}
			}

			if (_mc->simDays_()[j] == this->dexp_())
			{
				if (isPayoff)
					payout = BlackPrice( (*_mc)(i,j), this->strike_(), 0.0, 0.0, 1, otype );
				else
					payout = 0.0;
			}
		}
		sum_p += payout;
	}
	return (sum_p/nPaths)*std::exp(-ir*(this->dexp_() - this->dtoday_())/365.0);
}