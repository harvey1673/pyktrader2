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
	virtual void setExpiry( const double dexp) { _dexp = dexp; }
	virtual void setToday( const double dtoday) { _dtoday = dtoday; }
	void setOtype( const std::string otype) { _otype = otype; }
	double strike_() { return _strike; }
	double fwd_() { return _fwd; }
	VolNode* vol_() { return _vol; }
	double dexp_() { return _dexp; }
	double dtoday_() { return _dtoday; }
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
	double _irate;
	std::string _otype;
};

class BlackPricer : public Pricer {
public:
	BlackPricer( const double dtoday, const double dexp, 
			const double fwd, VolNode *vol,
			const double strike, const double ir, std::string otype)
			: Pricer( dtoday, dexp, fwd, vol, strike, ir, otype ) {}

	virtual double price();
};

class AmericanFutPricer : public Pricer {
public:
	AmericanFutPricer( const double dtoday, const double dexp, 
			const double fwd, VolNode *vol,
			const double strike, const double ir, std::string otype)
			: Pricer( dtoday, dexp, fwd, vol, strike, ir, otype ) {}

	virtual double price();
};

class DigitalPricer : public Pricer {
public:
	DigitalPricer( const double dtoday, const double dexp, 
			const double fwd, VolNode *vol, const double strike, 
			const double ir, std::string otype)
			: Pricer( dtoday, dexp, fwd, vol, strike, ir, otype ), 
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

	virtual double price();
};

class BlackStripPricer : public Pricer {
public:
	BlackStripPricer( const double dtoday, 
		const double startDate, const double endDate, 
		const double fwd, VolNode *vol,
		const double strike, const double ir, 
		const std::string otype, const DblVector &hols );
	virtual double price();
	virtual void setFwd( const double fwd);
	virtual void setVol( VolNode *vol);
	virtual void setIR( const double ir);
	virtual void setToday( const double dtoday);

private:
	vector<BlackPricer> _pvec;
	DblVector _bdays;
	DblVector _hols;
	double _sDate;
	double _eDate;
};

class DigitalStripPricer : public Pricer {
public:
	DigitalStripPricer( const double dtoday, 
		const double startDate, const double endDate, 
		const double fwd, VolNode *vol,
		const double strike, const double ir, 
		const std::string otype, const DblVector &hols );
	virtual double price();
	virtual void setFwd( const double fwd);
	virtual void setVol( VolNode *vol);
	virtual void setIR( const double ir);
	virtual void setToday( const double dtoday);

private:
	vector<DigitalPricer> _pvec;
	DblVector _bdays;
	DblVector _hols;
	double _sDate;
	double _eDate;
};

class BarrierPricer : public Pricer {
public:
	BarrierPricer( const double dtoday, const double dexp, 
			const double fwd, VolNode *vol, const double strike, 
			const double barrier, const std::string btype,
			const double ir, std::string otype, const std::string mtype)
			: Pricer( dtoday, dexp, fwd, vol, strike, ir, otype ), 
			  _barrier(barrier), _btype(btype), _mtype(mtype) {}

	virtual double price();

	void setBarrier(const double barrier) { _barrier = barrier; }
	void setBtype(const std::string btype) { _btype = btype; }
	void setMtype(const std::string mtype) { _mtype = mtype; }

	double barrier_() { return _barrier; }
	std::string btype_()   { return _btype;   }
	std::string mtype_()   { return _mtype;   }
private:
	double _barrier;
	std::string _btype;
	std::string _mtype;
};

class BarrierStripPricer : public Pricer {
public:
	BarrierStripPricer( const double dtoday, 
		const double startDate, const double endDate, 
		const double fwd, VolNode *vol, const double strike, 
		const double barrier, const std::string btype,
		const double ir, std::string otype, const std::string mtype,
		const DblVector &hols );
	virtual double price();
	virtual void setFwd( const double fwd);
	virtual void setVol( VolNode *vol);
	virtual void setIR( const double ir);
	virtual void setToday( const double dtoday);

	void setBarrier(const double barrier) { _barrier = barrier; }
	void setBtype(const std::string btype) { _btype = btype; }
	void setMtype(const std::string mtype) { _mtype = mtype; }

	double barrier_() { return _barrier; }
	std::string btype_()   { return _btype;   }
	std::string mtype_()   { return _mtype;   }

private:
	vector<BarrierPricer> _pvec;
	DblVector _bdays;
	DblVector _hols;
	double _sDate;
	double _eDate;
	double _barrier;
	std::string _btype;
	std::string _mtype;
};
#endif