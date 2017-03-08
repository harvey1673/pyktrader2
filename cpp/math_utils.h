#ifndef MATH_UTILS_H
#define MATH_UTILS_H
#include <stdexcept>
#include <limits>
#include <sstream>
#include <cmath>
#include <string>
#include <vector>
#include <algorithm>
#include "normdist.h"

#ifdef WIN32
#include <float.h>
#else
#include <math.h>
#endif

typedef std::vector <double>                DblVector;
typedef std::vector <DblVector>             DblVectorOfVectors;
typedef std::vector<DblVectorOfVectors>     DblVectorOfVectorsOfVectors;
typedef std::vector< DblVector >            DblMatrix2D;
typedef std::vector<DblMatrix2D>            DblMatrix2DOfVectors;
typedef std::vector <DblMatrix2D>           DblVectorOfMatrices2D;
typedef std::vector <DblVectorOfMatrices2D> DblMatrix2DOfMatrices2D;
typedef std::vector< DblMatrix2D >          DblMatrix3D;
typedef std::vector <DblMatrix3D>           DblVectorOfMatrices3D;

typedef std::vector <int>               IntVector;
typedef std::vector <char>              CharVector;
typedef std::vector <unsigned int>      UIntVector;
typedef std::vector <size_t>              SizeTVector;
typedef std::vector< SizeTVector >        SizeTVectorOfVectors;
typedef std::vector<SizeTVectorOfVectors> SizeTMatrix2DOfVectors;

typedef std::vector <bool>                BoolVector;
typedef std::vector <BoolVector>          BoolVectorOfVectors;
typedef std::vector <BoolVector>          BoolMatrix2D;

typedef std::vector<std::string>          StringVector;
typedef std::vector<StringVector>         StringMatrix2D;

const int CHN_Holidays[] = {41640, 41641, 41642, 41670, 41673, 41674, 41675, 41676, \
						  41736, 41760, 41761, 41792, 41890, 41913, 41914, 41915, \
						  41918, 41919, 42005, 42006, 42053, 42054, 42055, 42058, \
						  42059, 42100, 42125, 42177, 42275, 42278, 42279, 42282, \
						  42283, 42284, 42370, 42408, 42409, 42410, 42411, 42412, \
						  42464, 42492, 42530, 42531, 42628, 42629, 42646, 42647, \
						  42648, 42649, 42650, 42737, 42765, 42766, 42767, 42768, \
						  42769, 42830, 42856, 42885, 43010, 43011, 43012, 43013, \
						  43014, 43101, 43147, 43150, 43151, 43152, 43195, 43221, \
						  43269, 43367, 43374, 43375, 43376, 43377, 43378, 0};

inline size_t xl2weekday(const double xldate)
{
	return ((int(xldate) - 1) % 7);
}

inline bool isweekday(const double xldate)
{
	int wkday = xl2weekday(xldate);
	if ((wkday == 0) || (wkday == 6))
		return false;
	else
		return true;
}

inline DblVector businessDays(const double startD, const double endD, DblVector hols)
{
	int sdate = int(startD);
	int edate = int(endD);
	DblVector res;

	for (int d = sdate; d <= edate; ++d)
		if (isweekday(d) && (std::find(hols.begin(), hols.end(), double(d))==hols.end()))
			res.push_back( double(d) );
	
	return res;
}

inline int NumBusDays(const double startD, const double endD, const int hols[])
{
	int sdate = int(startD);
	int edate = int(endD);
	//#if (sdate == edate) return endD - startD;
	int nlen = 0;
	while (hols[nlen] > 0) nlen++;
	int res = 0;
	int i = 0;
	for (int d = sdate; d <= edate; ++d) {
		while ((i<nlen-1) && (hols[i]<d)) i++;
		if (isweekday(d) && (d != hols[i]))
			res++;
	}
	return res;
}

inline double NextBusDay(const double startD, const int hols[])
{
	int sdate = int(startD);
	int nlen = 0;
	while (hols[nlen] > 0) nlen++;
	double res = startD;
	int i = 0;
	do 
	{	
		res = res + 1;
		while ((i<nlen-1) && (hols[i]<int(res))) i++;
	} while ( (!isweekday(res))|| (int(res) == hols[i]));
	return res;
}

inline double GetDayFraction(const double dExp, std::string accrual)
{
	double res = 0.0;
	if (accrual == "act365")
		res = dExp - int(dExp);
	else if (accrual == "SSE" || accrual == "SZE")
	{
		double frac = dExp - int(dExp);
		if (frac < 9.5/24.0)
			res = 0.0;
		else if (frac < 11.5/24.0)
			res = (frac - 9.5/24.0)*6.0;
		else if (frac < 13.0/24.0)
			res = 0.5;
		else if (frac < 15.0/24.0)
			res = 0.5 + (frac -13.0/24.0)*6.0;
		else
			res = 1.0;
	}
	else if (accrual == "CFFEX")
	{
		double frac = dExp - int(dExp);
		if (frac < 9.25/24.0)
			res = 0.0;
		else if (frac < 11.5/24.0)
			res = (frac - 9.25/24.0)*24.0/4.25;
		else if (frac < 13.0/24.0)
			res = 2.25/4.25;
		else if (frac < 15.0/24.0)
			res = 2.25/4.25 + (frac -13.0/24.0)*24.0/4.25;
		else
			res = 1.0;
	}
	else if (accrual == "COM")
	{
		double frac = dExp - int(dExp);
		if (frac < 9.0/24.0)
			res = 0.0;
		else if (frac < 10.25/24.0)
			res = (frac - 9.0/24.0)*24.0/3.75;
		else if (frac < 10.5/24.0)
			res = 1.25/3.75;
		else if (frac < 11.5/24.0)
			res = 1.25/3.75 + (frac -10.5/24.0)*24.0/3.75;
		else if (frac < 13.5/24.0)
			res = 2.25/3.75;
		else if (frac < 15.0/24.0)
			res = 2.25/3.75 + (frac -13.5/24.0)*24.0/3.75;
		else
			res = 1.0;
	}
	return res;
}

inline double norm_rand()
{
	double p = double(rand())/double(RAND_MAX);
	return norminv(p);
}

inline void ExcelSerialDateToDMY(int nSerialDate, int &nDay, 
                          int &nMonth, int &nYear)
{
    // Excel/Lotus 123 have a bug with 29-02-1900. 1900 is not a
    // leap year, but Excel/Lotus 123 think it is...
    if (nSerialDate == 60)
    {
        nDay    = 29;
        nMonth    = 2;
        nYear    = 1900;

        return;
    }
    else if (nSerialDate < 60)
    {
        // Because of the 29-02-1900 bug, any serial date 
        // under 60 is one off... Compensate.
        nSerialDate++;
    }

    // Modified Julian to DMY calculation with an addition of 2415019
    int l = nSerialDate + 68569 + 2415019;
    int n = int(( 4 * l ) / 146097);
            l = l - int(( 146097 * n + 3 ) / 4);
    int i = int(( 4000 * ( l + 1 ) ) / 1461001);
        l = l - int(( 1461 * i ) / 4) + 31;
    int j = int(( 80 * l ) / 2447);
     nDay = l - int(( 2447 * j ) / 80);
        l = int(j / 11);
        nMonth = j + 2 - ( 12 * l );
    nYear = 100 * ( n - 49 ) + i + l;
}

inline int DMYToExcelSerialDate(int nDay, int nMonth, int nYear)
{
    // Excel/Lotus 123 have a bug with 29-02-1900. 1900 is not a
    // leap year, but Excel/Lotus 123 think it is...
    if (nDay == 29 && nMonth == 02 && nYear==1900)
        return 60;

    // DMY to Modified Julian calculatie with an extra substraction of 2415019.
    long nSerialDate = 
            int(( 1461 * ( nYear + 4800 + int(( nMonth - 14 ) / 12) ) ) / 4) +
            int(( 367 * ( nMonth - 2 - 12 * ( ( nMonth - 14 ) / 12 ) ) ) / 12) -
            int(( 3 * ( int(( nYear + 4900 + int(( nMonth - 14 ) / 12) ) / 100) ) ) / 4) +
            nDay - 2415019 - 32075;

    if (nSerialDate < 60)
    {
        // Because of the 29-02-1900 bug, any serial date 
        // under 60 is one off... Compensate.
        nSerialDate--;
    }

    return int(nSerialDate);
}


// Matrix manipulation

inline void resizeMatrix( DblMatrix2D & m,
                        const size_t n1,
                        const size_t n2 )
{
    m.resize(n1);
    for ( size_t i = 0; i < n1; ++i )
        m[i].resize(n2);
}

inline void resizeMatrix( StringMatrix2D & m,
                        const size_t n1,
                        const size_t n2 )
{
    m.resize(n1);
    for ( size_t i = 0; i < n1; ++i )
        m[i].resize(n2);
}

inline void resizeMatrix( SizeTVectorOfVectors & m,
                        const size_t n1,
                        const size_t n2 )
{
    m.resize(n1);
    for ( size_t i = 0; i < n1; ++i )
        m[i].resize(n2);
}

inline size_t size1( const DblMatrix2D & m ) 
{
    return m.size();
}

inline size_t size2( const DblMatrix2D & m ) 
{
    if ( 0 == m.size() )
        return 0;
    else
        return m[0].size();
}

inline size_t size1( const StringMatrix2D & m ) 
{
    return m.size();
}

inline size_t size2( const StringMatrix2D & m ) 
{
    if ( 0 == m.size() )
        return 0;
    else
        return m[0].size();
}

inline void resizeMatrix( DblMatrix3D & m,
                        const size_t n1,
                        const size_t n2,
                        const size_t n3 )
{
    m.resize(n1);
    for ( size_t i = 0; i < n1; ++i ){
        m[i].resize(n2);
        for ( size_t j = 0; j < n2; ++j ){
            m[i][j].resize(n3);
        }
    }
}

inline void resizeMatrix( DblMatrix2DOfMatrices2D & m,
                          const size_t n1,
                          const size_t n2 )
{
    m.resize(n1);
    for ( size_t i = 0; i < n1; ++i ){
        m[i].resize(n2);
    }
}
inline void resizeMatrix( SizeTMatrix2DOfVectors & m,
                          const size_t n1,
                          const size_t n2 )
{
    m.resize(n1);
    for ( size_t i = 0; i < n1; ++i ){
        m[i].resize(n2);
    }
}

inline size_t size1( const DblMatrix2DOfMatrices2D & m ) 
{
    return m.size();
}

inline size_t size2( const DblMatrix2DOfMatrices2D & m ) 
{
    if ( 0 == m.size() )
        return 0;
    else
        return m[0].size();
}

inline void resizeMatrix(DblMatrix2DOfVectors & m,
                         const size_t n1,
                         const size_t n2)
{
    m.resize(n1);
    for (size_t i = 0; i < n1; ++i) {
        m[i].resize(n2);
    }
}

inline size_t size1(const DblMatrix2DOfVectors & m)
{
    return m.size();
}

inline size_t size2(const DblMatrix2DOfVectors & m)
{
    if (0 == m.size())
        return 0;
    else
        return m[0].size();
}
inline void resizeMatrix( BoolMatrix2D & m,
                        const size_t n1,
                        const size_t n2 )
{
    m.resize(n1);
    for ( size_t i = 0; i < n1; ++i )
        m[i].resize(n2);
}

inline size_t size1( const BoolMatrix2D & m ) 
{
    return m.size();
}

inline size_t size2( const BoolMatrix2D & m ) 
{
    if ( 0 == m.size() )
        return 0;
    else
        return m[0].size();
}

inline DblMatrix2D transpose( const DblMatrix2D & m )
{
    DblMatrix2D tm;
    const size_t ndim1 = size2(m);
    const size_t ndim2 = size1(m);

    resizeMatrix(tm, ndim1, ndim2);

    for ( size_t i = 0; i < ndim1; ++i ) {
        for ( size_t j = 0; j < ndim2; ++j ) {
            tm[i][j] = m[j][i];
        }
    }
    return tm;
}

inline SizeTVector range(size_t rstart, size_t rend)
{
    SizeTVector r;
    r.resize(rend - rstart);
    for (size_t i = 0; i < (rend - rstart); ++i) r[i] = rstart + i;
    return r;
}

inline SizeTVector range(size_t rend) 
{
    return range(0, rend);
}

// Useful vectors

inline DblVector zeros(const size_t n)
{
    return DblVector(n, 0.0);
}

inline DblVector ones(const size_t n)
{
    return DblVector(n, 1.0);
}

inline DblVector add(const DblVector & v1, const double & a)
{
    DblVector v;
    size_t vsize = v1.size();

    v.resize(vsize);
    for (size_t i = 0; i < vsize; ++i) v[i] = v1[i] + a;
    return v;
}

inline DblVector subtract(const DblVector & v1, const DblVector & v2)
{
    DblVector v;
    size_t vsize = std::min(v1.size(), v2.size());

    v.resize(vsize);
    for (size_t i = 0; i < vsize; ++i) v[i] = v1[i] - v2[i];
    return v;
}

inline DblVector subtract(const DblVector & v1, const double & a)
{
    DblVector v;
    size_t vsize = v1.size();

    v.resize(vsize);
    for (size_t i = 0; i < vsize; ++i) v[i] = v1[i] - a;
    return v;
}

inline DblVector multItems(const DblVector & v1, const double & a)
{
    DblVector v;
    size_t vsize = v1.size();

    v.resize(vsize);
    for (size_t i = 0; i < vsize; ++i) v[i] = v1[i] * a;
    return v;
}

inline DblVector divItems(const DblVector & v1, const double & a)
{
    DblVector v;
    size_t vsize = v1.size();

    v.resize(vsize);
    for (size_t i = 0; i < vsize; ++i) v[i] = v1[i] / a;
    return v;
}

inline DblVector multItems(const DblVector & v1, const DblVector & v2)
{
    DblVector v;
    size_t vsize = std::min(v1.size(), v2.size());

    v.resize(vsize);
    for (size_t i = 0; i < vsize; ++i) v[i] = v1[i] * v2[i];
    return v;
}

inline DblVector divItems(const DblVector & v1, const DblVector & v2)
{
    DblVector v;
    size_t vsize = std::min(v1.size(), v2.size());

    v.resize(vsize);
    for (size_t i = 0; i < vsize; ++i) v[i] = v1[i] / v2[i];
    return v;
}

inline void applyFun(DblVector & v, double (*fct)(double))
{
    for ( size_t i = 0; i < v.size(); ++i ) v[i] = (*fct)(v[i]);
}


// Matrix arithmetic operations

inline DblMatrix2D add(const DblMatrix2D & m1, const DblMatrix2D & m2)
{
    DblMatrix2D m;
    size_t msize1 = std::min(size1(m1), size1(m2));
    size_t msize2 = std::min(size2(m1), size2(m2));

    resizeMatrix(m, msize1, msize2);
    for (size_t i = 0; i < msize1; ++i) {
        for (size_t j = 0; j < msize2; ++j) {
            m[i][j] = m1[i][j] + m2[i][j];
        }
    }
    return m;
}

inline DblMatrix2D add(const DblMatrix2D & m1, const double a)
{
    DblMatrix2D m;
    size_t msize1 = size1(m1);
    size_t msize2 = size2(m1);

    resizeMatrix(m, msize1, msize2);
    for (size_t i = 0; i < msize1; ++i) {
        for (size_t j = 0; j < msize2; ++j) {
            m[i][j] = m1[i][j] + a;
        }
    }
    return m;
}

inline DblMatrix2D subtract(const DblMatrix2D & m1, const DblMatrix2D & m2)
{
    DblMatrix2D m;
    size_t msize1 = std::min(size1(m1), size1(m2));
    size_t msize2 = std::min(size2(m1), size2(m2));

    resizeMatrix(m, msize1, msize2);
    for (size_t i = 0; i < msize1; ++i) {
        for (size_t j = 0; j < msize2; ++j) {
            m[i][j] = m1[i][j] - m2[i][j];
        }
    }
    return m;
}

inline DblMatrix2D subtract(const DblMatrix2D & m1, const double a)
{
    DblMatrix2D m;
    size_t msize1 = size1(m1);
    size_t msize2 = size2(m1);

    resizeMatrix(m, msize1, msize2);
    for (size_t i = 0; i < msize1; ++i) {
        for (size_t j = 0; j < msize2; ++j) {
            m[i][j] = m1[i][j] - a;
        }
    }
    return m;
}

inline DblMatrix2D multItems(const DblMatrix2D & m1, const DblMatrix2D & m2)
{
    DblMatrix2D m;
    size_t msize1 = std::min(size1(m1), size1(m2));
    size_t msize2 = std::min(size2(m1), size2(m2));

    resizeMatrix(m, msize1, msize2);
    for (size_t i = 0; i < msize1; ++i) {
        for (size_t j = 0; j < msize2; ++j) {
            m[i][j] = m1[i][j] * m2[i][j];
        }
    }
    return m;
}

inline DblMatrix2D multItems(const DblMatrix2D & m1, const double a)
{
    DblMatrix2D m;
    size_t msize1 = size1(m1);
    size_t msize2 = size2(m1);

    resizeMatrix(m, msize1, msize2);
    for (size_t i = 0; i < msize1; ++i) {
        for (size_t j = 0; j < msize2; ++j) {
            m[i][j] = m1[i][j] * a;
        }
    }
    return m;
}


inline void matrixMult(DblMatrix2D& result, const DblMatrix2D& m1, const DblMatrix2D& m2)
{
    for (size_t i = 0; i < size1(m1); ++i) {
        for (size_t j = 0; j < size2(m2); ++j) {
            result[i][j] = 0.0;
            for (size_t k = 0; k < size2(m1); ++k) {
                result[i][j] += m1[i][k] * m2[k][j];
            }
        }
    }
}

inline double sum(const DblMatrix2D& m)
{
    double sum = 0.0; 
    for ( size_t i = 0; i < size1(m); ++i ) {
        for ( size_t j = 0; j < size2(m); ++j ) {
            sum += m[i][j];
        }
    }
    return sum;
}


inline DblMatrix2D divItems(const DblMatrix2D & m1, const DblMatrix2D & m2)
{
    DblMatrix2D m;
    size_t msize1 = std::min(size1(m1), size1(m2));
    size_t msize2 = std::min(size2(m1), size2(m2));

    resizeMatrix(m, msize1, msize2);
    for (size_t i = 0; i < msize1; ++i) {
        for (size_t j = 0; j < msize2; ++j) {
            m[i][j] = m1[i][j] / m2[i][j];
        }
    }
    return m;
}

inline DblMatrix2D divItems(const DblMatrix2D & m1, const double a)
{
    DblMatrix2D m;
    size_t msize1 = size1(m1);
    size_t msize2 = size2(m1);

    resizeMatrix(m, msize1, msize2);
    for (size_t i = 0; i < msize1; ++i) {
        for (size_t j = 0; j < msize2; ++j) {
            m[i][j] = m1[i][j] / a;
        }
    }
    return m;
}

inline void applyFun(DblMatrix2D & m, double (*fct)(double))
{
    for ( size_t i = 0; i < size1(m); ++i ) {
        for (size_t j = 0; j < size2(m); ++j) {
            m[i][j] = (*fct)(m[i][j]);
        }
    }
}

inline void matrixVectorMult(DblVector& result, const DblMatrix2D& m, const DblVector& v)
{
    const size_t s1 = size1(m);
    const size_t s2 = size2(m);
    result.resize( s1 );
    for (size_t i = 0; i < s1; ++i)
        result[i] = 0.0;

    for (size_t k = 0; k < s2; ++k)
        for (size_t i = 0; i < s1; ++i)
            result[i] += m[i][k] * v[k];
}

#endif