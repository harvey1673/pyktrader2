// normdist.h 

#ifndef NORMAL_DIST_H_
#define NORMAL_DIST_H_

double ExpIntegral(double b, double tau);

double normcdf( double z );

double normcdf_fast( double prob );

double norminv( double prob );

double normpdf( double z );

#endif