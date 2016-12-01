#ifndef MCPRICER_H
#define MCPRICER_H

#include "euopt.h"
#include "volmodel.h"
#include "mc.h"
#include "pricer.h"

class MCBarrierPricer : public BarrierPricer {
public:
	MCBarrierPricer( double dtoday, double dexp, 
			double fwd, VolNode *vol, double strike, 
			double barrier, std::string btype, double ir, 
			std::string otype, std::string mtype, DblVector hols, 
			int nPath, bool useAntithetic );
	~MCBarrierPricer();
	MCSmilePathGen* mc_() { return _mc; }
	virtual double theta();
	virtual void setFwd( const double fwd);
	virtual void setVol( VolNode *vol);
	virtual void setToday( const double dtoday);
	double price();
	virtual double priceTweak() { return 0.01; }
	virtual double volTweak() { return 0.02; }
private:
	MCSmilePathGen* _mc;
	bool _isValid;
};

#endif
			