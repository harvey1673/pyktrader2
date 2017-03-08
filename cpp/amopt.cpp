#include "amopt.h"
#include "euopt.h"

const int bin_tree_nstep = 128;

double american_prem_fut_btree(double F,double K,double vol,double t_exp,double df, std::string PutCall) 
{
	if (t_exp < 0.0) return 0.0;

	double fut;
	double stk;

	if ((PutCall == "C") || (PutCall =="c")) {
		fut = K;
		stk = F;
	} else {
		fut = F; 
		stk = K; 
	}

	int nstep = (int) (2 * t_exp * bin_tree_nstep);
	if (nstep < bin_tree_nstep ) 
		nstep = bin_tree_nstep;
	else if (nstep > 10 * bin_tree_nstep)
		nstep = 10 * bin_tree_nstep;

	const double dt = t_exp/nstep;
	const double dvol = vol * std::sqrt(dt);
	const double tem = std::exp(dvol*dvol);
	const double u = (tem + 1.0 + std::sqrt((tem+3.0)*(tem-1.0)))*0.5;
	const double logu = std::log(u);
	const double p = 1.0/(1.0+u);
	const double q = 1.0- p;
	const double ddisc = std::exp(std::log(df)/nstep);
	DblVector Farray(nstep*2+1);

	for (int i = 0; i<= 2*nstep; ++i) {
		if (i==0)
			Farray[i] = std::exp(-nstep*logu);
		else
			Farray[i] = Farray[i-1] * u;
	}

	const double normK = stk/fut;

	DblVector aopay(nstep);
	DblVector eopay(nstep);

	for ( int i = 0; i < nstep; ++i ) {
		const double ff = Farray[i+i+1];
		const double exer_value = normK - ff;

		if ( dvol < std::numeric_limits<double>::epsilon() ) {
			aopay[i] = eopay[i] = exer_value * ddisc;
		} else {
			const double d1 = std::log( ff / normK ) / dvol + dvol * 0.5;
			const double d2 = d1 - dvol;
			aopay[i] = eopay[i] = ( normK * normcdf(-d2) - ff * normcdf(-d1) ) * ddisc;
		}

		if ( aopay[i] < exer_value ) 
			aopay[i] = exer_value;
	}

	for ( int j = nstep - 2; j>=0; --j ) {
		for ( int i = 0; i<=j; ++i ) {
			const double exer_value = normK - Farray[i+i+nstep-j];
			eopay[i] = ddisc * ( p * eopay[i+1] + q * eopay[i] );
			aopay[i] = ddisc * ( p * aopay[i+1] + q * aopay[i] );
			if (aopay[i] < exer_value )
				aopay[i] = exer_value;
		}
	}
	return F * ( aopay[0] - eopay[0] );
}

double AmericanOptFutPrice(double F,double K,double vol,double t_exp,double df, std::string PutCall) 
{
	double european = BlackPrice( F, K, vol, t_exp, df, PutCall); 
	double am_prem = american_prem_fut_btree( F, K, vol, t_exp, df, PutCall); 
	return (european + am_prem);
}

double AmericanImpliedVol(double MktPrice, double F,double K,double r,double T, std::string PutCall) {
	double df = std::exp(-r*T);
	double euiv = BlackImpliedVol(MktPrice, F, K, r, T, PutCall);
	double a = 0.5 * euiv;
	double b = 1.1 * euiv;
	double lowdiff = AmericanOptFutPrice(F,K,a,T,df,PutCall) - MktPrice;
	double highdiff = AmericanOptFutPrice(F,K,b,T,df,PutCall) - MktPrice;
	double midv = euiv;
	double middiff = AmericanOptFutPrice(F,K,euiv,T,df,PutCall) - MktPrice; 
	double tol = 1e-6;
	int MaxIter = 100;

	for (int i=0; i <= MaxIter; ++i) {
		if ( std::abs(middiff) < tol )
			break;
		else {
			if (middiff > 0) {
				b = midv;
				highdiff = middiff;
			} 
			else {
				a = midv;
				lowdiff = middiff;
			}

			midv = (highdiff * a - lowdiff * b)/(highdiff - lowdiff);
			middiff = AmericanOptFutPrice(F,K,midv,T,df,PutCall) - MktPrice;
		}
	}

	if ( std::abs(middiff) >= tol )
		return -1;
	else
		return midv;
}

