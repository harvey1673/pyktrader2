#ifndef BARRIERSMILE_H
#define BARRIERSMILE_H

#include "euopt.h"
#include "volmodel.h"
#include "pricer.h"

double SmileToLognormal(double p, double stdev, DblVector& Strikes, DblVector& CDFs);

class BarrierSmilePricer : public BarrierPricer {
public:
	BarrierSmilePricer( double dtoday, double dexp, 
			double fwd, VolNode *vol, double strike, 
			double barrier, std::string btype, double ir, 
			std::string otype, std::string mtype, 
			unsigned int nSteps=1600, double nSigmas=6.0)
			: BarrierPricer(dtoday, dexp, fwd, vol, 
			strike, barrier, btype, ir, otype, mtype),
			_nSideSteps(nSteps), _nSigmas(nSigmas){}
	virtual double price();
	virtual double priceTweak() { return 0.002; }
	virtual double volTweak() { return 0.01; }
private:
	double _nSigmas;
	unsigned int _nSideSteps;
};


#endif