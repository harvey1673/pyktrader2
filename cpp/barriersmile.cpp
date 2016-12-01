#include "barriersmile.h"

double SmileToLognormal(double p, double stdev, DblVector& Strikes, DblVector& CDFs)
{
	double NN = Strikes.size();
	double cdf = 0.5;
	if (p <= Strikes[0] )
		cdf = 1e-6;
	else if ( p >= Strikes[NN-1] )
		cdf = 1 - 1e-6;
	else {
		int left = 0;
		int right = (int) CDFs.size()-1;
		int mid;

		while (right - left > 1)
		{
			mid = (left + right)/2;
			if (p < Strikes[mid])
				right = mid;
			else
				left = mid;
		}
		cdf = CDFs[left] + (p - Strikes[left])/(Strikes[right] - Strikes[left])*(CDFs[right] - CDFs[left]);	
	}
	double logprice = norminv( cdf ) * stdev - 0.5 * stdev * stdev;
	return std::exp(logprice);
}

double BarrierSmilePricer::price()
{
	VolNode *vol = this->vol_();
	double atm = vol->atmVol_();
	double fwd = this->fwd_();
	double strike = this->strike_();	
	double barrier = this->barrier_();
	double dexp = vol->dexp_();
	double texp = (this->dexp_() - this->dtoday_())/365;
	double df = std::exp(-this->irate_()*texp);
	std::string otype = this->otype_();
	std::string btype = this->btype_();
	std::string mtype = this->mtype_();


	if ((btype.at(1)=='o') && (((btype.at(0) == 'd') && (fwd <= barrier)) || 
		((btype.at(0) == 'd') && (fwd <= barrier))))
		return 0.0;

	if ( mtype == "d" ) {
		double discreteAdj = std::exp( 0.5826 * atm / std::sqrt(252.0));
		if ( fwd > barrier )
		{
			barrier = barrier / discreteAdj;
		}
		else if ( fwd < barrier )
		{
			barrier = barrier * discreteAdj;
		}
	}

	unsigned int nSteps = 2 * _nSideSteps + 1;
	DblVector strikes(nSteps);
	DblVector vols(nSteps);
	DblVector raw_cdf(nSteps);

	for (unsigned int i = 0; i < 2 * _nSideSteps + 1; ++i)
		strikes[i] = fwd * std::exp( (double(i)/double(_nSideSteps)-1) * _nSigmas * std::sqrt(texp) * atm);

	double last_call, last_put; 
	for (unsigned int i = 0; i < _nSideSteps+1; ++i)
	{	
		double z = std::log(strikes[_nSideSteps -i]/fwd);	
		double v = vol->GetVolByMoneyness(std::log(strikes[_nSideSteps -i]/fwd), dexp);
		double curr_put =  BlackPrice( fwd, strikes[_nSideSteps -i], v, texp, 1, "p");
		z = std::log(strikes[_nSideSteps + i]/fwd);	
		v = vol->GetVolByMoneyness(std::log(strikes[_nSideSteps +i]/fwd), dexp);
		double curr_call =  BlackPrice( fwd, strikes[_nSideSteps + i], v, texp, 1, "c");
		if (i > 0)
		{
			raw_cdf[_nSideSteps - i] = (last_put - curr_put)/(strikes[_nSideSteps - i + 1] - strikes[_nSideSteps - i]);
			raw_cdf[_nSideSteps - 1 + i] = 1 - (last_call - curr_call)/(strikes[_nSideSteps + i] - strikes[_nSideSteps -1 + i]);
		}		
		last_call = curr_call;
		last_put = curr_put;
	}

	DblVector cdfs(nSteps);
	cdfs[0] = 0.0;
	cdfs[nSteps-1] = 1.0;

	for (int i = 1; i < nSteps-1; ++i)
		cdfs[i] = (raw_cdf[i-1]+raw_cdf[i])/2;

	double auxSum = 0.0;
	for (unsigned int i = 1; i< cdfs.size(); ++i )
	{
		double thisPrice = 0.5 * ( strikes[i-1] + strikes[i] );
		auxSum += thisPrice * thisPrice * (cdfs[i] - cdfs[i-1]);
	}

	double stdDev = std::sqrt(std::log(auxSum/(fwd * fwd)));
	double invStdDev = 1.0/stdDev;

	double barrier0, fwd0;
	
	barrier0 = SmileToLognormal(barrier, stdDev, strikes, cdfs);
	fwd0 = SmileToLognormal(fwd, stdDev, strikes, cdfs);
	double imageWeight = fwd0/barrier0;
	double cdfCutoff = 1e-6;

	double optionPrice = 0.0;
	bool previousFIsSet = false;
	double previousF0 = 0.0;
	const double invSqrt2Pi = 0.39894228040143267793994605993;

	for ( unsigned int i = 1; i < strikes.size(); ++i )
	{
		if (cdfs[i] < cdfCutoff || cdfs[i] > 1.0 - cdfCutoff)
			continue;
		if ( !previousFIsSet ) {
			double prevSmilelessD2 = norminv( cdfs[i-1] );
			previousF0 = fwd0 * std::exp(stdDev * prevSmilelessD2 - 0.5 * stdDev * stdDev);
			previousFIsSet = true;
		}

		double smilelessD2 = norminv(cdfs[i]);
		double F0 = fwd0 * std::exp(stdDev * smilelessD2 - 0.5 * stdDev * stdDev);
		double aux1 = smilelessD2;
		double pdf1 = invSqrt2Pi * invStdDev * std::exp(-0.5*aux1*aux1)/F0;
		double aux2 = smilelessD2 + 2.0 * std::log(fwd0/barrier0)/stdDev;
		double pdf2 = invSqrt2Pi * invStdDev * std::exp(-0.5*aux2*aux2)/F0;

		double optPayoff;
		if (otype == "c")
			optPayoff = (strikes[i]>strike)? (strikes[i]-strike): 0.0;
		else
			optPayoff = (strike>strikes[i])? (strike - strikes[i]): 0.0;

		bool barrierHit;
		if (((fwd0>=barrier0) && (btype.at(0)=='u')) || ((fwd0<=barrier0) && (btype.at(0)=='d')))
			barrierHit = true;
		else
			barrierHit = false;

		if (btype.at(1) == 'o') 
		{
			if (((btype.at(0) == 'd') && ( F0 > barrier0 )) 
				|| ((btype.at(0) == 'u') && ( F0 < barrier0)))
				optionPrice += ( F0 - previousF0 ) * ( pdf1 - imageWeight * pdf2) * optPayoff;
		} 
		else 
		{
			if ((((btype.at(0) == 'd') && ( F0 > barrier0 )) 
				|| ((btype.at(0) == 'u') && ( F0 < barrier0))) && !barrierHit)
				optionPrice += (F0 - previousF0)*(imageWeight*pdf2)*optPayoff;
			else if (((btype.at(0)=='d') && ( F0 < barrier0)) 
				|| ((btype.at(0) == 'u') && ( F0 > barrier0 ) 
				|| barrierHit))
                optionPrice += (F0 - previousF0)*pdf1*optPayoff;
		}
		previousF0 = F0;
	}
	return optionPrice;
}