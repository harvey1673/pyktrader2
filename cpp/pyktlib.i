//pyktlib.i
%module pyktlib

%{
#include "euopt.h"
#include "amopt.h"
#include "volmodel.h"
#include "pricer.h"
#include "barriersmile.h"
#include "timeseries.h"
%}
%include "std_string.i"
%include "std_vector.i"
%include "euopt.h"
%include "amopt.h"
%include "volmodel.h"
%include "pricer.h"
%include "barriersmile.h"
%include "timeseries.h"
