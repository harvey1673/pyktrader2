#include "barrier.h"

/// down knock-in call
double BarrierSingleFull_dic( double fwd, 
							  double vol, 
							  double expiry, 
							  double strike, 
							  double barrier, 
							  double df )
{
    double price = 0.0;

    if ( fwd <= barrier )   // knock-in region
        price = BlackPrice(fwd, strike, vol, expiry, 1, "c");
    else if ( vol * vol * expiry <= 0 )
		price = 0.0;
	else {
        const double VolRtT = vol * std::sqrt( expiry );
        const double H2_F = barrier * barrier / fwd;
        const double mu =  - 0.5;
        const double H_F2mu = std::pow( barrier / fwd, 2.0 * mu );

        if ( strike > barrier )
        {
            const double dc2 = std::log( H2_F / strike ) / VolRtT - 0.5 * VolRtT;
            price = H_F2mu * ( H2_F * normcdf( dc2 + VolRtT ) - strike * normcdf(dc2));
        }
        else
        {
            const double HalfVolRtT = 0.5 * VolRtT;
            const double da2 = std::log( fwd / strike ) / VolRtT - HalfVolRtT;
            const double db2 = std::log( fwd / barrier ) / VolRtT - HalfVolRtT;
            const double dd2 = std::log( H2_F / barrier ) / VolRtT - HalfVolRtT;
            price = fwd * ( normcdf( da2 + VolRtT ) - normcdf( db2 + VolRtT)) - 
					strike * ( normcdf( da2 ) - normcdf( db2 )) +
					H_F2mu * ( H2_F * normcdf( dd2 + VolRtT ) - strike * normcdf( dd2 ));
        }
    }

    return price * df;
}

/// up knock-in call
double BarrierSingleFull_uic( double fwd, 
							  double vol, 
							  double expiry, 
							  double strike, 
							  double barrier, 
							  double df )
{
    double price = 0.0;

    if ( fwd >= barrier )  // knock-in region
    {
        price = BlackPrice(fwd, strike, vol, expiry, 1, "c");
    }
    else if ( vol * vol * expiry <= 0 )
		price = 0.0;
    else {
        const double VolRtT = vol * std::sqrt( expiry );
        if (  strike > barrier )
        {
            const double da2 = std::log( fwd / strike ) / VolRtT - 0.5 * VolRtT;
            price = fwd * normcdf( da2 + VolRtT ) - strike * normcdf( da2 );
        }
        else
        {
            const double H2_F = barrier * barrier / fwd;
            const double mu = - 0.5;
            const double H_F2mu = std::pow( barrier / fwd, 2.0 * mu );
            const double HalfVolRtT = 0.5 * VolRtT;
            const double db2 = std::log( fwd / barrier ) / VolRtT - HalfVolRtT;
            const double dc2 = std::log( H2_F / strike ) / VolRtT - HalfVolRtT;
            const double dd2 = std::log( H2_F / barrier ) / VolRtT - HalfVolRtT;
            price = fwd * normcdf( db2 + VolRtT ) - strike * normcdf( db2 ) 
                     - H_F2mu * ( H2_F * ( normcdf(- dc2 - VolRtT ) - normcdf(- dd2 - VolRtT ))
                                  - strike * (normcdf( -dc2 ) - normcdf(- dd2 )));
        }
    }

    return price * df;
}

/// down knock-in put
double BarrierSingleFull_dip( double fwd, 
							  double vol, 
							  double expiry, 
							  double strike, 
							  double barrier, 
							  double df )
{
    double price = 0.0;

    if ( fwd <= barrier )   // knock-in region
		price = BlackPrice(fwd, strike, vol, expiry, 1, "p");
    else if ( vol * vol * expiry <= 0)
        price = 0.0;
    else {
        const double VolRtT = vol * std::sqrt( expiry );

        if ( strike > barrier )
        {
            const double H2_F = barrier * barrier / fwd;
            const double mu = -0.5;
            const double H_F2mu = std::pow( barrier / fwd, 2.0 * mu );
            const double HalfVolRtT = 0.5 * VolRtT;
            const double db2 = std::log( fwd / barrier ) / VolRtT - HalfVolRtT;
            const double dc2 = std::log( H2_F / strike ) / VolRtT - HalfVolRtT;
            const double dd2 = std::log( H2_F / barrier ) / VolRtT - HalfVolRtT;
            price = strike * normcdf(- db2 ) - fwd * normcdf(- db2 - VolRtT )
                     + H_F2mu * ( H2_F * ( normcdf( dc2 + VolRtT ) - normcdf( dd2 + VolRtT ))
                                  - strike * ( normcdf( dc2 ) - normcdf( dd2 )));
        }
        else
        {
            const double da2 = std::log( fwd / strike ) / VolRtT - 0.5 * VolRtT;
            price = strike * normcdf(- da2 ) - fwd * normcdf(- da2 - VolRtT );
        }
    }

    return price * df;
}

/// up knock-in put
double BarrierSingleFull_uip( double fwd,
                              double vol,
                              double expiry,
                              double strike,
                              double barrier,
							  double df )
{
    double price = 0.0;

    if ( fwd >= barrier )  // knock-in region
    {
        price = BlackPrice(fwd, strike, vol, expiry, 1, "p");
    }
    else if ( vol * vol * expiry <= 0 )
    {
        price = 0.0;
    }
    else 
    {
        const double VolRtT = vol * std::sqrt( expiry );
        const double H2_F = barrier * barrier / fwd;
        const double mu = -0.5;
        const double H_F2mu = std::pow( barrier / fwd, 2.0 * mu );

        if ( strike > barrier )
        {
            const double HalfVolRtT = 0.5 * VolRtT;
            const double da2 = std::log( fwd / strike ) / VolRtT - HalfVolRtT;
            const double db2 = std::log( fwd / barrier ) / VolRtT - HalfVolRtT;
            const double dd2 = std::log( H2_F / barrier ) / VolRtT - HalfVolRtT;
            price = strike * ( normcdf(- da2 ) - normcdf(- db2 ))
                     - fwd * ( normcdf(- da2 - VolRtT ) - normcdf(- db2 - VolRtT ))
                     - H_F2mu * ( H2_F * normcdf(-dd2 -VolRtT ) - strike * normcdf( -dd2 ));
        }
        else
        {
            const double dc2 = std::log( H2_F / strike ) / VolRtT - 0.5 * VolRtT;
            price = H_F2mu * ( strike * normcdf(- dc2 ) - H2_F * normcdf(- dc2 - VolRtT ));
        }
    }

    return price * df;
}

/// down knock-out call
double BarrierSingleFull_doc( double fwd,
                              double vol,
                              double expiry,
                              double strike,
                              double barrier,
							  double df )
{
    double price = 0.0;

    if ( fwd <= barrier )   // knock-out region
    {
        price = 0.0;
    }
    else if ( vol * vol * expiry <= 0 )
    {
        price = BlackPrice(fwd, strike, vol, expiry, 1, "c");
    }
    else 
    {
        const double VolRtT = vol * std::sqrt( expiry );
        const double H2_F = barrier * barrier / fwd;
        const double mu = -0.5;
        const double H_F2mu = std::pow( barrier / fwd, 2.0 * mu );
        const double HalfVolRtT = 0.5 * VolRtT;

        if ( strike > barrier )
        {
            const double da2 = std::log( fwd / strike ) / VolRtT - HalfVolRtT;
            const double dc2 = std::log( H2_F / strike ) / VolRtT - HalfVolRtT;
            price = fwd * normcdf( da2 + VolRtT ) - strike * normcdf( da2 )
                     - H_F2mu * ( H2_F * normcdf( dc2 + VolRtT ) - strike * normcdf( dc2 ));
        }
        else
        {
            const double db2 = std::log( fwd / barrier ) / VolRtT - HalfVolRtT;
            const double dd2 = std::log( H2_F / barrier ) / VolRtT - HalfVolRtT;
            price = fwd * normcdf( db2 + VolRtT ) - strike * normcdf( db2 )
                     - H_F2mu * ( H2_F * normcdf( dd2 + VolRtT ) - strike * normcdf( dd2 ));
        }
    }

    return price * df;
}

/// up knock-out call
double BarrierSingleFull_uoc( double fwd,
                              double vol,
                              double expiry,
                              double strike,
                              double barrier,
							  double df )
{
    double price = 0.0;

    if ( fwd >= barrier )  // knock-out region
    {
        price = 0.0;
    }
    else if ( vol * vol * expiry <= 0 ) 
    {
        price = BlackPrice(fwd, strike, vol, expiry, 1, "c");
    }
    else if ( strike > barrier )
    {
        price = 0.0;
    }
    else
    {
        const double VolRtT = vol * std::sqrt( expiry );
        const double H2_F = barrier * barrier / fwd;
        const double mu = -0.5;
        const double H_F2mu = std::pow( barrier / fwd, 2.0 * mu );
        const double HalfVolRtT = 0.5 * VolRtT;
        const double da2 = std::log( fwd / strike ) / VolRtT - HalfVolRtT;
        const double db2 = std::log( fwd / barrier ) / VolRtT - HalfVolRtT;
        const double dc2 = std::log( H2_F / strike ) / VolRtT - HalfVolRtT;
        const double dd2 = std::log( H2_F / barrier ) / VolRtT - HalfVolRtT;
        price = fwd * ( normcdf( da2 + VolRtT ) - normcdf( db2 + VolRtT ))
                 - strike * ( normcdf( da2 ) - normcdf( db2 ))
                 + H_F2mu * ( H2_F * ( normcdf(- dc2 - VolRtT ) - normcdf(- dd2 - VolRtT ))
                              - strike * ( normcdf(- dc2 ) - normcdf(- dd2 )));
    }

    return price * df;
}

/// down knock-out put
double BarrierSingleFull_dop( double fwd,
                              double vol,
                              double expiry,
                              double strike,
                              double barrier,
							  double df )
{
    double price = 0.0;

    if ( fwd <= barrier )       // knock-out region
    {
        price = 0.0;
    }
    else if ( vol * vol * expiry <= 0 )
    {
        price = BlackPrice(fwd, strike, vol, expiry, 1, "p");
	}
    else if ( strike > barrier ) // positive time to maturity
    {
        const double VolRtT = vol * std::sqrt( expiry );
        const double H2_F = barrier * barrier / fwd;
        const double mu = -0.5;
        const double H_F2mu = std::pow( barrier / fwd, 2.0 * mu );
        const double HalfVolRtT = 0.5 * VolRtT;
        const double da2 = std::log( fwd / strike ) / VolRtT - HalfVolRtT;
        const double db2 = std::log( fwd / barrier ) / VolRtT - HalfVolRtT;
        const double dc2 = std::log( H2_F / strike ) / VolRtT - HalfVolRtT;
        const double dd2 = std::log( H2_F / barrier ) / VolRtT - HalfVolRtT;
        price = strike * ( normcdf(- da2 ) - normcdf(- db2 ))
                 - fwd * ( normcdf(- da2 - VolRtT ) - normcdf(- db2 - VolRtT ))
                 - H_F2mu * ( H2_F * ( normcdf( dc2 + VolRtT ) - normcdf( dd2 + VolRtT ))
                              - strike * ( normcdf( dc2 ) - normcdf( dd2 )));
    }
    else
    {
        price = 0.0;
    }

    return price * df;
}

/// up knock-out put
double BarrierSingleFull_uop( double fwd,
                              double vol,
                              double expiry,
                              double strike,
                              double barrier,
							  double df )
{
    double price = 0.0;

    if ( fwd >= barrier )  // knock-out region
    {
        price = 0.0;
    }
    else if ( vol * vol * expiry <= 0 )
    {
        price = BlackPrice(fwd, strike, vol, expiry, 1, "p");
    }
    else 
    {
        const double VolRtT = vol * std::sqrt( expiry );
        const double H2_F = barrier * barrier / fwd;
        const double mu = -0.5;
        const double H_F2mu = std::pow( barrier / fwd, 2.0 * mu );
        const double HalfVolRtT = 0.5 * VolRtT;

        if ( strike > barrier )
        {
            const double db2 = std::log( fwd / barrier ) / VolRtT - HalfVolRtT;
            const double dd2 = std::log( H2_F / barrier ) / VolRtT - HalfVolRtT;
            price = strike * normcdf(- db2 ) - fwd * normcdf(- db2 - VolRtT )
                     + H_F2mu * ( H2_F * normcdf(- dd2 - VolRtT ) - strike * normcdf(- dd2 ));
        }
        else
        {
            const double da2 = std::log( fwd / strike ) / VolRtT - HalfVolRtT;
            const double dc2 = std::log( H2_F / strike ) / VolRtT - HalfVolRtT;
            price = strike * normcdf(- da2 ) - fwd * normcdf(- da2 - VolRtT )
                     + H_F2mu * ( H2_F * normcdf(- dc2 - VolRtT ) - strike * normcdf(- dc2 ));
        }
    }

    return price * df;
}