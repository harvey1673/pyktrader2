#ifndef TIMESERIES_H
#define TIMESERIES_H

#include <string>
#include <vector>
#include "math_utils.h"
#include "normdist.h"
#include "euopt.h"

class TimeSeries {
public:
	DblVector date_() { return _date; }
	DblVector data_() { return _data; }
	TimeSeries( DblVector date, DblVector data):_date(date),_data(data) {}
	TimeSeries() {}
	void setDate( const DblVector date ) { _date = date; }
	void setData( const DblVector data ) { _data = data; }
	bool isValidated();
private:
	DblVector _date;
	DblVector _data;
};

TimeSeries GetTSWeightedSum(TimeSeries ts1, TimeSeries ts2, double w1,double w2 );

class HistVolCalculator {
public:
	HistVolCalculator( TimeSeries ts, double expiry, double freq, int btMonths);
	double pricer(double fwd, double strike, double vol, double currDate);
	double delta(double fwd, double strike, double vol, double currDate);
	double deltaHedgePL(double vol, int start_idx, int end_idx);
	DblVector BreakevenVols();
	TimeSeries ts_() { return _ts; }
	double freq_() { return _freq; }
	double expiry_() { return _expiry; }
	void setExpiry(double expiry) { _expiry = expiry; }
	void setFreq( double freq) { _freq = freq; }
	void setTS(TimeSeries ts) { _ts = ts; }
private:
	TimeSeries _ts;
	double _expiry;
	double _freq;
	int _backtestMonths;
};
#endif