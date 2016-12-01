#include <cmath>     // c library of math functions
#include <cerrno>

///* Coefficients in rational approximations. */
//#ifndef PI 
//#define PI 3.141592653589793238462643
//#endif
//static const double a[] =
//{
//	-3.969683028665376e+01,
//	 2.209460984245205e+02,
//	-2.759285104469687e+02,
//	 1.383577518672690e+02,
//	-3.066479806614716e+01,
//	 2.506628277459239e+00
//};
//
//static const double b[] =
//{
//	-5.447609879822406e+01,
//	 1.615858368580409e+02,
//	-1.556989798598866e+02,
//	 6.680131188771972e+01,
//	-1.328068155288572e+01
//};
//
//static const double c[] =
//{
//	-7.784894002430293e-03,
//	-3.223964580411365e-01,
//	-2.400758277161838e+00,
//	-2.549732539343734e+00,
//	 4.374664141464968e+00,
//	 2.938163982698783e+00
//};
//
//static const double d[] =
//{
//	7.784695709041462e-03,
//	3.224671290700398e-01,
//	2.445134137142996e+00,
//	3.754408661907416e+00
//};
//
//#define LOW 0.02425
//#define HIGH 0.97575


const double gc_dSqrtTwoPi                = 2.50662827463100050242;
const double gc_dTwoPi                    = 6.28318530717958647692;

double ExpIntegral(double b, double tau)
{
	if ((b == 0) || (tau == 0))
		return 1.0;
	else
		return (1-std::exp(-b*tau))/(b*tau);
}

double normpdf( double z) {  // normal distribution function    
    return std::exp(-0.5*z*z)/gc_dSqrtTwoPi;
}

//double normcdf(const double& z) 
//{
//	double b1 = -0.0004406;
//	double b2 =  0.0418198;
//	double b3 =  0.9;
//	return 1.0 / (1.0 + std::exp(-std::sqrt(PI)*(b1*std::pow(z,5.0) + b2*std::pow(z,3.0) + b3*z)));
//}
//
//double norminv(const double& p)
//{
//	double q, r;
//
//	errno = 0;
//
//	if (p < 0 || p > 1)
//	{
//		errno = EDOM;
//		return 0.0;
//	}
//	else if (p == 0)
//	{
//		errno = ERANGE;
//		return -HUGE_VAL /* minus "infinity" */;
//	}
//	else if (p == 1)
//	{
//		errno = ERANGE;
//		return HUGE_VAL /* "infinity" */;
//	}
//	else if (p < LOW)
//	{
//		/* Rational approximation for lower region */
//		q = sqrt(-2*std::log(p));
//		return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) /
//			((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1);
//	}
//	else if (p > HIGH)
//	{
//		/* Rational approximation for upper region */
//		q  = std::sqrt(-2*std::log(1-p));
//		return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) /
//			((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1);
//	}
//	else
//	{
//		/* Rational approximation for central region */
//    		q = p - 0.5;
//    		r = q*q;
//		return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q /
//			(((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1);
//	}
//}


////////////////////////////////////////////////////////////////////////////
/////////
// normcdf
//
// Algorithm AS66 Applied Statistics
// Evaluates the tail area of the standardised normal curve from minus infinity to z
// z = no. of standard deviations from the mean
// Normal distribution probabilities accurate to 1.0e-15
// Based upon algorithm 5666 for the error function, from:
//        Hart, J.F. et al, 'Computer Approximations', Wiley 1968
////////////////////////////////////////////////////////////////////////////
/////////
double normcdf( double z )
{
    double zabs = std::abs( z );

    if ( zabs > 37.0 )
    {
        return ( z > 0.0 ) ? 1.0 : 0.0;
    }
    else
    {
        const double cutoff = 7.07106781186547;     // 10/sqrt( 2 )
        double prob;
        double expntl = std::exp(-0.5 * z * z );

        if ( zabs < cutoff ) {
            const double p0 = 220.2068679123761;
            const double p1 = 221.2135961699311;
            const double p2 = 112.0792914978709;
            const double p3 = 33.91286607838300;
            const double p4 = 6.373962203531650;
            const double p5 = 0.7003830644436881;
            const double p6 = 0.03526249659989109;
            const double q0 = 440.4137358247522;
            const double q1 = 793.8265125199484;
            const double q2 = 637.3336333788311;
            const double q3 = 296.5642487796737;
            const double q4 = 86.78073220294608;
            const double q5 = 16.06417757920695;
            const double q6 = 1.755667163182642;
            const double q7 = 0.08838834764831844;

            prob = expntl * (((((( p6 * zabs + p5 ) * zabs + p4 ) * zabs + 
						p3 ) * zabs + p2 ) * zabs + p1 ) * zabs + p0 )
					/ ((((((( q7 * zabs + q6 ) * zabs + q5 ) * zabs + q4 ) * 
						zabs + q3 ) * zabs + q2 ) * zabs + q1 ) * zabs + q0 );
		} else {
            prob = expntl / ( gc_dSqrtTwoPi * ( zabs + 1.0 / ( zabs + 2.0 / 
						( zabs + 3.0 / ( zabs + 4.0 / ( zabs + 0.65 ))))));
        }
        if ( z > 0.0 )
        {
            prob = 1.0 - prob;
        }
        
        return prob;
    }
}

////////////////////////////////////////////////////////////////////////////
/////////
// norminv
//
// Algorithm AS241 Applied Statistics
// Produces the normal deviate z corresponding to a given lower tail area of prob
// z is accurate to about 1.0e-16
////////////////////////////////////////////////////////////////////////////
/////////
double norminv( double prob )
{
    static const double epsilon = 1.0e-16;
    static const double split1 = 0.425;
    static const double split2 = 5.0;

    static const double a0 = 3.3871328727963666080;
    static const double a1 = 1.3314166789178437745e2;
    static const double a2 = 1.9715909503065514427e3;
    static const double a3 = 1.3731693765509461125e4;
    static const double a4 = 4.5921953931549871457e4;
    static const double a5 = 6.7265770927008700853e4;
    static const double a6 = 3.3430575583588128105e4;
    static const double a7 = 2.5090809287301226727e3;
    static const double b1 = 4.2313330701600911252e1;
    static const double b2 = 6.8718700749205790830e2;
    static const double b3 = 5.3941960214247511077e3;
    static const double b4 = 2.1213794301586595867e4;
    static const double b5 = 3.9307895800092710610e4;
    static const double b6 = 2.8729085735721942674e4;
    static const double b7 = 5.2264952788528545610e3;
    static const double const1 = 0.180625;

    static const double c0 = 1.42343711074968357734;
    static const double c1 = 4.63033784615654529590;
    static const double c2 = 5.76949722146069140550;
    static const double c3 = 3.64784832476320460504;
    static const double c4 = 1.27045825245236838258;
    static const double c5 = 2.41780725177450611770e-1;
    static const double c6 = 2.27238449892691845833e-2;
    static const double c7 = 7.74545014278341407640e-4;
    static const double d1 = 2.05319162663775882187;
    static const double d2 = 1.67638483018380384940;
    static const double d3 = 6.89767334985100004550e-1;
    static const double d4 = 1.48103976427480074590e-1;
    static const double d5 = 1.51986665636164571966e-2;
    static const double d6 = 5.47593808499534494600e-4;
    static const double d7 = 1.05075007164441684324e-9;
    static const double const2 = 1.6;

    static const double e0 = 6.65790464350110377720;
    static const double e1 = 5.46378491116411436990;
    static const double e2 = 1.78482653991729133580;
    static const double e3 = 2.96560571828504891230e-1;
    static const double e4 = 2.65321895265761230930e-2;
    static const double e5 = 1.24266094738807843860e-3;
    static const double e6 = 2.71155556874348757815e-5;
    static const double e7 = 2.01033439929228813265e-7;
    static const double f1 = 5.99832206555887937690e-1;
    static const double f2 = 1.36929880922735805310e-1;
    static const double f3 = 1.48753612908506148525e-2;
    static const double f4 = 7.86869131145613259100e-4;
    static const double f5 = 1.84631831751005468180e-5;
    static const double f6 = 1.42151175831644588870e-7;
    static const double f7 = 2.04426310338993978564e-15;

    const double q = prob - 0.5;
    if ( std::abs( q ) <= split1 ) {
        double r = const1 - q * q;
        double z = q * ((((((( a7 * r + a6 ) * r + a5 ) * r + a4 ) * r + a3 
					) * r + a2 ) * r + a1 ) * r + a0 )
				/ ((((((( b7 * r + b6 ) * r + b5 ) * r + b4 ) * r + b3 ) * r + 
					b2 ) * r + b1 ) * r + 1.0 );
        return z;
    } else {
        double z;
        double r = ( q < 0.0 ) ? prob : 1.0 - prob;

        if ( r <= 0.0 ) r = epsilon; // if zero, re-adjust to very small positive value /// @todo JS should throw an exception of r < 0

        r = std::sqrt(-std::log( r ));
        if ( r <= split2 ) {
            r -= const2;
            z = ((((((( c7 * r + c6 ) * r + c5 ) * r + c4 ) * r + c3 ) * r +
					c2 ) * r + c1 ) * r + c0 )
                /((((((( d7 * r + d6 ) * r + d5 ) * r + d4 ) * r + d3 ) * r 
					+ d2 ) * r + d1 ) * r + 1.0 );
        } else {
            r -= split2;
            z = ((((((( e7 * r + e6 ) * r + e5 ) * r + e4 ) * r + e3 ) * r +
					e2 ) * r + e1 ) * r + e0 )
                /((((((( f7 * r + f6 ) * r + f5 ) * r + f4 ) * r + f3 ) * r 
					+ f2 ) * r + f1 ) * r + 1.0 );
        }

        return ( q < 0.0 ) ? -z : z;
    }
}

//relative error is ~1e-9
double normcdf_fast( double prob )
{
    static const double p_low  = 0.02425;
    static const double p_high = 1 - p_low;
    static const double eps = 1e-16;
    
    static const double a1 = -3.969683028665376e+01;
    static const double a2 =  2.209460984245205e+02;
    static const double a3 = -2.759285104469687e+02;
    static const double a4 =  1.383577518672690e+02;
    static const double a5 = -3.066479806614716e+01;
    static const double a6 =  2.506628277459239e+00;

    static const double b1 = -5.447609879822406e+01;
    static const double b2 =  1.615858368580409e+02;
    static const double b3 = -1.556989798598866e+02;
    static const double b4 =  6.680131188771972e+01;
    static const double b5 = -1.328068155288572e+01;

    static const double c1 = -7.784894002430293e-03;
    static const double c2 = -3.223964580411365e-01;
    static const double c3 = -2.400758277161838e+00;
    static const double c4 = -2.549732539343734e+00;
    static const double c5 =  4.374664141464968e+00;
    static const double c6 =  2.938163982698783e+00;

    static const double d1 =  7.784695709041462e-03;
    static const double d2 =  3.224671290700398e-01;
    static const double d3 =  2.445134137142996e+00;
    static const double d4 =  3.754408661907416e+00;

    //Rational approximation for lower region.
    double q, r;
    if(prob < p_low){
        if(prob < eps)
            prob = eps;

        q = std::sqrt(-2*std::log(prob));
        return (((((c1*q+c2)*q+c3)*q+c4)*q+c5)*q+c6) /
                ((((d1*q+d2)*q+d3)*q+d4)*q+1);
    } else if(prob <= p_high){
		//Rational approximation for central region.
        q = prob - 0.5;
        r = q*q;
        return (((((a1*r+a2)*r+a3)*r+a4)*r+a5)*r+a6)*q /
                (((((b1*r+b2)*r+b3)*r+b4)*r+b5)*r+1);
    } else {
		//Rational approximation for upper region.
        //p_high < prob

        double one_minus_prob = 1 - prob;
        if(one_minus_prob < eps)
            one_minus_prob = eps;
            
        q = std::sqrt(-2*log(one_minus_prob));
        return -(((((c1*q+c2)*q+c3)*q+c4)*q+c5)*q+c6) /
                ((((d1*q+d2)*q+d3)*q+d4)*q+1);
    }
}
