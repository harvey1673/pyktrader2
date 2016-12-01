#ifndef BARRIER_H
#define BARRIER_H
#include "euopt.h"

double BarrierSingleFull_dic( double fwd, 
							  double vol, 
							  double expiry, 
							  double strike, 
							  double barrier, 
							  double df );

double BarrierSingleFull_uic( double fwd, 
							  double vol, 
							  double expiry, 
							  double strike, 
							  double barrier, 
							  double df );

double BarrierSingleFull_dip( double fwd, 
							  double vol, 
							  double expiry, 
							  double strike, 
							  double barrier, 
							  double df );

double BarrierSingleFull_uip( double fwd,
                              double vol,
                              double expiry,
                              double strike,
                              double barrier,
							  double df );

double BarrierSingleFull_doc( double fwd,
                              double vol,
                              double expiry,
                              double strike,
                              double barrier,
							  double df );

double BarrierSingleFull_uoc( double fwd,
                              double vol,
                              double expiry,
                              double strike,
                              double barrier,
							  double df );

double BarrierSingleFull_dop( double fwd,
                              double vol,
                              double expiry,
                              double strike,
                              double barrier,
							  double df );

double BarrierSingleFull_uop( double fwd,
                              double vol,
                              double expiry,
                              double strike,
                              double barrier,
							  double df );


#endif