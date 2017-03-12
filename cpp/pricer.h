#ifndef PRICER_H
#define PRICER_H

#include <string>
#include "volmodel.h"
#include "euopt.h"
#include "amopt.h"
#include "barrier.h"
#include "math_utils.h"

class Pricer {
public:
	Pricer( const double dtoday, const double dexp, 
			const double fwd, VolNode *vol,
			const double strike, const double ir, std::string otype):
			_dtoday(dtoday), _dexp(dexp),
			_fwd(fwd), _vol(vol), 
			_strike(strike), _irate(ir), _otype(otype) { _time2expiry = vol->time2expiry_(dtoday, dexp);}
    Pricer( const double time2expiry, 
			const double fwd, VolNode *vol,
			const double strike, const double ir, std::string otype):
			_time2expiry(time2expiry), _dtoday(0), _dexp(time2expiry*Yearly_Accrual_Days), 
			_fwd(fwd), _vol(vol), 
			_strike(strike), _irate(ir), _otype(otype) {}
	virtual double price() = 0;
	virtual double delta();
	virtual double gamma();
	virtual double vega();
	virtual double theta();

	virtual void setStrike( const double strike) { _strike = strike; }
	virtual void setFwd( const double fwd) { _fwd = fwd; }
	virtual void setVol( VolNode *vol) { _vol = vol; }
	virtual void setIR( const double ir) { _irate = ir; }
	virtual void setExpiry( const double dexp) { _dexp = dexp; _time2expiry = _vol->time2expiry_(this->dtoday_(), dexp); }
    virtual void setT2Exp( const double time2expiry ) { _time2expiry = time2expiry; }
	virtual void setToday( const double dtoday) { _dtoday = dtoday; _time2expiry = _vol->time2expiry_(dtoday, this->dexp_());}
	void setOtype( const std::string otype) { _otype = otype; }
	double strike_() { return _strike; }
	double fwd_() { return _fwd; }
	VolNode* vol_() { return _vol; }
	double dexp_() { return _dexp; }
	double dtoday_() { return _dtoday; }
    double time2expiry_() { return _time2expiry; }
	double irate_() { return _irate; }
	std::string otype_() { return _otype; }
	virtual double priceTweak() { return 0.001; }
	virtual double volTweak() { return 0.01; }
private:
	double _fwd;
	VolNode *_vol;
	double _strike;
	double _dexp;
	double _dtoday;
    double _time2expiry;
	double _irate;
	std::string _otype;
};

class BlackPricer : public Pricer {
public:
	BlackPricer( const double dtoday, const double dexp, 
			const double fwd, VolNode *vol,
			const double strike, const double ir, std::string otype)
			: Pricer( dtoday, dexp, fwd, vol, strike, ir, otype ) {}
	BlackPricer( const double time2expiry, 
			const double fwd, VolNode *vol,
			const double strike, const double ir, std::string otype)
			: Pricer( time2expiry, fwd, vol, strike, ir, otype ) {}
	virtual double price();
};

class AmericanFutPricer : public Pricer {
public:
	AmericanFutPricer( const double dtoday, const double dexp, 
			const double fwd, VolNode *vol,
			const double strike, const double ir, std::string otype, const int tree_steps = 128)
			: Pricer( dtoday, dexp, fwd, vol, strike, ir, otype ), _tree_steps(tree_steps) {}
	AmericanFutPricer( const double time2expiry,  
			const double fwd, VolNode *vol,
			const double strike, const double ir, std::string otype, const int tree_steps = 128)
			: Pricer( time2expiry, fwd, vol, strike, ir, otype ), _tree_steps(tree_steps) {}
	virtual double price();
private:
	int _tree_steps;    
};

class DigitalPricer : public Pricer {
public:
	DigitalPricer( const double dtoday, const double dexp, 
			const double fwd, VolNode *vol, const double strike, 
			const double ir, std::string otype)
			: Pricer( dtoday, dexp, fwd, vol, strike, ir, otype ), 
			  _sprdwidth(0.0001) {}
	DigitalPricer( const double time2expiry, 
			const double fwd, VolNode *vol, const double strike, 
			const double ir, std::string otype)
			: Pricer( time2expiry, fwd, vol, strike, ir, otype ), 
			  _sprdwidth(0.0001) {}
	virtual double price();
private:
	double _sprdwidth;
};

class BachelierPricer : public Pricer {
public:
	BachelierPricer( const double dtoday, const double dexp, 
			const double fwd, VolNode *vol,
			const double strike, const double ir, std::string otype)
			: Pricer( dtoday, dexp, fwd, vol, strike, ir, otype ) {}
	BachelierPricer( const double time2expiry, 
			const double fwd, VolNode *vol,
			const double strike, const double ir, std::string otype)
			: Pricer( time2expiry, fwd, vol, strike, ir, otype ) {}
	virtual double price();
};

#endif
