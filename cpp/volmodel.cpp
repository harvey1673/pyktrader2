#include "volmodel.h"

double SamuelsonFactor(double a, double b, double t, double T, double mat)
{
	double factor1 = std::sqrt(1 + 2 * a * ExpIntegral(b, T - t) +
							a*a*ExpIntegral( 2*b, T - t));
	double tdiff = T - mat;
	double factor2 = std::sqrt(1 + 2 * a * std::exp( -tdiff * b) * ExpIntegral(b, mat - t) + 
							a*a*std::exp( -2*b*tdiff) * ExpIntegral( 2*b, mat - t));
	return factor2/factor1;
}

double VolNode::expiry_()
{
	return this->time2expiry_(this->dtoday_(), this->dexp_());
}

double VolNode::time2expiry_(const double dtoday, const double dexp)
{
	if ( _accrual == "act365") 
		return (dexp - dtoday)/365.0;
	else {
		double ndays = NumBusDays(dtoday, dexp, CHN_Holidays);
		if (ndays >= 1)
			ndays = ndays - GetDayFraction(dtoday, _accrual) + GetDayFraction(dexp, _accrual) - 1;
		return ndays/245.0;
	}
}

double VolNode::nextwkday_(const double dtoday)
{
	if ( _accrual == "act365") 
		return dtoday + 1;
	else
		return NextBusDay(dtoday, CHN_Holidays);
}

double SamuelVolNode::GetVolByMoneyness(const double ratio, const double dmat)
{	
	double vol = this->atmVol_();
	double T = this->dexp_()/365.0;
	double t = this->dtoday_()/365.0;
	double mat = dmat / 365.0;
	double a = this->alpha_();
	double b = this->beta_();

	if (T <= t)
		return vol;
	else
		return vol * SamuelsonFactor(a,b,t,T, mat);
}

double SamuelVolNode::GetInstVol(const double d)
{
	double vol = this->atmVol_();
	double T = this->dexp_()/365.0;
	double t = d/365.0;
	double a = this->alpha_();
	double b = this->beta_();
	if (T <= t)
		return vol;
	else
		return vol * ( 1 + a * std::exp(-b*(T-t)));
}

void Delta5VolNode::setAtm( double atm ) 
{
	delete _interp;
	VolNode::setAtm( atm );
	initialize();
}

void Delta5VolNode::initialize()
{
	double expiry = this->expiry_();
	DblVector xs(5,0.0), ys(5, 0.0);
	double atm = this->atmVol_(); 

	xs[0] = atm * (0.5 * atm * expiry - std::sqrt(expiry) * norminv(0.9));
	xs[1] = atm * (0.5 * atm * expiry - std::sqrt(expiry) * norminv(0.75));
	xs[2] = 0;
	xs[3] = atm * (0.5 * atm * expiry - std::sqrt(expiry) * norminv(0.25));
	xs[4] = atm * (0.5 * atm * expiry - std::sqrt(expiry) * norminv(0.1));

	ys[0] = atm + _d90Vol;
	ys[1] = atm + _d75Vol;
	ys[2] = atm;
	ys[3] = atm + _d25Vol;
	ys[4] = atm + _d10Vol;	
	_interp = new ConvInterpolator(xs, ys, _omega);
}

Delta5VolNode::Delta5VolNode(const double dtoday,
					const double dexp,
					const double fwd,
					const double atm, 
					const double v90, 
					const double v75, 
					const double v25, 
					const double v10,
					const std::string accrual):
					VolNode(atm, dtoday, dexp, accrual),
					_fwd(fwd),
					_d90Vol(v90),
					_d75Vol(v75),
					_d25Vol(v25),
					_d10Vol(v10),
					_omega(0.75) 
{
	initialize();
}

double Delta5VolNode::GetVolByStrike(const double strike, const double dmat) {
	double atmvol = this->atmVol_();
	double expiry = this->expiry_();

	if ( (expiry <= 0) || (strike <= 0) )
		return atmvol;
	else
		return this->GetVolByMoneyness( std::log(strike/this->fwd_()), dmat );
}

double Delta5VolNode::GetVolByDelta(const double delta, const double dmat) {
	double atmvol = this->atmVol_();
	double expiry = this->expiry_();

	if ( (expiry <= 0))
		return atmvol;
	else {
		double logmoneyness = atmvol * (0.5 * atmvol * expiry - std::sqrt(expiry) * norminv(delta));
		return this->GetVolByMoneyness( logmoneyness, dmat );
	}
}

double Delta5VolNode::GetVolByMoneyness(const double xr, const double dmat) 
{
	if ( (this->expiry_() <=0))
		return this->atmVol_();
	else
		return _interp->value(xr);
}

SamuelDelta5VolNode::SamuelDelta5VolNode(const double dtoday,
				const double dexp, 
				const double fwd,
				const double atm, 
				const double v90, 
				const double v75, 
				const double v25, 
				const double v10,
				const double alpha,
				const double beta,
				const std::string accrual):
				Delta5VolNode(dtoday, dexp, fwd, atm, v90, v75, v25, v10, accrual),
				_alpha(alpha), _beta(beta){}

double SamuelDelta5VolNode::GetVolByMoneyness(const double ratio, const double dmat)
{
	double impvol = Delta5VolNode::GetVolByMoneyness(ratio);
	double T = this->dexp_()/365.0;
	double t = this->dtoday_()/365.0;
	double mat = dmat / 365.0;
	double a = this->alpha_();
	double b = this->beta_();

	if (T <= t)
		return impvol;
	else
		return impvol * SamuelsonFactor(a,b,t,T, mat);
}

double SamuelDelta5VolNode::GetInstVol(const double d)
{
	double vol = this->atmVol_();
	double T = this->dexp_()/365.0;
	double t = d/365.0;
	double a = this->alpha_();
	double b = this->beta_();
	if (T <= t)
		return vol;
	else
	{
		double factor = std::sqrt(1 + 2 * a * ExpIntegral(b, T - t) + 
							a*a*ExpIntegral( 2*b, T - t));
		return vol / factor * ( 1 + a * std::exp(-b*(T-t)));
	}
}