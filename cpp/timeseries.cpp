#include "timeseries.h"

bool TimeSeries::isValidated()
{
	bool isValid = true;
	if (_date.size() != _data.size())
		isValid = false;

	return isValid;
}

TimeSeries GetTSWeightedSum(TimeSeries ts1, TimeSeries ts2, double w1,double w2 )
{
	DblVector oDate, oData;	
	DblVector date1 = ts1.date_();
	DblVector date2 = ts2.date_();
	unsigned int j = 0;
	for ( unsigned int i = 0; i < date1.size(); ++i )
	{
		while ((date1[i] > date2[j]) && (j < date2.size() - 1)) 
			++j;

		if (date1[i] < date2[j])
			continue;
		else if ((date1[i] > date2[j]) && (j == date2.size()-1) )
			break;
		else { 
			oDate.push_back(date1[i]);
			double wsum = ts1.data_()[i] * w1 + ts2.data_()[j] * w2;
			oData.push_back(wsum);
		}
	}
	return TimeSeries(oDate, oData);
}

HistVolCalculator::HistVolCalculator(TimeSeries ts, double expiry, double freq=1, int btMonths=12): 
										_ts(ts), _expiry(expiry), _freq(freq), _backtestMonths(btMonths)
{}

double HistVolCalculator::pricer(double fwd, double strike, double vol, double currDate)
{
	double t_exp = (_expiry - currDate)/365.0;
	return BachelierPrice(fwd, strike, vol, t_exp, 1.0, "c");
}

double HistVolCalculator::delta(double fwd, double strike, double vol, double currDate)
{
	return (pricer(fwd + 0.00001, strike, vol, currDate) - pricer(fwd - 0.00001, strike, vol, currDate))/0.00002;
}

double HistVolCalculator::deltaHedgePL(double vol, int start_idx, int end_idx)
{
	double strike = _ts.data_()[start_idx];
	DblVector date = _ts.date_();
	DblVector data = _ts.data_();
	int last_idx = start_idx;
	double pnl = pricer(data[start_idx], strike, vol, date[start_idx]);
	double last_pos = delta(data[start_idx], strike, vol, date[start_idx]);

	for (int i = start_idx + 1; i <= end_idx; ++i)
	{
		if (((date[i] - date[last_idx]) >= _freq) || (i == end_idx))
		{					
			pnl += last_pos * (data[i] - data[last_idx]);
			last_pos = delta(data[i], strike, vol, date[i]);
			last_idx = i;
		}
	}		
	return pnl;
}

DblVector HistVolCalculator::BreakevenVols()
{
	double solver_epsilon = 1e-6, iter_step = 0.0002;
	int iter_num = 200;
	DblVector beVols;
	//double last_vol = 0.0;
	double payoff;
	DblVector dates = _ts.date_();

	int exp_idx = dates.size() - 1;
	while ( dates[exp_idx] != _expiry ) exp_idx--;

	double vol = 4;
	int end_idx = exp_idx;
	int start_idx = end_idx;

	for (int i = 0; i < _backtestMonths; ++i)
	{
		double startdate = _expiry - 30 * (i+1);
		
		while ((start_idx >= 1) && ( dates[start_idx - 1] >= startdate)) start_idx--;

		if (i==0)
			payoff = (_ts.data_()[end_idx]> _ts.data_()[start_idx])? (_ts.data_()[end_idx]- _ts.data_()[start_idx]):0;
		else
			payoff = pricer(_ts.data_()[end_idx], _ts.data_()[start_idx], vol, dates[end_idx]);

		double next_vol = vol;
		double current, high, low;	
		int tried_num = 0;
		double diff = 1e+6;

		while ((diff > solver_epsilon) && (tried_num < iter_num))
		{
			current = deltaHedgePL(vol, start_idx, end_idx) - payoff;
			high =  deltaHedgePL(vol + iter_step, start_idx, end_idx) - payoff;
			low  =  deltaHedgePL(vol - iter_step, start_idx, end_idx) - payoff;
			if (high == low)
				next_vol = (vol-iter_step>0.01)? (vol-iter_step):0.01;
			else {
				next_vol = vol - 2 * iter_step * current/(high - low);
				if (next_vol < 0.01)
					next_vol = vol/2.0;
			}

			diff = std::abs(next_vol - vol);
			vol = next_vol;
			tried_num++;
		}

		if ((diff > solver_epsilon) || (tried_num >= iter_num))
			vol = 0;

		end_idx = start_idx;
		beVols.push_back(vol);		
		if (start_idx == 0) break;
	}

	return beVols;
}