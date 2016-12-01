#ifndef MC_H
#define MC_H

#include <iostream>
#include <math.h>
#include <stdlib.h>
#include "math_utils.h"
#include "volmodel.h"
#include "normdist.h"
#include "euopt.h"

class MCPathGenerator{
public:
	MCPathGenerator(int npath, double dstart, double dend, DblVector hols, double fwd, VolNode *vol, bool useAntithetic);
	double& operator()(int i, int j) { return _data[i][j]; }
	double dStart_() { return _dStart; }
	double dEnd_() { return _dEnd; }
	int nPaths_() { return _nPaths; }
	int nDays_() { return _nDays; }
	double fwd_() { return _fwd; }
	VolNode* vol_() { return _vol; }
	DblVector& simDays_() { return _bdays; }
	DblMatrix2D& data_() { return _data; }

	void setPaths(int npaths) { _nPaths = npaths; }
	void setHolidays(DblVector hols) { _hols = hols; }
	void setFwd( const double fwd) { _fwd = fwd; }
	void setVol( VolNode *vol) { _vol = vol; }
	void setStart( const double dstart);
	void setEnd( const double dend) { _dEnd = dend; }
	void genRandNumber();
	virtual void calcPaths();
private:
	bool _useAntithetic;
	double _fwd;
	VolNode *_vol;
	int _nPaths;
	double _dStart;
	double _dEnd;
	DblVector _hols;
	DblVector _bdays;
	int _nDays;
	DblMatrix2D _rand;
	DblMatrix2D _data;
};

class MCSmilePathGen : public MCPathGenerator{
public:
	MCSmilePathGen(int npath, double dstart, double dend, DblVector hols, double fwd, VolNode *vol, bool useAntithetic, double nSigma, int nSideStep);
	void calcCDF();
	double convertLNToSmile(double p, double d, DblVector& Strikes, DblVector& CDFs);
	virtual void calcPaths();
private:
	DblVector _strikes;
	DblVector _cdfs;
};

#endif
