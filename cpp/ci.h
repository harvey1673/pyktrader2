#ifndef CI_H
#define CI_H

#include <cmath>
#include "normdist.h"
#include "math_utils.h"
#include "lusolve.h"

class ConvInterpolator {
public:
	ConvInterpolator(const DblVector &xs, const DblVector &ys, const double omega); 
	double value( double xi );
private:
	void CalcWeights( DblVector & w, double x);
	DblVector _xs;
	DblVector _ys;
	DblVector _proxyY;

	double _stdev;
};

#endif