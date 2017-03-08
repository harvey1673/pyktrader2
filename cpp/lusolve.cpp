#include "lusolve.h"
#include "math_utils.h"

int LuDecomp( DblMatrix2D & lu_,
              SizeTVector & perm_,
              const DblMatrix2D & a_ )
{
    // sanity checks
    if ( size1( a_ ) != size2( a_ ) )
        return -1;

    const size_t n = size1( a_ );

    //const double TINY = 1e-20;

    DblVector vv(n);
    perm_.resize(n);
    
    double d = 1.0;

    lu_ = a_;

    for ( size_t i = 0; i < n; ++i )
    {
        double big = 0.0;
        for ( size_t j = 0; j < n; ++j )
        {
            big = std::max( big, std::fabs( lu_[i][j] ) );
        }
        if ( 0.0 == big )
            return -1;
        vv[i] = 1.0 / big;
    }

    for ( size_t j = 0; j < n; ++j )
    {
        for ( size_t i = 0; i < j; ++i )
        {
            double sum = lu_[i][j];
            for ( size_t k = 0; k < i; ++k )
            {
                sum -= lu_[i][k] * lu_[k][j];
            }
            lu_[i][j] = sum;
        }
        double big = 0.0;
        size_t imax = std::numeric_limits<size_t>::quiet_NaN();

        for ( size_t i = j; i < n; ++i )
        {
            double sum = lu_[i][j];
            for ( size_t k = 0; k < j; ++k )
            {
                sum -= lu_[i][k] * lu_[k][j];
            }
            lu_[i][j] = sum;

            const double tmp = vv[i] * std::fabs(sum);
            if ( tmp >= big )
            {
                big = tmp;
                imax = i;
            }
        }
        if ( j != imax )
        {
            for ( size_t k = 0; k < n; ++k )
            {
                const double tmp = lu_[imax][k];
                lu_[imax][k] = lu_[j][k];
                lu_[j][k] = tmp;
            }
            d = -d;
            vv[imax] = vv[j];
        }
        perm_[j] = imax;
        // if ( 0.0 == lu_[j][j] ) lu_[j][j] = TINY;
        if ( j != n - 1 )
        {
            const double tmp = 1.0 / lu_[j][j];
            for ( size_t i = j + 1; i < n; ++i )
            {
                lu_[i][j] *= tmp;
            }
        }
    }
	return 0;
}


int LuSubst( DblVector   & x_,
             const DblMatrix2D & lu_,
             const SizeTVector & perm_,
             const DblVector   & b_)
{
    if ( size1( lu_ ) != size2( lu_ ) )
        return -1;

    const size_t n = size1( lu_ );
    x_ = b_;

    size_t ii = 0;

    for ( size_t i = 0; i < n; ++i )
    {
        size_t ip = perm_[i];
        double sum = x_[ip];
        x_[ip] = x_[i];
        if ( ii != 0 )
        {
            for ( size_t j = ii - 1; j < i; ++j )
            {
                sum -= lu_[i][j] * x_[j];
            }
        }
        else if ( sum != 0.0 )
        {
            ii = i + 1;
        }
        x_[i] = sum;
    }
    for ( int i = n - 1; i >= 0; --i )
    {
        double sum = x_[i];
        for ( size_t j = i + 1; j < n; ++j )
        {
            sum -= lu_[i][j] * x_[j];
        }
        x_[i] = sum / lu_[i][i];
    }
	return 0;
}

int LuInvert( DblMatrix2D & x_,
              const DblMatrix2D & a_)
{
    if ( size1( a_ ) != size2( a_ ) )
        return -1;

    DblMatrix2D lu_;
    SizeTVector perm_;
    LuDecomp(lu_, perm_, a_);

    resizeMatrix(x_, size1( a_ ), size2( a_ ));

    const size_t n = size1(a_);
    DblVector cols(n);
    DblVector tmp_(n);
    for (size_t j = 0; j < n; ++j)
    {
        cols[j] = 1.0;
        LuSubst(tmp_, lu_, perm_, cols);
        cols.clear();
        cols.resize(n, 0.0);
        for (size_t i = 0; i < n; ++i)
        {
            x_[i][j] = tmp_[i];
        }
    }
	return 0;
}

int LuSolve( DblVector   & x_,
              const DblMatrix2D & a_,
              const DblVector   & b_ )
{
    DblMatrix2D lu;
    SizeTVector perm;
    int res = LuDecomp( lu, perm, a_ );
	if (res == -1)
		return -1;
    res = LuSubst( x_, lu, perm, b_ );
	if (res == -1)
		return -1;
	else
		return 0;
}