#include<cppinterface.h>

#pragma warning (disable : 4996)
using namespace System;

MyArray CLFitDelta5VolParams( const double dtoday,
					const double dexp,
					const double fwd,
					const MyArray &strikeList,
					const MyArray &volList)
{
	double expiry = (dexp - dtoday)/365.0;
	DblVector xi(strikeList.size());;

	for (size_t i = 0; i < strikeList.size(); ++i)
		xi[i] = std::log(strikeList[i]/fwd);
	
	ConvInterpolator intp( xi, volList, 0.75);

	DblVector volparam(5);
	double atm = intp.value(0);
	
	volparam[0] = atm;

	xi.resize(4);
	xi[0] = 0.9;
	xi[1] = 0.75;
	xi[2] = 0.25;
	xi[3] = 0.1;

	for (size_t i = 0; i < 4; ++i )
		volparam[i+1] = intp.value( atm * (0.5 * atm * expiry - std::sqrt(expiry) * norminv(xi[i])) ) - atm;

	return volparam;
}

double CLSmileVolbyStrike(const double dtoday,
					const double dexp,
					const double fwd,
					const double atm, 
					const double v90, 
					const double v75, 
					const double v25, 
					const double v10,
					const double K)
{
	if (dtoday > dexp )
		THROW_XLW("the expiry date has passed already");

	if ((atm <= 0) || (fwd <= 0) || (K <= 0))
		THROW_XLW("Either price or vol is not positive");

	Delta5VolNode vol(dtoday, dexp, fwd, atm, v90, v75, v25, v10, 0.75);
	return vol.GetVolByStrike(K);
}

double CLSmileVolbyDelta(const double dtoday,
					const double dexp,
					const double fwd,
					const double atm, 
					const double v90, 
					const double v75, 
					const double v25, 
					const double v10,
					const double delta)
{
	if (dtoday > dexp )
		THROW_XLW("the expiry date has passed already");
	if ((atm <= 0) || (fwd <= 0) || (delta < 0))
		THROW_XLW("Either price or vol is not positive");

	Delta5VolNode vol(dtoday, dexp, fwd, atm, v90, v75, v25, v10, 0.75);
	return vol.GetVolByDelta(delta);
}

double CLBlackImpliedVol(const double dtoday, 
					const double dexp, 
					const double fwd, 
					const double strike, 
					const double ir,
					const std::string otype, 
					const double prem)
{
	if (dtoday >= dexp )
		THROW_XLW("the expiry date has passed already");

	if ( (fwd <= 0) || (prem <= 0) )
		THROW_XLW("Either price or premium is not positive");

	if ( (otype!= "c") && (otype!= "C") && (otype!= "p") && (otype!= "P") )
		THROW_XLW("The option type is not recognized");

	double t_exp = (dexp - dtoday)/365.0; 
	return BlackImpliedVol( prem, fwd, strike, ir, t_exp, otype);
}

double CLBachelierImpliedVol(const double dtoday, 
					const double dexp, 
					const double fwd, 
					const double strike, 
					const double ir,
					const std::string otype, 
					const double prem)
{
	if (dtoday >= dexp )
		THROW_XLW("the expiry date has passed already");

	if ( prem <= 0 )
		THROW_XLW("Premium is not positive");

	if ( (otype!= "c") && (otype!= "C") && (otype!= "p") && (otype!= "P") )
		THROW_XLW("The option type is not recognized");

	double t_exp = (dexp - dtoday)/365.0; 
	return BachelierImpliedVol( prem, fwd, strike, ir, t_exp, otype);
}

double CLBlackDelta(const double dtoday, 
					const double dexp, 
					const double fwd,
					const double strike,
					const double vol,
					const double ir, 
					const std::string otype)
{
	if (dtoday >= dexp )
		THROW_XLW("the expiry date has passed already");

	if ((ir < 0) || (fwd <= 0) || (strike <= 0) )
		THROW_XLW("Either price or rate is not positive");

	if ( (otype!= "c") && (otype!= "C") && (otype!= "p") && (otype!= "P") )
		THROW_XLW("The option type is not recognized");

	double t_exp = (dexp - dtoday)/365.0;
	double df = exp(-ir*t_exp);
	return BlackDelta(fwd, strike, vol, t_exp, df, otype);
}

double CLSmileEuroOptPricer(const double dtoday,
					const double dexp,
					const double fwd,
					const double strike,
					const double atm, 
					const double v90, 
					const double v75, 
					const double v25, 
					const double v10,
					const double doptexp,
					const double ir,
					const std::string otype,
					const std::string outflag,
					const double alpha,
					const double beta)
{
	if (dtoday > dexp )
		THROW_XLW("the expiry date has passed already");

	if (dexp > doptexp )
		THROW_XLW("the expiry date is later than option expiry date");

	if (beta < 0)
		THROW_XLW("Beta is less than 0");

	if ((atm <= 0) || (fwd <= 0) || (strike <= 0))
		THROW_XLW("Either price or vol is not positive");

	if ( (otype!= "c") && (otype!= "C") && (otype!= "p") && (otype!= "P") )
		THROW_XLW("The option type is not recognized");

	SamuelDelta5VolNode vol(dtoday, doptexp, fwd, atm, v90, v75, v25, v10, alpha, beta, 0.75);
	BlackPricer bp(dtoday, dexp, fwd, &vol, strike, ir, otype);

	double ret = 0.0;
	if (( "p" == outflag ) || ( "P" == outflag ))
		ret = bp.price();
	else if (( "d" == outflag ) || ( "D" == outflag ))
		ret = bp.delta();
	else if (( "g" == outflag ) || ( "G" == outflag ))
		ret = bp.gamma();
	else if (( "v" == outflag ) || ( "V" == outflag ))
		ret = bp.vega();
	else if (( "t" == outflag ) || ( "T" == outflag ))
		ret = bp.theta();
	else if (( "z" == outflag ) || ( "Z" == outflag ))
		ret = 1;
	else
		THROW_XLW("The output flag is not valid, should be p,d,g,v,t");
	
	return ret;
}

double CLEuroOptStripPricer(const double dtoday,
					const double dstart,
					const double dend,
					const double fwd,
					const double strike,
					const double atm, 
					const double v90, 
					const double v75, 
					const double v25, 
					const double v10,
					const double doptexp,
					const double ir,
					const std::string otype,
					const std::string outflag,
					const MyArray &hols,
					const double alpha,
					const double beta)
{
	if (dtoday >= dend )
		THROW_XLW("the expiry date has passed already");

	if (dend > doptexp )
		THROW_XLW("the end date is later than option expiry date");

	if (beta < 0)
		THROW_XLW("Beta is less than 0");

	if ((atm <= 0) || (fwd <= 0) || (strike <= 0))
		THROW_XLW("Either price or vol is not positive");

	if ( (otype!= "c") && (otype!= "C") && (otype!= "p") && (otype!= "P") )
		THROW_XLW("The option type is not recognized");

	SamuelDelta5VolNode vol(dtoday, doptexp, fwd, atm, v90, v75, v25, v10, alpha, beta, 0.75);
	BlackStripPricer bsp(dtoday, dstart, dend, fwd, &vol, strike, ir, otype, hols);

	double ret = 0.0;
	if (( "p" == outflag ) || ( "P" == outflag ))
		ret = bsp.price();
	else if (( "d" == outflag ) || ( "D" == outflag ))
		ret = bsp.delta();
	else if (( "g" == outflag ) || ( "G" == outflag ))
		ret = bsp.gamma();
	else if (( "v" == outflag ) || ( "V" == outflag ))
		ret = bsp.vega();
	else if (( "t" == outflag ) || ( "T" == outflag ))
		ret = bsp.theta();
	else if (( "z" == outflag ) || ( "Z" == outflag ))
		ret = 3;
	else
		THROW_XLW("The output flag is not valid, should be p,d,g,v,t");	

	return ret;
}

double CLSmileBinOptPricer(const double dtoday,
					const double dexp,
					const double fwd,
					const double strike,
					const double atm, 
					const double v90, 
					const double v75, 
					const double v25, 
					const double v10,
					const double doptexp,
					const double ir,
					const std::string otype,
					const std::string outflag,
					const double alpha,
					const double beta)
{
	if (dtoday > dexp )
		THROW_XLW("the expiry date has passed already");

	if (dexp > doptexp )
		THROW_XLW("the expiry date is later than option expiry date");

	if (beta < 0)
		THROW_XLW("Beta is less than 0");

	if ((atm <= 0) || (fwd <= 0) || (strike <= 0))
		THROW_XLW("Either price or vol is not positive");

	if ( (otype!= "c") && (otype!= "C") && (otype!= "p") && (otype!= "P") )
		THROW_XLW("The option type is not recognized");

	SamuelDelta5VolNode vol(dtoday, doptexp, fwd, atm, v90, v75, v25, v10, alpha, beta, 0.75);
	DigitalPricer dp(dtoday, dexp, fwd, &vol, strike, ir, otype);

	double ret = 0.0;
	if (( "p" == outflag ) || ( "P" == outflag ))
		ret = dp.price();
	else if (( "d" == outflag ) || ( "D" == outflag ))
		ret = dp.delta();
	else if (( "g" == outflag ) || ( "G" == outflag ))
		ret = dp.gamma();
	else if (( "v" == outflag ) || ( "V" == outflag ))
		ret = dp.vega();
	else if (( "t" == outflag ) || ( "T" == outflag ))
		ret = dp.theta();
	else if (( "z" == outflag ) || ( "Z" == outflag ))
		ret = 2;
	else
		THROW_XLW("The output flag is not valid, should be p,d,g,v,t");

	return ret;
}

double CLDigitalStripPricer(const double dtoday,
					const double dstart,
					const double dend,
					const double fwd,
					const double strike,
					const double atm, 
					const double v90, 
					const double v75, 
					const double v25, 
					const double v10,
					const double doptexp,
					const double ir,
					const std::string otype,
					const std::string outflag,
					const MyArray &hols,
					const double alpha,
					const double beta)
{
	if (dtoday >= dend )
		THROW_XLW("the expiry date has passed already");

	if (dend > doptexp )
		THROW_XLW("the end date is later than option expiry date");

	if (beta < 0)
		THROW_XLW("Beta is less than 0");

	if ((atm <= 0) || (fwd <= 0) || (strike <= 0))
		THROW_XLW("Either price or vol is not positive");

	if ( (otype!= "c") && (otype!= "C") && (otype!= "p") && (otype!= "P") )
		THROW_XLW("The option type is not recognized");

	SamuelDelta5VolNode vol(dtoday, doptexp, fwd, atm, v90, v75, v25, v10, alpha, beta, 0.75);
	DigitalStripPricer dsp(dtoday, dstart, dend, fwd, &vol, strike, ir, otype, hols);

	double ret = 0.0;
	if (( "p" == outflag ) || ( "P" == outflag ))
		ret = dsp.price();
	else if (( "d" == outflag ) || ( "D" == outflag ))
		ret = dsp.delta();
	else if (( "g" == outflag ) || ( "G" == outflag ))
		ret = dsp.gamma();
	else if (( "v" == outflag ) || ( "V" == outflag ))
		ret = dsp.vega();
	else if (( "t" == outflag ) || ( "T" == outflag ))
		ret = dsp.theta();
	else if (( "z" == outflag ) || ( "Z" == outflag ))
		ret = 4;
	else
		THROW_XLW("The output flag is not valid, should be p,d,g,v,t");	

	return ret;
}

double CLSprdOptPricer(const double dtoday,
					const double dexp,
					const double fwd,
					const double strike,
					const double atm,
					const double ir,
					const std::string otype,
					const std::string outflag)
{
	if (dtoday > dexp )
		THROW_XLW("The expiry date has passed already");

	if (atm <= 0) 
		THROW_XLW("Dollar vol is not positive");

	if ( (otype!= "c") && (otype!= "C") && (otype!= "p") && (otype!= "P") )
		THROW_XLW("The option type is not recognized");

	VolNode vol(atm, dtoday, dexp);
	BachelierPricer p(dtoday, dexp, fwd, &vol, strike, ir, otype);

	double ret = 0.0;
	if (( "p" == outflag ) || ( "P" == outflag ))
		ret = p.price();
	else if (( "d" == outflag ) || ( "D" == outflag ))
		ret = p.delta();
	else if (( "g" == outflag ) || ( "G" == outflag ))
		ret = p.gamma();
	else if (( "v" == outflag ) || ( "V" == outflag ))
		ret = p.vega();
	else if (( "t" == outflag ) || ( "T" == outflag ))
		ret = p.theta();
	else if (( "z" == outflag ) || ( "Z" == outflag ))
		ret = 5;
	else
		THROW_XLW("The output flag is not valid, should be p,d,g,v,t");

	return ret;
}

double CLBarrierOptFlatVolPricer(const double dtoday,
					const double dexp,
					const double fwd,
					const double strike,
					const double barrier,
					const std::string btype,
					const double atm, 
					const double doptexp,
					const double ir,			
					const std::string otype,
					const std::string mtype,
					const std::string outflag,
					const double alpha,
					const double beta)
{
	if (dtoday > dexp )
		THROW_XLW("the expiry date has passed already");

	if (dexp > doptexp )
		THROW_XLW("the expiry date is later than option expiry date");

	if (beta < 0)
		THROW_XLW("Beta is less than 0");

	if ((atm <= 0) || (fwd <= 0) || (strike <= 0) || (barrier <= 0))
		THROW_XLW("Either price or vol is not positive");

	if ((otype!= "c") && (otype!= "C") && (otype!= "p") && (otype!= "P") )
		THROW_XLW("The option type is not recognized");

	if ( (btype.length() != 2) || ((btype.at(0) != 'D') && (btype.at(0) != 'd') && 
								   (btype.at(0) != 'U') && (btype.at(0) != 'u') && 
								   (btype.at(1) != 'O') && (btype.at(1) != 'o') && 
								   (btype.at(1) != 'I') && (btype.at(1) != 'i'))) 
		THROW_XLW("The barrier type is not recognized, should be one of uo,ui,do,di");

	if ((mtype != "d") && (mtype != "D") && (mtype != "c") && (mtype != "C"))
		THROW_XLW("The barrier monitoring flag is not recognized, c - continusous, d - daily");

	SamuelVolNode vol(dtoday, doptexp, atm, alpha, beta);
	BarrierPricer bp(dtoday, dexp, fwd, &vol, strike, barrier, btype, ir, otype, mtype);

	double ret = 0.0;
	if (( "p" == outflag ) || ( "P" == outflag ))
		ret = bp.price();
	else if (( "d" == outflag ) || ( "D" == outflag ))
		ret = bp.delta();
	else if (( "g" == outflag ) || ( "G" == outflag ))
		ret = bp.gamma();
	else if (( "v" == outflag ) || ( "V" == outflag ))
		ret = bp.vega();
	else if (( "t" == outflag ) || ( "T" == outflag ))
		ret = bp.theta();
	else if (( "z" == outflag ) || ( "Z" == outflag ))
		ret = 6;
	else
		THROW_XLW("The output flag is not valid, should be p,d,g,v,t");

	return ret;
}

double CLBarrierOptSmilePricer(const double dtoday,
					const double dexp,
					const double fwd,
					const double strike,
					const double barrier,
					const std::string btype,
					const double atm, 
					const double v90, 
					const double v75, 
					const double v25, 
					const double v10,
					const double doptexp,
					const double ir,			
					const std::string otype,
					const std::string mtype,
					const std::string outflag,
					const double alpha,
					const double beta)
{
	if (dtoday > dexp )
		THROW_XLW("the expiry date has passed already");

	if (dexp > doptexp )
		THROW_XLW("the expiry date is later than option expiry date");

	if (beta < 0)
		THROW_XLW("Beta is less than 0");

	if ((atm <= 0) || (fwd <= 0) || (strike <= 0) || (barrier <= 0))
		THROW_XLW("Either price or vol is not positive");

	if ((otype!= "c") && (otype!= "C") && (otype!= "p") && (otype!= "P") )
		THROW_XLW("The option type is not recognized");

	if ( (btype.length() != 2) || ((btype.at(0) != 'd') && 
								   (btype.at(0) != 'u') && 
								   (btype.at(1) != 'o') && 
								   (btype.at(1) != 'i'))) 
		THROW_XLW("The barrier type is not recognized, should be one of uo,ui,do,di");

	if ((mtype != "d") && (mtype != "D") && (mtype != "c") && (mtype != "C"))
		THROW_XLW("The barrier monitoring flag is not recognized, c - continusous, d - daily");
	
	SamuelDelta5VolNode vol(dtoday, doptexp, fwd, atm, v90, v75, v25, v10, alpha, beta, 0.75);
	BarrierSmilePricer bp(dtoday, dexp, fwd, &vol, strike, barrier, btype, ir, otype, mtype, 1600, 6.0);

	double ret = 0.0;
	if (( "p" == outflag ) || ( "P" == outflag ))
		ret = bp.price();
	else if (( "d" == outflag ) || ( "D" == outflag ))
		ret = bp.delta();
	else if (( "g" == outflag ) || ( "G" == outflag ))
		ret = bp.gamma();
	else if (( "v" == outflag ) || ( "V" == outflag ))
		ret = bp.vega();
	else if (( "t" == outflag ) || ( "T" == outflag ))
		ret = bp.theta();
	else if (( "z" == outflag ) || ( "Z" == outflag ))
		ret = 8;
	else
		THROW_XLW("The output flag is not valid, should be p,d,g,v,t");

	return ret;
}

double CLBarrierStripPricer(const double dtoday,
					const double dstart,
					const double dend,
					const double fwd,
					const double strike,
					const double barrier,
					const std::string btype,
					const double atm, 
					const double doptexp,
					const double ir,			
					const std::string otype,
					const std::string mtype,
					const std::string outflag,
					const MyArray &hols,
					const double alpha,
					const double beta)
{
	if (dtoday >= dend )
		THROW_XLW("the expiry date has passed already");

	if (dend > doptexp )
		THROW_XLW("the end date is later than option expiry date");

	if (beta < 0)
		THROW_XLW("Beta is less than 0");

	if ((atm <= 0) || (fwd <= 0) || (strike <= 0))
		THROW_XLW("Either price or vol is not positive");

	if ( (otype!= "c") && (otype!= "C") && (otype!= "p") && (otype!= "P") )
		THROW_XLW("The option type is not recognized");

	if ( (btype.length() != 2) || ((btype.at(0) != 'D') && (btype.at(0) != 'd') && 
								   (btype.at(0) != 'U') && (btype.at(0) != 'u') && 
								   (btype.at(1) != 'O') && (btype.at(1) != 'o') && 
								   (btype.at(1) != 'I') && (btype.at(1) != 'i'))) 
		THROW_XLW("The barrier type is not recognized, should be one of uo,ui,do,di");

	if ((mtype != "d") && (mtype != "D") && (mtype != "c") && (mtype != "C"))
		THROW_XLW("The barrier monitoring flag is not recognized, c - continusous, d - daily");

	SamuelVolNode vol(dtoday, doptexp, atm, alpha, beta);
	BarrierStripPricer bsp(dtoday, dstart, dend, fwd, &vol, strike, barrier, btype, ir, otype, mtype, hols );

	double ret = 0.0;
	if (( "p" == outflag ) || ( "P" == outflag ))
		ret = bsp.price();
	else if (( "d" == outflag ) || ( "D" == outflag ))
		ret = bsp.delta();
	else if (( "g" == outflag ) || ( "G" == outflag ))
		ret = bsp.gamma();
	else if (( "v" == outflag ) || ( "V" == outflag ))
		ret = bsp.vega();
	else if (( "t" == outflag ) || ( "T" == outflag ))
		ret = bsp.theta();
	else if (( "z" == outflag ) || ( "Z" == outflag ))
		ret = 7;
	else
		THROW_XLW("The output flag is not valid, should be p,d,g,v,t");

	return ret;
}

int CLCalibHistBreakevenVol( std::string hostname, std::string dbname, std::string tablename, 
									int sprdnum, int expbackdays, int freq, 
									const MyArray &contDates, std::string out_table)
{
	int numCont = contDates.size();
	vector<TimeSeries> ts_vec;
	for (int i = 0; i < numCont; ++i)
		ts_vec.push_back(GetDBTimeSeries(hostname, dbname, tablename, contDates[i]));

	for (int i = 0; i < numCont - sprdnum; ++i)
	{
		for (int j = 0; j < sprdnum; ++j)
		{
			TimeSeries ts = GetTSWeightedSum(ts_vec[i], ts_vec[i+j+1], 1,-1);
			DblVector dates = ts.date_();
			double expiry = dates[dates.size() - expbackdays - 1];			
			HistVolCalculator histvol = HistVolCalculator(ts, expiry, freq, 12);
			DblVector BEvols = histvol.BreakevenVols();
			WriteVolResultsToDB(hostname, dbname, out_table, BEvols, "SB", "CSOBreakeven", freq, contDates[i], j+1);
		}
	}
	return 0;
}

double CLFXEuroOptPricer(const double dtoday,
					const double dexp,
					const double fwd,
					const double strike,
					const double atm, 
					const double doptexp,
					const double ir,
					const std::string otype,
					MyArray& fxFwdTenors,
					MyArray& fxFwds,
					MyArray& fxVolTenors,
					MyArray& fxVols,
					const double corr,
					const std::string outflag,
					const double alpha,
					const double beta)
{
	if (dtoday > dexp )
		THROW_XLW("the expiry date has passed already");

	if (dexp > doptexp )
		THROW_XLW("the expiry date is later than option expiry date");

	if (beta < 0)
		THROW_XLW("Beta is less than 0");

	if ((atm <= 0) || (fwd <= 0) || (strike <= 0))
		THROW_XLW("Either price or vol is not positive");

	if ( (otype!= "c") && (otype!= "C") && (otype!= "p") && (otype!= "P") )
		THROW_XLW("The option type is not recognized");

	if ( (fxFwdTenors.size()!=fxFwds.size()) || (fxVolTenors.size()!=fxVols.size()) )
		THROW_XLW("FX tenor or fwd or vol inputs are not same size");

	FXSamuelVolNode vol(dtoday, doptexp, atm, alpha, beta, fxVolTenors, fxVols, corr);
	FXBlackPricer fbp(dtoday, dexp, fwd, &vol, strike, ir, otype, fxFwdTenors, fxFwds);
	double ret;
	if (( "p" == outflag ) || ( "P" == outflag ))
		ret = fbp.price();
	else if (( "d" == outflag ) || ( "D" == outflag ))
		ret = fbp.delta();
	else if (( "g" == outflag ) || ( "G" == outflag ))
		ret = fbp.gamma();
	else if (( "v" == outflag ) || ( "V" == outflag ))
		ret = fbp.vega();
	else if (( "t" == outflag ) || ( "T" == outflag ))
		ret = fbp.theta();
	else if (( "fv" == outflag ) || ( "FV" == outflag ))
		ret = fbp.fxvega();
	//else if (( "fvs" == outflag ) || ( "FV" == outflag ))
	//	ret = fbp.fxvegas();		
	else if (( "fd" == outflag ) || ( "FD" == outflag ))
		ret = fbp.fxdelta();
	//else if (( "fds" == outflag ) || ( "FDS" == outflag ))
	//	ret = fbp.fxdeltas();
	else if (( "z" == outflag ) || ( "Z" == outflag ))
		ret = 8;
	else
		THROW_XLW("The output flag is not valid, should be p,d,g,v,t,fd,fds,fv,fvs");
	
	return ret;
}

MyArray CLFXEuroOptRisks(const double dtoday,
					const double dexp,
					const double fwd,
					const double strike,
					const double atm, 
					const double doptexp,
					const double ir,
					const std::string otype,
					MyArray& fxFwdTenors,
					MyArray& fxFwds,
					MyArray& fxVolTenors,
					MyArray& fxVols,
					const double corr,
					const std::string outflag,
					const double alpha,
					const double beta)
{
	if (dtoday > dexp )
		THROW_XLW("the expiry date has passed already");

	if (dexp > doptexp )
		THROW_XLW("the expiry date is later than option expiry date");

	if (beta < 0)
		THROW_XLW("Beta is less than 0");

	if ((atm <= 0) || (fwd <= 0) || (strike <= 0))
		THROW_XLW("Either price or vol is not positive");

	if ( (otype!= "c") && (otype!= "C") && (otype!= "p") && (otype!= "P") )
		THROW_XLW("The option type is not recognized");

	if ( (fxFwdTenors.size()!=fxFwds.size()) || (fxVolTenors.size()!=fxVols.size()) )
		THROW_XLW("FX tenor or fwd or vol inputs are not same size");

	FXSamuelVolNode vol(dtoday, doptexp, atm, alpha, beta, fxVolTenors, fxVols, corr);
	FXBlackPricer fbp(dtoday, dexp, fwd, &vol, strike, ir, otype, fxFwdTenors, fxFwds);
	MyArray ret;
	if (( "v" == outflag ) || ( "V" == outflag ))
		ret = fbp.fxvegas();		
	else if (( "d" == outflag ) || ( "D" == outflag ))
		ret = fbp.fxdeltas();
	else
		THROW_XLW("The output flag is not valid, should be d, v");
	
	return ret;
}

double CLFXEuroStripPricer(const double dtoday,
					const double dstart,
					const double dend,
					const double fwd,
					const double strike,
					const double atm, 
					const double doptexp,
					const double ir,
					const std::string otype,
					MyArray& fxFwdTenors,
					MyArray& fxFwds,
					MyArray& fxVolTenors,
					MyArray& fxVols,
					const double corr,
					const std::string outflag,
					MyArray &hols,
					const double alpha,
					const double beta)
{
	if (dtoday >= dend )
		THROW_XLW("the expiry date has passed already");

	if (dend > doptexp )
		THROW_XLW("the expiry date is later than option expiry date");

	if (beta < 0)
		THROW_XLW("Beta is less than 0");

	if ((atm <= 0) || (fwd <= 0) || (strike <= 0))
		THROW_XLW("Either price or vol is not positive");

	if ( (otype!= "c") && (otype!= "C") && (otype!= "p") && (otype!= "P") )
		THROW_XLW("The option type is not recognized");

	if ( (fxFwdTenors.size()!=fxFwds.size()) || (fxVolTenors.size()!=fxVols.size()) )
		THROW_XLW("FX tenor or fwd or vol inputs are not same size");

	FXSamuelVolNode vol(dtoday, doptexp, atm, alpha, beta, fxVolTenors, fxVols, corr);
	FXBlackStripPricer fbp(dtoday, dstart, dend, fwd, &vol, strike, ir, otype, hols, fxFwdTenors, fxFwds);
	double ret;
	if (( "p" == outflag ) || ( "P" == outflag ))
		ret = fbp.price();
	else if (( "d" == outflag ) || ( "D" == outflag ))
		ret = fbp.delta();
	else if (( "g" == outflag ) || ( "G" == outflag ))
		ret = fbp.gamma();
	else if (( "v" == outflag ) || ( "V" == outflag ))
		ret = fbp.vega();
	else if (( "t" == outflag ) || ( "T" == outflag ))
		ret = fbp.theta();
	else if (( "fv" == outflag ) || ( "FV" == outflag ))
		ret = fbp.fxvega();		
	else if (( "fd" == outflag ) || ( "FD" == outflag ))
		ret = fbp.fxdelta();
	else if (( "z" == outflag ) || ( "Z" == outflag ))
		ret = 10;
	else
		THROW_XLW("The output flag is not valid, should be p,d,g,v,t,fd,fv");
	return ret;
}
					
MyArray CLFXEuroStripRisks(const double dtoday,
					const double dstart,
					const double dend,
					const double fwd,
					const double strike,
					const double atm, 
					const double doptexp,
					const double ir,
					const std::string otype,
					MyArray& fxFwdTenors,
					MyArray& fxFwds,
					MyArray& fxVolTenors,
					MyArray& fxVols,
					const double corr,
					const std::string outflag,
					MyArray &hols,
					const double alpha,
					const double beta)
{
	if (dtoday >= dend )
		THROW_XLW("the expiry date has passed already");

	if (dend > doptexp )
		THROW_XLW("the expiry date is later than option expiry date");

	if (beta < 0)
		THROW_XLW("Beta is less than 0");

	if ((atm <= 0) || (fwd <= 0) || (strike <= 0))
		THROW_XLW("Either price or vol is not positive");

	if ( (otype!= "c") && (otype!= "C") && (otype!= "p") && (otype!= "P") )
		THROW_XLW("The option type is not recognized");

	if ( (fxFwdTenors.size()!=fxFwds.size()) || (fxVolTenors.size()!=fxVols.size()) )
		THROW_XLW("FX tenor or fwd or vol inputs are not same size");

	FXSamuelVolNode vol(dtoday, doptexp, atm, alpha, beta, fxVolTenors, fxVols, corr);
	FXBlackStripPricer fbp(dtoday, dstart, dend, fwd, &vol, strike, ir, otype, hols, fxFwdTenors, fxFwds);
	MyArray ret;
	if (( "v" == outflag ) || ( "V" == outflag ))
		ret = fbp.fxvegas();		
	else if (( "d" == outflag ) || ( "D" == outflag ))
		ret = fbp.fxdeltas();
	else
		THROW_XLW("The output flag is not valid, should be d, v");
	return ret;
}

double CLFXBinOptPricer(const double dtoday,
					const double dexp,
					const double fwd,
					const double strike,
					const double atm, 
					const double doptexp,
					const double ir,
					const std::string otype,
					MyArray& fxFwdTenors,
					MyArray& fxFwds,
					MyArray& fxVolTenors,
					MyArray& fxVols,
					const double corr,
					const std::string outflag,
					const double alpha,
					const double beta)
{
	if (dtoday > dexp )
		THROW_XLW("the expiry date has passed already");

	if (dexp > doptexp )
		THROW_XLW("the expiry date is later than option expiry date");

	if (beta < 0)
		THROW_XLW("Beta is less than 0");

	if ((atm <= 0) || (fwd <= 0) || (strike <= 0))
		THROW_XLW("Either price or vol is not positive");

	if ( (otype!= "c") && (otype!= "C") && (otype!= "p") && (otype!= "P") )
		THROW_XLW("The option type is not recognized");

	if ( (fxFwdTenors.size()!=fxFwds.size()) || (fxVolTenors.size()!=fxVols.size()) )
		THROW_XLW("FX tenor or fwd or vol inputs are not same size");
		
	FXSamuelVolNode vol(dtoday, doptexp, atm, alpha, beta, fxVolTenors, fxVols, corr);
	FXDigitalPricer fdp(dtoday, dexp, fwd, &vol, strike, ir, otype, fxFwdTenors, fxFwds);
	double ret;
	if (( "p" == outflag ) || ( "P" == outflag ))
		ret = fdp.price();
	else if (( "d" == outflag ) || ( "D" == outflag ))
		ret = fdp.delta();
	else if (( "g" == outflag ) || ( "G" == outflag ))
		ret = fdp.gamma();
	else if (( "v" == outflag ) || ( "V" == outflag ))
		ret = fdp.vega();
	else if (( "t" == outflag ) || ( "T" == outflag ))
		ret = fdp.theta();
	else if (( "fv" == outflag ) || ( "FV" == outflag ))
		ret = fdp.fxvega();		
	else if (( "fd" == outflag ) || ( "FD" == outflag ))
		ret = fdp.fxdelta();
	else if (( "z" == outflag ) || ( "Z" == outflag ))
		ret = 9;
	else
		THROW_XLW("The output flag is not valid, should be p,d,g,v,t,fd,fds,fv,fvs");
	
	return ret;
}

MyArray CLFXBinOptRisks(const double dtoday,
					const double dexp,
					const double fwd,
					const double strike,
					const double atm, 
					const double doptexp,
					const double ir,
					const std::string otype,
					MyArray& fxFwdTenors,
					MyArray& fxFwds,
					MyArray& fxVolTenors,
					MyArray& fxVols,
					const double corr,
					const std::string outflag,
					const double alpha,
					const double beta)
{
	if (dtoday > dexp )
		THROW_XLW("the expiry date has passed already");

	if (dexp > doptexp )
		THROW_XLW("the expiry date is later than option expiry date");

	if (beta < 0)
		THROW_XLW("Beta is less than 0");

	if ((atm <= 0) || (fwd <= 0) || (strike <= 0))
		THROW_XLW("Either price or vol is not positive");

	if ( (otype!= "c") && (otype!= "C") && (otype!= "p") && (otype!= "P") )
		THROW_XLW("The option type is not recognized");

	if ( (fxFwdTenors.size()!=fxFwds.size()) || (fxVolTenors.size()!=fxVols.size()) )
		THROW_XLW("FX tenor or fwd or vol inputs are not same size");
		
	FXSamuelVolNode vol(dtoday, doptexp, atm, alpha, beta, fxVolTenors, fxVols, corr);
	FXDigitalPricer fdp(dtoday, dexp, fwd, &vol, strike, ir, otype, fxFwdTenors, fxFwds);
	MyArray ret;
	if (( "v" == outflag ) || ( "V" == outflag ))
		ret = fdp.fxvegas();		
	else if (( "d" == outflag ) || ( "D" == outflag ))
		ret = fdp.fxdeltas();
	else
		THROW_XLW("The output flag is not valid, should be d, v");
		
	return ret;
}

double CLFXBinStripPricer(const double dtoday,
					const double dstart,
					const double dend,
					const double fwd,
					const double strike,
					const double atm, 
					const double doptexp,
					const double ir,
					const std::string otype,
					MyArray& fxFwdTenors,
					MyArray& fxFwds,
					MyArray& fxVolTenors,
					MyArray& fxVols,
					const double corr,
					const std::string outflag,
					MyArray &hols,
					const double alpha,
					const double beta)
{
	if (dtoday >= dend )
		THROW_XLW("the expiry date has passed already");

	if (dend > doptexp )
		THROW_XLW("the expiry date is later than option expiry date");

	if (beta < 0)
		THROW_XLW("Beta is less than 0");

	if ((atm <= 0) || (fwd <= 0) || (strike <= 0))
		THROW_XLW("Either price or vol is not positive");

	if ( (otype!= "c") && (otype!= "C") && (otype!= "p") && (otype!= "P") )
		THROW_XLW("The option type is not recognized");

	if ( (fxFwdTenors.size()!=fxFwds.size()) || (fxVolTenors.size()!=fxVols.size()) )
		THROW_XLW("FX tenor or fwd or vol inputs are not same size");

	FXSamuelVolNode vol(dtoday, doptexp, atm, alpha, beta, fxVolTenors, fxVols, corr);
	FXBinStripPricer fbp(dtoday, dstart, dend, fwd, &vol, strike, ir, otype, hols, fxFwdTenors, fxFwds);
	double ret;
	if (( "p" == outflag ) || ( "P" == outflag ))
		ret = fbp.price();
	else if (( "d" == outflag ) || ( "D" == outflag ))
		ret = fbp.delta();
	else if (( "g" == outflag ) || ( "G" == outflag ))
		ret = fbp.gamma();
	else if (( "v" == outflag ) || ( "V" == outflag ))
		ret = fbp.vega();
	else if (( "t" == outflag ) || ( "T" == outflag ))
		ret = fbp.theta();
	else if (( "fv" == outflag ) || ( "FV" == outflag ))
		ret = fbp.fxvega();		
	else if (( "fd" == outflag ) || ( "FD" == outflag ))
		ret = fbp.fxdelta();
	else if (( "z" == outflag ) || ( "Z" == outflag ))
		ret = 11;
	else
		THROW_XLW("The output flag is not valid, should be p,d,g,v,t,fd,fv");
	return ret;
}
					
MyArray CLFXBinStripRisks(const double dtoday,
					const double dstart,
					const double dend,
					const double fwd,
					const double strike,
					const double atm, 
					const double doptexp,
					const double ir,
					const std::string otype,
					MyArray& fxFwdTenors,
					MyArray& fxFwds,
					MyArray& fxVolTenors,
					MyArray& fxVols,
					const double corr,
					const std::string outflag,
					MyArray &hols,
					const double alpha,
					const double beta)
{
	if (dtoday >= dend )
		THROW_XLW("the expiry date has passed already");

	if (dend > doptexp )
		THROW_XLW("the expiry date is later than option expiry date");

	if (beta < 0)
		THROW_XLW("Beta is less than 0");

	if ((atm <= 0) || (fwd <= 0) || (strike <= 0))
		THROW_XLW("Either price or vol is not positive");

	if ( (otype!= "c") && (otype!= "C") && (otype!= "p") && (otype!= "P") )
		THROW_XLW("The option type is not recognized");

	if ( (fxFwdTenors.size()!=fxFwds.size()) || (fxVolTenors.size()!=fxVols.size()) )
		THROW_XLW("FX tenor or fwd or vol inputs are not same size");

	FXSamuelVolNode vol(dtoday, doptexp, atm, alpha, beta, fxVolTenors, fxVols, corr);
	FXBinStripPricer fbp(dtoday, dstart, dend, fwd, &vol, strike, ir, otype, hols, fxFwdTenors, fxFwds);
	MyArray ret;
	if (( "v" == outflag ) || ( "V" == outflag ))
		ret = fbp.fxvegas();		
	else if (( "d" == outflag ) || ( "D" == outflag ))
		ret = fbp.fxdeltas();
	else
		THROW_XLW("The output flag is not valid, should be d, v");
	return ret;
}
