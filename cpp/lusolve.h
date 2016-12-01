#ifndef LUSOLVE_H
#define LUSOLVE_H

#include "math_utils.h"
#include <cmath>

int LuDecomp( DblMatrix2D & lu_, SizeTVector & perm_, 
			const DblMatrix2D & a_ );

int LuSubst( DblVector   & x_, const DblMatrix2D & lu_,
            const SizeTVector & perm_, const DblVector   & b_);

int LuInvert( DblMatrix2D & x_, const DblMatrix2D & a_);

int LuSolve( DblVector   & x_, const DblMatrix2D & a_,
            const DblVector   & b_ );

#endif