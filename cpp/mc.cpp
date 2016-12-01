#include "mc.h"

MCPathGenerator::MCPathGenerator(int npath, double dstart, double dend, DblVector hols, 
								 double fwd, VolNode *vol, bool useAntithetic):
								_nPaths(npath), _dStart(dstart), _dEnd(dend), _hols(hols), 
								_fwd(fwd), _vol(vol), _useAntithetic(useAntithetic)
{
	_bdays = businessDays(dstart, dend, hols);
	_nDays = _bdays.size();
	resizeMatrix(_rand, npath, _nDays-1);
	resizeMatrix(_data, npath, _nDays);
}

void MCPathGenerator::setStart( const double dstart) 
{
	_dStart = dstart;
	_bdays = businessDays(_dStart, _dEnd, _hols);
	_nDays = _bdays.size();
}

void MCPathGenerator::genRandNumber()
{
	int nPath = this->nPaths_();
	if (_useAntithetic)
		nPath = nPath/2;
	DblVector simDays = this->simDays_();

	for (int i = 0; i< nPath; ++i)
		for (int j = 0; j< simDays.size()-1; ++j)
		{
			_rand[i][j] = norm_rand();
			if (_useAntithetic)
				_rand[i+ nPath][j] = -_rand[i][j];
		}
}

void MCPathGenerator::calcPaths()
{
	int nPath = this->nPaths_();
	DblVector simDays = this->simDays_();

	for (int j = 0; j< simDays.size(); ++j)
		for (int i = 0; i< nPath; ++i)
		{
			if (j == 0) 
			{
				_data[i][j] = _fwd;
				continue;
			}
			else
			{
				double dtoday = simDays[j];
				double v = this->vol_()->GetInstVol(dtoday);
				double dt = (simDays[j] - simDays[j-1])/365.0;
				_data[i][j] = _data[i][j -1] * std::exp( -0.5*v*v*dt + v*std::sqrt(dt)*_rand[i][j-1]);
			}
		}
}

MCSmilePathGen::MCSmilePathGen(int npath, double dstart, double dend, DblVector hols, 
								double fwd, VolNode *vol, bool useAntithetic, 
								double nSigma=6.0, int nSideStep=4800):
								MCPathGenerator(npath, dstart, dend, hols, fwd, vol, useAntithetic)
{
	DblVector calls(nSideStep+1), puts(nSideStep+1);
	for (int i = 0; i< 2*nSideStep+1; ++i) 
		_strikes.push_back( nSigma * (i - nSideStep)/nSideStep );

	calcCDF();

}

void MCSmilePathGen::calcCDF()
{
	double fwd = this->fwd_();
	VolNode* vol = this->vol_();
	double atm = vol->atmVol_();

	double nSideStep = int((_strikes.size() -1)/2);
	DblVector raw_cdf(2*nSideStep);	
	double lastopt = 0;
	double dexp = vol->dexp_();
	double texp = vol->expiry_();
	double last_call = 0.0;
	double last_put = 0.0;

	DblVector strikes(2*nSideStep+1);
	for (int i = 0; i < 2 * nSideStep + 1; ++i)
		strikes[i] = fwd * std::exp(_strikes[i] * std::sqrt(texp) * atm);

	for (int i = 0; i < nSideStep+1; ++i)
	{	
		double z = std::log(_strikes[nSideStep -i]/fwd);	
		double v = vol->GetVolByMoneyness(std::log(strikes[nSideStep -i]/fwd), dexp);
		double curr_put =  BlackPrice( fwd, strikes[nSideStep -i], v, texp, 1, "p");
		z = std::log(_strikes[nSideStep + i]/fwd);	
		v = vol->GetVolByMoneyness(std::log(strikes[nSideStep +i]/fwd), dexp);
		double curr_call =  BlackPrice( fwd, strikes[nSideStep + i], v, texp, 1, "c");
		if (i > 0)
		{
			raw_cdf[nSideStep - i] = (last_put - curr_put)/(strikes[nSideStep - i + 1] - strikes[nSideStep - i]);
			raw_cdf[nSideStep - 1 + i] = 1 - (last_call - curr_call)/(strikes[nSideStep + i] - strikes[nSideStep -1 + i]);
		}		
		last_call = curr_call;
		last_put = curr_put;
	}

	_cdfs.resize( 2*nSideStep+1);
	_cdfs[0] = 0.0;
	_cdfs[2*nSideStep] = 1.0;

	for (int i = 1; i < 2*nSideStep; ++i)
		_cdfs[i] = (raw_cdf[i-1]+raw_cdf[i])/2;
}

double MCSmilePathGen::convertLNToSmile(double p, double d, DblVector& Strikes, DblVector& CDFs)
{
	double fwd = this->fwd_();
	VolNode* vol = this->vol_();
	double dtoday = vol->dtoday_();
	double t_mat = (d - dtoday)/365.0;
	if (t_mat <=0)
		return p;

	double v = vol->GetVolByMoneyness(0.0, d);
	double z = (std::log(p/fwd) + 0.5 * v * v * t_mat)/std::sqrt(t_mat)/v;
	double cdf = normcdf(z);
	z = 0.0;
	int left = 0;
	int right = (int) CDFs.size()-1;
	int mid = (left + right)/2;

	while (right - left > 1)
	{
		mid = (left + right)/2;
		if (cdf < CDFs[mid])
			right = mid;
		else
			left = mid;
	}

	z = Strikes[left] + (cdf - CDFs[left])/(CDFs[right] - CDFs[left])*(Strikes[right] - Strikes[left]);	
	return fwd*exp( z * v * std::sqrt(t_mat));
}

void MCSmilePathGen::calcPaths()
{
	DblMatrix2D& data = this->data_();
	MCPathGenerator::calcPaths();
	DblVector days = this->simDays_();
	for (int i = 0; i < this->nPaths_(); ++i)
		for (int j = 0; j  < days.size(); ++j)
			data[i][j] = convertLNToSmile( data[i][j], days[j], _strikes, _cdfs);
}

								