#include "ci.h"

ConvInterpolator::ConvInterpolator( const DblVector &xs, 
					const DblVector &ys, const double omega):
					_xs(xs), _ys(ys) 
{
	int dim = xs.size();
	double xmin = 1e8;
	_proxyY.resize(dim);

	for (int i = 0; i < dim-1; ++i)
		xmin = std::min( _xs[i+1] - _xs[i], xmin );

	_stdev = omega * xmin;

	DblMatrix2D A;
	resizeMatrix(A, dim, dim);
	for (int i=0; i<dim; ++i)
		CalcWeights( A[i], _xs[i] );

	LuSolve( _proxyY, A, _ys);
}

void ConvInterpolator::CalcWeights( DblVector & w, double xr) {
	int dim = _xs.size();
	DblVector npdf(dim, 0.0), ncdf(dim, 0.0), xx_adj(dim, 0.0);
	DblVector diff_pdf(dim-1, 0.0), diff_cdf(dim-1, 0.0);
	for (int i = 0; i < dim; ++i) {
		xx_adj[i] = (xr - _xs[i]);
		npdf[i] = normpdf( -xx_adj[i]/_stdev) * _stdev;
		ncdf[i] = normcdf( -xx_adj[i]/_stdev);
	}

	for (int i = 0; i < dim-1; ++i) {
		diff_pdf[i] = npdf[i+1] - npdf[i];
		diff_cdf[i] = ncdf[i+1] - ncdf[i];
	}

	for (int i = 1; i < dim-1; ++i) {
		w[i] = ( -xx_adj[i+1]* diff_cdf[i] + diff_pdf[i])/(_xs[i+1]-_xs[i])
				+ ( xx_adj[i-1]* diff_cdf[i-1] - diff_pdf[i-1])/(_xs[i]-_xs[i-1]);
	}

	w[0] = ncdf[0]+ (-xx_adj[1] * diff_cdf[0] + diff_pdf[0] )/(_xs[1]-_xs[0]);
	w[dim-1] = 1- ncdf[dim-1] + ( xx_adj[dim-2]*diff_cdf[dim-2] - diff_pdf[dim-2])/(_xs[dim-1]-_xs[dim-2]);
}

double ConvInterpolator::value( double xr ) 
{
	int dim = _xs.size();
	DblVector w(dim, 0.0);
	CalcWeights(w, xr);

	double y = 0.0;
	for (int i=0; i<dim; ++i)
		y += w[i] * _proxyY[i];

	return y;
}