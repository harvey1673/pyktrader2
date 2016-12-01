#include "euopt.h"

double BlackPrice(double F,double K,double vol,double t_exp,double df, std::string PutCall) {
	if (t_exp <=0) {
		if ((PutCall == "C") || (PutCall =="c"))
			return ((F>K)? F-K : 0);
		else
			return ((K>F)? K-F : 0);
	}

	double d1 = (std::log(F/K) + (vol*vol/2.0)*t_exp)/vol/std::sqrt(t_exp);
	double d2 = d1 - vol * std::sqrt(t_exp);
	double BlackCall = F * normcdf(d1) - K*normcdf(d2);
	if ((PutCall == "C") || (PutCall =="c"))
		return BlackCall*df;
	else 
		return (BlackCall - F + K)*df;
}

double BlackScholesPrice(double S,double K,double vol,double t_exp,double rf, double rd, std::string PutCall) {
	double dd = std::exp(-t_exp*rd);
	double df = std::exp(-t_exp*rf);
	if (t_exp <=0) {
		if ((PutCall == "C") || (PutCall =="c"))
			return ((S*dd>K*df)? S*dd-K*df : 0);
		else
			return ((K*df>S*dd)? K*df-S*dd : 0);
	}

	double d1 = (std::log(S/K) + (rf-rd+0.5*vol*vol)*t_exp)/vol/std::sqrt(t_exp);
	double d2 = d1 - vol * std::sqrt(t_exp);
	double BSCall = S*dd*normcdf(d1)-K*df*normcdf(d2);
	if ((PutCall == "C") || (PutCall =="c"))
		return BSCall;
	else 
		return (BSCall - S*dd + K*df);
}

double BlackDelta(double F,double K,double vol,double t_exp,double df, std::string PutCall)
{
	if (t_exp <=0) {
		if ((PutCall == "C") || (PutCall =="c"))
			return ((F>K)? 1 : 0);
		else
			return ((K>F)? -1 : 0);
	}

	double d1 = (std::log(F/K) + (vol*vol/2.0)*t_exp)/vol/std::sqrt(t_exp);
	if ((PutCall == "C") || (PutCall =="c"))
		return normcdf(d1)*df;
	else 
		return (normcdf(d1)-1)*df;
}

double BSDigitalPrice(double F,double K,double vol,double t_exp,double df, std::string PutCall) {
	if (t_exp <=0) {
		if ((PutCall == "C") || (PutCall =="c"))
			return ((F>K)? 1 : 0);
		else
			return ((K>F)? 1 : 0);
	}

	double d1 = (std::log(F/K) + (vol*vol/2.0)*t_exp)/vol/std::sqrt(t_exp);
	double d2 = d1 - vol * std::sqrt(t_exp);
	if ((PutCall == "C") || (PutCall =="c"))
		return normcdf(d2)*df;
	else 
		return normcdf(-d2)*df;
}

double BachelierPrice(double F,double K,double vol,double t_exp,double df, std::string PutCall) {
	if (t_exp <=0) {
		if ((PutCall == "C") || (PutCall =="c"))
			return ((F>K)? F-K : 0);
		else
			return ((K>F)? K-F : 0);
	}

	double d = (F-K)/vol/std::sqrt(t_exp);
	double CallPrice = ( F - K) * normcdf(d) + vol * std::sqrt(t_exp) * normpdf(d);
	if ((PutCall == "C") || (PutCall =="c"))
		return CallPrice*df;
	else 
		return (CallPrice - F + K) * df;
}

double BlackImpliedVol(double MktPrice, double F,double K,double r,double T, std::string PutCall) {
	double midP = 0.0;
	double a = 0.001;
	double b = 1.0;
	double tol = 1e-6;
	int MaxIter = 400;
	double df = std::exp(-r*T);

	double midCdif = 0.0;
	double  lowCdif = MktPrice - BlackPrice(F,K,a,T,df,PutCall);
	double highCdif = MktPrice - BlackPrice(F,K,b,T,df,PutCall);
	if (lowCdif*highCdif > 0.0) {
		double Temp = lowCdif;
		lowCdif = highCdif;
		highCdif = Temp;
	}
	else
		for (int i=0; i <= MaxIter; i++ ) {
			midP = (a + b) / 2.0;
			midCdif = MktPrice - BlackPrice(F,K,midP,T,df,PutCall);
			if ( std::abs(midCdif) < tol )
				break;
			else {
				if (midCdif>0.0) a = midP;
				else b = midP;
			}
		}

	if ( midCdif >= tol )
		return -1;
	else
		return midP;
}

double BSImpliedVol(double MktPrice, double S,double K,double r,double T, std::string PutCall) {
	double midP = 0.0;
	double a = 0.001;
	double b = 1.0;
	double tol = 1e-6;
	int MaxIter = 400;
	double df = std::exp(-r*T);

	double midCdif = 0.0;
	double  lowCdif = MktPrice - BlackScholesPrice(S,K,a,T,r,0,PutCall);
	double highCdif = MktPrice - BlackScholesPrice(S,K,b,T,r,0,PutCall);
	if (lowCdif*highCdif > 0.0) {
		double Temp = lowCdif;
		lowCdif = highCdif;
		highCdif = Temp;
	}
	else
		for (int i=0; i <= MaxIter; i++ ) {
			midP = (a + b) / 2.0;
			midCdif = MktPrice - BlackScholesPrice(S,K,midP,T,r,0,PutCall);
			if ( std::abs(midCdif) < tol )
				break;
			else {
				if (midCdif>0.0) a = midP;
				else b = midP;
			}
		}

	if ( midCdif >= tol )
		return -1;
	else
		return midP;
}

double BachelierImpliedVol(double MktPrice, double F,double K,double r,double T, std::string PutCall) {
	double midP = 0.0;
	double a = 0.01;
	double b = 1000.0;
	double tol = 1e-6;
	int MaxIter = 400;
	double df = std::exp(-r*T);

	double midCdif = 0.0;
	double  lowCdif = MktPrice - BachelierPrice(F,K,a,T,df,PutCall);
	double highCdif = MktPrice - BachelierPrice(F,K,b,T,df,PutCall);
	if (lowCdif*highCdif > 0.0) {
		double Temp = lowCdif;
		lowCdif = highCdif;
		highCdif = Temp;
	}
	else
		for (int i=0; i <= MaxIter; i++ ) {
			midP = (a + b) / 2.0;
			midCdif = MktPrice - BachelierPrice(F,K,midP,T,df,PutCall);
			if ( std::abs(midCdif) < tol )
				break;
			else {
				if (midCdif>0.0) a = midP;
				else b = midP;
			}
		}

	if ( midCdif >= tol )
		return -1;
	else
		return midP;
}