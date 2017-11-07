# -*- coding: utf-8 -*-
import scipy.stats
import numpy
from math import exp, log, pi, sqrt
import scipy
from scipy.optimize import brenth, brentq, newton
from scipy.integrate import dblquad, quad
import time

def asian_vol_adj(atm, time2mat, tau):
    M = (2 * numpy.exp(atm * atm * time2mat) \
         - 2 * numpy.exp(atm * atm * tau) * (1.0 + atm * atm * (time2mat - tau))) / \
        ((atm ** 4) * ((time2mat - tau) ** 2))
    return numpy.sqrt(numpy.log(M) / time2mat)

def cnorm(x):
    return scipy.stats.norm.cdf(x)

def cnorminv(x):
    return scipy.stats.norm.ppf(x)

def pnorm(x):
    return scipy.stats.norm.pdf(x)

def d1(Spot, Strike, Vol, Texp, Rd, Rf ):
    return (log(float(Spot)/float(Strike)) + (Rd - Rf + 0.5*Vol*Vol) * Texp)/(Vol*sqrt(Texp))

def d2(Spot, Strike, Vol, Texp, Rd, Rf ):
    return d1(Spot, Strike, Vol, Texp, Rd, Rf ) - Vol*sqrt(Texp)

def fd1(Fwd,K,Vol,T):
    return log(float(Fwd)/K)/Vol/sqrt(T) + Vol*sqrt(T)/2.

def fd2(Fwd,K,Vol,T):
    return log(float(Fwd)/K)/Vol/sqrt(T) - Vol*sqrt(T)/2.
    
def BlackSholesFormula(IsCall, S, K, Vol, Texp, Rd, Rf):
    x1 = d1(S, K, Vol, Texp, Rd, Rf )
    x2 = d2(S, K, Vol, Texp, Rd, Rf )
    y = pnorm(x1)
    res = {}

    if IsCall:
        res['Price'] = S * exp(-Rf*Texp)* x1 - K * exp(-Rd*Texp) * x2
        res['Delta'] = x1 * exp(-Rf*Texp)
    else:
        res['Price'] = K * exp(-Rd*Texp) * (1 - x2) - S * exp(-Rf*Texp) * (1 - x1)
        res['Delta'] = (x1  - 1) * exp(-Rf*Texp)
    res['Vega'] = S * sqrt(Texp) * y * exp(-Rf*Texp)
    res['Gamma'] = y * exp(-Rf*Texp)/(S*Vol* sqrt(Texp))
    return res

def KirkApprox(IsCall, F1, F2, Sigma1, Sigma2, Corr, K, Texp, r):
    FA = F1/(F2+K)
    Sigma = sqrt(Sigma1**2 + (Sigma2*F2/(F2+K))**2 - \
                       2*Corr*Sigma1*Sigma2*F2/(F2+K))
    d1 = (numpy.log(FA) + 0.5* Sigma**2 * Texp)/(Sigma*sqrt(Texp))
    d2 = d1 - Sigma*sqrt(Texp)
    x1 = scipy.stats.norm.cdf(d1)
    x2 = scipy.stats.norm.cdf(d2)
    res = {}
    if IsCall:
        res['Price'] = (F2+K)*(FA * x1 - x2) * exp(-r*Texp)
    else:
        res['Price'] = (F2+K)*((1 - x2) - FA*(1 - x1)) * exp(-r*Texp)
    return res

def MinOptionOnSpdCall(F1, F2, dv1, dv2, rho, K1, K2, T):
    ' min(max(F1-K1),max(F2-K2)) assuming F1 F2 are spread of two assets'
    v1 = dv1 * numpy.sqrt(T)
    v2 = dv2 * numpy.sqrt(T)
    def int_func1(x):
        return  scipy.stats.norm.cdf(((F1-K1)-(F2-K2) + (v1 * rho - v2) * x)/(v1 * numpy.sqrt(1-rho**2))) \
                        * (v2 * x + F2- K2) * scipy.stats.norm.pdf(x)

    def int_func2(x):
        return  scipy.stats.norm.cdf(((F2-K2)-(F1-K1) + (v2 * rho - v1) * x)/(v2 * numpy.sqrt(1-rho**2))) \
                        * (v1 * x + F1- K1) * scipy.stats.norm.pdf(x)
    res1 = quad(int_func1, (K2-F2)/v2, numpy.inf)
    res2 = quad(int_func2, (K1-F1)/v1, numpy.inf)
    return res1[0] + res2[0]

def BSOpt( IsCall, Spot, Strike, Vol, Texp, Rd, Rf ):
    'Standard Black-Scholes European vanilla pricing.'
    if Strike <= 1e-12 * Spot:
        if IsCall:
            return Spot * exp( -Rf * Texp )
        else:
            return 0.

    if IsCall:
        return Spot   * exp( -Rf * Texp ) * cnorm( d1( Spot, Strike, Vol, Texp, Rd, Rf ) ) \
             - Strike * exp( -Rd * Texp ) * cnorm( d2( Spot, Strike, Vol, Texp, Rd, Rf ) )
    else:
        return Strike * exp( -Rd * Texp ) * cnorm( -d2( Spot, Strike, Vol, Texp, Rd, Rf ) ) \
             - Spot   * exp( -Rf * Texp ) * cnorm( -d1( Spot, Strike, Vol, Texp, Rd, Rf ) )


def BSFwd( IsCall, Fwd, Strike, Vol, Texp, ir):
    'Standard Black-Scholes European vanilla pricing.'

    if Strike <= 1e-12 * Fwd:
        if IsCall:
            return Fwd
        else:
            return 0.
    df = exp(-ir * Texp)
    if IsCall:
        return df * (Fwd  * cnorm( fd1( Fwd, Strike, Vol, Texp ) ) \
             - Strike * cnorm( fd2( Fwd, Strike, Vol, Texp ) ))
    else:
        return df * (Strike * cnorm( -fd2( Fwd, Strike, Vol, Texp ) ) \
             - Fwd * cnorm( -fd1( Fwd, Strike, Vol, Texp ) ))

def BSFwdDelta( IsCall, Fwd, Strike, Vol, Texp, ir):
    if IsCall:
        return exp( -ir * Texp ) * cnorm(fd1( Fwd, Strike, Vol, Texp))
    else:
        return -exp( -ir * Texp ) * cnorm(-fd1( Fwd, Strike, Vol, Texp))

def BSFwdNormal( IsCall, Fwd, Strike, Vol, Texp, ir):
    'Standard Bachelier European vanilla pricing.'
    d = (Fwd-Strike)/Vol/sqrt(Texp)
    p = (Fwd-Strike)  * cnorm( d ) + Vol * sqrt(Texp) * pnorm(d)
    if not IsCall:
        p = p - Fwd + Strike
    return p * exp(-Texp*ir)
    
def BSDelta( IsCall, Spot, Strike, Vol, Texp, Rd, Rf ):
    'Standard Black-Scholes Delta calculation. Over-currency spot delta.'
    if IsCall:
        return exp( -Rf * Texp ) * cnorm( d1( Spot, Strike, Vol, Texp, Rd, Rf ) )
    else:
        return -exp( -Rf * Texp ) * cnorm( -d1( Spot, Strike, Vol, Texp, Rd, Rf ) )

def BSVega( Spot, Strike, Vol, Texp, Rd, Rf ):
    'Standard Black-Scholes Vega calculation.'

    d = d1( Spot, Strike, Vol, Texp, Rd, Rf )
    return Spot * exp( -Rf * Texp ) * sqrt( Texp / 2. / pi ) * exp( -d * d / 2. )
    
def BSFwdNormalDelta( IsCall, Fwd, Strike, Vol, Texp, Rd, Rf = 0.0 ):
    d1 = (Fwd - Strike)/Vol/numpy.sqrt(Texp)
    return exp( -Rd * Texp ) * cnorm(d1)

def BSFwdNormalVega( IsCall, Fwd, Strike, Vol, Texp, Rd, Rf = 0.0 ):
    v = BSFwdNormal( IsCall, Fwd, Strike, Vol * 1.01, Texp, Rd) - BSFwdNormal( IsCall, Fwd, Strike, Vol * 0.99, Texp, Rd)
    v = v /0.02/Vol
    return v

def BSBin( IsCall, Spot, Strike, Vol, Texp, Rd, Rf ):
    'Standard Black-Scholes European binary call/put pricing.'

    Bin = cnorm( d2( Spot, Strike, Vol, Texp, Rd, Rf ) )
    if not IsCall:
        Bin = 1 - Bin
    Bin = Bin * exp( -Rd * Texp )
    return Bin

def BSImpVol( IsCall, Spot, Strike, Texp, Rd, Rf, Price ):
    '''Calculates Black-Scholes implied volatility from a European price.
    It uses Brent rootfinding, and tries to isolate the root somewhat using
    a lower limit based on recognizing that the time value of the option is
    less than or equal to the time value of an ATM option, and an upper limit
    by calculating the vega at the lower limit and recognizing that vanillas
    have positive vol convexity (or zero for ATM options).'''

    Dd = exp( -Rd * Texp )
    Df = exp( -Rf * Texp )

    if IsCall:
        IntVal = max( Df * Spot - Dd * Strike, 0. )
    else:
        IntVal = max( Dd * Strike - Df * Spot, 0. )

    TimeVal = Price - IntVal

    VolMin    = sqrt( 2 * pi / Texp ) * TimeVal / Df / Spot
    PriceMin  = BSOpt( IsCall, Spot, Strike, VolMin, Texp, Rd, Rf )
    PriceDiff = Price - PriceMin
    VegaMin   = BSVega( Spot, Strike, VolMin, Texp, Rd, Rf )

    if VegaMin == 0:
        VolMax = 10
        VolMin = 0.001
    else:
        VolMax    = VolMin + PriceDiff / VegaMin
        VolMin    = max( 0.00001, VolMin - 0.001 )
        VolMax    = min( 10, VolMax + 0.001 )

    def ArgFunc( Vol ):
        PriceCalc = BSOpt( IsCall, Spot, Strike, Vol, Texp, Rd, Rf )
        return PriceCalc - Price

    Vol = brenth( ArgFunc, VolMin, VolMax )
    return Vol

def BSImpVolSimple( IsCall, Spot, Strike, Texp, Rd, Rf, Price ):
    '''Calculates Black-Scholes implied volatility from a European price.
    It uses Brent rootfinding and assumes the vol is between 0.0000001 and 1.'''

    def ArgFunc( Vol ):
        PriceCalc = BSOpt( IsCall, Spot, Strike, Vol, Texp, Rd, Rf )
        return PriceCalc - Price

    Vol = brenth( ArgFunc, 0.0000001, 1 )
    return Vol

def BSImpVolNormal( IsCall, Fwd, Strike, Texp, Rd, Price ):
    '''Calculates the normal-model implied vol to match the option price.'''

    def ArgFunc( Vol ):
        PriceCalc = BSFwdNormal( IsCall, Fwd, Strike, Vol, Texp, Rd )
        return PriceCalc - Price

    Vol = brenth( ArgFunc, 0.0000001, Fwd )
    return Vol

def StrikeFromDelta( IsCall, Spot, Vol, Texp, Rd, Rf, Delta ):
    '''Calculates the strike of a European vanilla option gives its Black-Scholes Delta.
    It assumes the Delta is an over-ccy spot Delta.'''

    def ArgFunc( Strike ):
        DeltaCalc = BSDelta( IsCall, Spot, Strike, Vol, Texp, Rd, Rf )
        return DeltaCalc - Delta

    LoStrike = Spot * exp( ( Rd - Rf ) * Texp - 4 * Vol * sqrt( Texp ) )
    HiStrike = Spot * exp( ( Rd - Rf ) * Texp + 4 * Vol * sqrt( Texp ) )

    Strike = brenth( ArgFunc, LoStrike, HiStrike )
    return Strike

def OneTouch( IsHigh, IsDelayed, Spot, Strike, Vol, Texp, Rd, Rf ):
    '''Prices a one touch option. IsHigh=True means it knocks up and in; False
    means down and in. IsDelayed=True means it pays at the end; False means it
    pays on hit.'''

    if ( IsHigh and Spot >= Strike ) or ( not IsHigh and Spot <= Strike ):
        if IsDelayed:
            return exp( -Rd * Texp )
        else:
            return 1

    if Vol <= 0 or Texp <= 0: return 0

    Alpha = log( Strike / float( Spot ) )
    Mu    = Rd - Rf - Vol * Vol / 2.

    if IsDelayed:
        if IsHigh:
            Price = exp( -Rd * Texp ) * ( cnorm( ( -Alpha + Mu * Texp ) / Vol / sqrt( Texp ) ) \
                  + exp( 2 * Mu * Alpha / Vol / Vol ) * cnorm( ( -Alpha - Mu * Texp ) / Vol / sqrt( Texp ) ) )
        else:
            Price = exp( -Rd * Texp ) * ( cnorm( (  Alpha - Mu * Texp ) / Vol / sqrt( Texp ) ) \
                  + exp( 2 * Mu * Alpha / Vol / Vol ) * cnorm( (  Alpha + Mu * Texp ) / Vol / sqrt( Texp ) ) )
    else:
        MuHat = sqrt( Mu * Mu + 2 * Rd * Vol * Vol )
        if IsHigh:
            Price = exp( Alpha / Vol / Vol * ( Mu - MuHat ) ) * cnorm( ( -Alpha + MuHat * Texp ) / Vol / sqrt( Texp ) ) \
                  + exp( Alpha / Vol / Vol * ( Mu + MuHat ) ) * cnorm( ( -Alpha - MuHat * Texp ) / Vol / sqrt( Texp ) )
        else:
            Price = exp( Alpha / Vol / Vol * ( Mu + MuHat ) ) * cnorm( (  Alpha + MuHat * Texp ) / Vol / sqrt( Texp ) ) \
                  + exp( Alpha / Vol / Vol * ( Mu - MuHat ) ) * cnorm( (  Alpha - MuHat * Texp ) / Vol / sqrt( Texp ) )

    return Price

def BSKnockout( IsCall, Spot, Strike, KO, IsUp, Vol, Texp, Rd, Rf ):
    '''Knockout option with a continuous barrier: price under constant vol, constant drift BS model.'''

    if ( Spot >= KO and IsUp ) or ( Spot <= KO and not IsUp ): return 0. # knocked

    Mu = Rd - Rf
    SqrtT = sqrt( Texp )

    # as per Haug

    Phi = IsCall and 1 or -1
    Eta = IsUp and -1 or 1

    m  = ( Mu - 0.5 * Vol * Vol ) / Vol / Vol
    Lambda = sqrt( m * m + 2. * Mu / Vol / Vol )
    x1 = log( Spot / Strike ) / Vol / SqrtT + ( 1 + m ) * Vol * SqrtT
    x2 = log( Spot / KO ) / Vol / SqrtT + ( 1 + m ) * Vol * SqrtT
    y1 = log( KO * KO / Spot / Strike ) / Vol / SqrtT + ( 1 + m ) * Vol * SqrtT
    y2 = log( KO / Spot ) / Vol / SqrtT + ( 1 + m ) * Vol * SqrtT

    A = Phi * Spot * exp( -Rf * Texp ) * cnorm( Phi * x1 ) - Phi * Strike * exp( -Rd * Texp ) * cnorm( Phi * x1 - Phi * Vol * SqrtT )
    B = Phi * Spot * exp( -Rf * Texp ) * cnorm( Phi * x2 ) - Phi * Strike * exp( -Rd * Texp ) * cnorm( Phi * x2 - Phi * Vol * SqrtT )
    C = Phi * Spot * exp( -Rf * Texp ) * ( KO / Spot ) ** ( 2 * ( m + 1 ) ) * cnorm( Eta * y1 ) - Phi * Strike * exp( -Rd * Texp ) * ( KO / Spot ) ** ( 2 * m ) * cnorm( Eta * y1 - Eta * Vol * SqrtT )
    D = Phi * Spot * exp( -Rf * Texp ) * ( KO / Spot ) ** ( 2 * ( m + 1 ) ) * cnorm( Eta * y2 ) - Phi * Strike * exp( -Rd * Texp ) * ( KO / Spot ) ** ( 2 * m ) * cnorm( Eta * y2 - Eta * Vol * SqrtT )

    if Strike < KO:
        if IsCall and IsUp:
            return A - B + C - D
        elif IsCall and not IsUp:
            return B - D
        elif not IsCall and IsUp:
            return A - C
        else:
            return 0
    else:
        if IsCall and IsUp:
            return 0
        elif IsCall and not IsUp:
            return A - C
        elif not IsCall and IsUp:
            return B - D
        else:
            return A - B + C - D

def WhaleyPremium( IsCall, Fwd, Strike, Vol, Texp, Df, Tr ):
    '''
    Early exercise premium for american futures options based on Whaley approximation
    formula. To compute the options prices, this needs to be added to the european
    options prices.
    '''
    if Texp <= 0.:
        return False,0.

    T   = Texp
    K   = Strike
    D   = Df
    Phi = (IsCall and 1 or -1)

    # handle zero vol case explicitly
    if Vol == 0.0:
        eePrem = max(Phi*(Fwd-Strike)*(1. - D), 0.)
        return ( bool(eePrem > 0.), eePrem )

    k = (D==1.) and 2./Tr/Vol/Vol or -2.*log(D)/Tr/Vol/Vol/(1-D)
    # the expression in the middle is really the expression on the right in the limit D -> 1
    # note that lim_{D -> 1.} log(D)/(1-D) = -1.

    try:

        if Phi == 1:
            q2=(1.+sqrt(1.+4.*k))/2.
            def EarlyExerBdry( eeb ):
                x = D*BSFwd(True,eeb,K,Vol,T) + (1.-D*cnorm(fd1(eeb,K,Vol,T)))*eeb/q2 - eeb + K
                return x

            eeBdry = D*BSFwd(True,Fwd,K,Vol,T) + (1.-D*cnorm(fd1(Fwd,K,Vol,T)))*Fwd/q2 + K
            eeBdry = newton(EarlyExerBdry,eeBdry)
            if Fwd >= eeBdry:
                eePrem = -D*BSFwd(True,Fwd,K,Vol,T) + Fwd - K
                earlyExercise = True
            else:
                A2=(eeBdry/q2)*(1.-D*cnorm(fd1(eeBdry,K,Vol,T)))
                eePrem = A2 * pow(Fwd/eeBdry,q2)
                earlyExercise = False
        elif Phi == -1:
            q1=(1.-sqrt(1.+4.*k))/2.
            def EarlyExerBdry( eeb ):
                x = D*BSFwd(False,eeb,K,Vol,T) - (1.-D*cnorm(-fd1(eeb,K,Vol,T)))*eeb/q1 + eeb - K
                return x

            eeBdry = -D*BSFwd(False,Fwd,K,Vol,T) + (1.-D*cnorm(-fd1(Fwd,K,Vol,T)))*Fwd/q1 + K
            eeBdry = newton(EarlyExerBdry,eeBdry)
            if Fwd <= eeBdry:
                eePrem = -D*BSFwd(False,Fwd,K,Vol,T) + K - Fwd
                earlyExercise = True
            else:
                A1=-(eeBdry/q1)*(1.-D*cnorm(-fd1(eeBdry,K,Vol,T)))
                eePrem = A1 * pow(Fwd/eeBdry,q1)
                earlyExercise = False
        else:
            raise ValueError, 'option type can only be call or put'

    except:
        eePrem = max( Phi * ( Fwd - Strike ) - Phi * Df * ( Fwd - Strike ), 0. )
        earlyExercise = True

    return earlyExercise, eePrem

def WhaleyDelta( IsCall, Spot, Fwd, Strike, Vol, Texp, Df, Tr, D,\
                deltaTerms='FORWARD', smileTerms='RISK', premiumTerms='BASE' ):
    '''
    This calculates the delta for american options under various conventions.
    D = discount until Texp (Df < D)
    '''
    Blip = .0001*Fwd

    def ECall(Fwd, Strike, Vol, Texp, Df):
        return Df * BSFwd(True, Fwd, Strike, Vol, Texp)
    def EPut(Fwd, Strike, Vol, Texp, Df):
        return Df * BSFwd(False, Fwd, Strike, Vol, Texp)

    def ACall(Fwd, Strike, Vol, Texp, Df, Tr, D):
        return ECall(Fwd, Strike, Vol, Texp, Df)+WhaleyPremium(True, Fwd, Strike, Vol, Texp, D, Texp)[1] * Df/D
    def APut(Fwd, Strike, Vol, Texp, Df, Tr, D):
        return EPut(Fwd, Strike, Vol, Texp, Df)+WhaleyPremium(False, Fwd, Strike, Vol, Texp, D, Texp)[1] * Df/D

    def Price( Fwd, Strike, Vol, Texp, Df, Tr, D ):
        if IsCall:
            return ACall( Fwd, Strike, Vol, Texp, Df, Tr, D )
        else:
            return APut( Fwd, Strike, Vol, Texp, Df, Tr, D )

    if premiumTerms=='RISK':
        PriceMid = Price( Fwd, Strike, Vol, Texp, Df, Tr, D )
    PriceUp = Price( Fwd+Blip, Strike, Vol, Texp, Df, Tr, D )
    PriceDn = Price( Fwd-Blip, Strike, Vol, Texp, Df, Tr, D )
    fD = (PriceUp-PriceDn)/2./Blip

    if deltaTerms=='FORWARD':
        if smileTerms=='RISK':
            if premiumTerms=='BASE':
                fD = fD
            else:
                fD = fD - PriceMid / Fwd
        else:
            if premiumTerms=='BASE':
                fD = - fD * Fwd / Strike
            else:
                fD = - fD * Fwd / Strike + PriceMid / Strike
        return fD  / Df
    else:
        if smileTerms=='RISK':
            if premiumTerms=='BASE':
                fD = fD * Fwd / Spot
            else:
                fD = fD * Fwd / Spot - PriceMid / Spot
        else:
            if premiumTerms=='BASE':
                fD = - fD * Fwd / Strike
            else:
                fD = - fD * Fwd / Strike + PriceMid / Strike
        return fD

def BAWPremium( IsCall, Fwd, Strike, Vol, Texp, rd, rf ):
    '''
    Early exercise premium for american spot options based on Barone-Adesi, Whaley
    approximation formula. To compute the options prices, this needs to be added to
    the european options prices.
    '''
    if Texp <= 0. or Vol <=0:
        return 0.

    T   = Texp
    K   = Strike
    D   = exp( -rd * Texp)
    Dq  = exp( -rf * Texp )
    Phi = (IsCall and 1 or -1)

    k = (D==1.) and 2./Vol/Vol or 2.* rf/Vol/Vol/(1-D)
    # the expression in the middle is really the expression on the right in the limit D -> 1
    # note that lim_{D -> 1.} log(D)/(1-D) = -1.

    beta = 2.*(rd-rf)/Vol/Vol
    if Phi == 1:
        q2=(-(beta-1.)+sqrt((beta-1.)**2+4.*k))/2.
        def EarlyExerBdry( eeb ):
            x = D*BSFwd(True,eeb,K,Vol,T) + (1.-Dq*cnorm(fd1(eeb,K,Vol,T)))*eeb/q2 - eeb + K
            return x

        eeBdry = D*BSFwd(True,Fwd,K,Vol,T) + (1.-Dq*cnorm(fd1(Fwd,K,Vol,T)))* Fwd/q2 + K
        eeBdry = newton(EarlyExerBdry,eeBdry)
        if Fwd >= eeBdry:
            eePrem = -D*BSFwd(True,Fwd,K,Vol,T) + Fwd - K
        else:
            A2=(eeBdry/q2)*(1.-Dq*cnorm(fd1(eeBdry,K,Vol,T)))
            eePrem = A2 * pow(Fwd/eeBdry,q2)
    elif Phi == -1:
        q1=(-(beta-1.)-sqrt((beta-1.)**2+4.*k))/2.
        def EarlyExerBdry( eeb ):
            x = D*BSFwd(False,eeb,K,Vol,T) - (1.-Dq*cnorm(-fd1(eeb,K,Vol,T)))*eeb/q1 + eeb - K
            return x

        eeBdry = -D*BSFwd(False,Fwd,K,Vol,T) + (1.-Dq*cnorm(-fd1(Fwd,K,Vol,T)))*Fwd/q1 + K
        eeBdry = brentq(EarlyExerBdry,1e-12, K)
        if Fwd <= eeBdry:
            eePrem = -D*BSFwd(False,Fwd,K,Vol,T) + K - Fwd
        else:
            A1=-(eeBdry/q1)*(1.-Dq*cnorm(-fd1(eeBdry,K,Vol,T)))
            eePrem = A1 * pow(Fwd/eeBdry,q1)
    else:
        raise ValueError, 'option type can only be call or put'

    return eePrem

def BAWAmOptPricer( IsCall, Fwd, Strike, Vol, Texp, rd, rf ):
    prem = BAWPremium( IsCall, Fwd, Strike, Vol, Texp, rd, rf )
    D    = exp( -rd * Texp)
    Euro = D * BSFwd(IsCall, Fwd, Strike, Vol, Texp)
    return Euro + prem

def IBAWVol( IsCall, Fwd, Strike, Price, Texp, rd, rf):
    '''
    Implied vol for american options according to BAW
    '''
    Df   = exp( -rd * Texp)
    if Texp <= 0.:
        raise ValueError, 'maturity must be > 0'

    def f( vol ):
        return Price - Df * BSFwd(IsCall, Fwd, Strike, vol, Texp) - BAWPremium(IsCall, Fwd, Strike, vol, Texp, rd, rf)

    Vol = brentq(f,0.001, 10.0)

    if Vol<0 or Vol>100.:
        raise ValueError, 'the implied vol solver fails'

    return Vol

def LogNormalPaths(mu, cov, fwd, numPaths):
    ''' mu and fwd are 1d lists/arrays (1xn); cov is a 2d scipy.array (nxn); numPaths is int '''
    return (fwd*scipy.exp(numpy.random.multivariate_normal(mu, cov, numPaths) - 0.5*cov.diagonal())).transpose()

def AsianOptTW_Fwd(IsCall, Fwd, strike, RlzAvg, Vol, Texp, AvgPeriod, Rd):
    '''Calculate Asian option price using TurnbullWakeman model.
       This is just for forward options, not for stocks.
       RlzAvg is the realized average price(daily)
       AvgPeriod is the time length of averaging period, usually 22 for the SGX options
    '''

    Fwd = float(Fwd)
    strike = float(strike)
    RlzAvg = float(RlzAvg)

    tau = numpy.max([0, Texp - AvgPeriod])
    if AvgPeriod == 0:
        volA = Vol
    else:
        volA = asian_vol_adj(Vol, Texp, tau)

    X = numpy.copy(strike)
    if AvgPeriod > Texp:
        X = X * (AvgPeriod / Texp) - RlzAvg * (AvgPeriod - Texp) / Texp

    if X < 0:
        if IsCall:
            return (RlzAvg * (AvgPeriod - Texp) / AvgPeriod + Fwd * Texp / AvgPeriod - X) * exp(-Rd * Texp)
        else:
            return 0
    else:
        price = BSFwd(IsCall, Fwd, X, volA, Texp, Rd)
        if AvgPeriod > Texp:
            return price * Texp / AvgPeriod
        else:
            return price

def AsianFwdDelta(IsCall, Fwd, strike, RlzAvg, Vol, Texp, AvgPeriod, Rd):
    Fwd = float(Fwd)
    strike = float(strike)
    RlzAvg = float(RlzAvg)

    if AvgPeriod > Texp:
        x = strike * (AvgPeriod / Texp) - RlzAvg * (AvgPeriod - Texp) / Texp
    else:
        x = strike
    tau = numpy.max([0, Texp - AvgPeriod])

    if AvgPeriod > 0:
        volA = asian_vol_adj(Vol, Texp, tau)
    else:
        volA = Vol

    if x < 0:
        if IsCall:
            return exp(-Rd * Texp) * Texp / AvgPeriod
        else:
            return 0
    else:
        if Texp < AvgPeriod:
            multi = Texp / AvgPeriod
        else:
            multi = 1.0
        Asiand1 = (log(Fwd / x) + (volA * volA * 0.5) * Texp) / (volA * sqrt(Texp))
        if IsCall:
            return multi * exp(-Rd * Texp) * cnorm(Asiand1)
        else:
            return multi * exp(-Rd * Texp) * (cnorm(Asiand1) - 1.0)


def AsianFwdGamma(Fwd, strike, RlzAvg, Vol, Texp, AvgPeriod, Rd):
    Fwd = float(Fwd)
    strike = float(strike)
    RlzAvg = float(RlzAvg)

    if AvgPeriod > Texp:
        x = strike * (AvgPeriod / Texp) - RlzAvg * (AvgPeriod - Texp) / Texp
    else:
        x = strike
    tau = numpy.max([0, Texp - AvgPeriod])

    if AvgPeriod > 0:
        volA = asian_vol_adj(Vol, Texp, tau)
    else:
        volA = Vol

    if x < 0:
        return 0
    else:
        if Texp < AvgPeriod:
            multi = Texp / AvgPeriod
        else:
            multi = 1.0

        Asiand1 = (log(Fwd / x) + (volA * volA * 0.5) * Texp) / (volA * sqrt(Texp))
        ND = exp(-(Asiand1 * Asiand1 * 0.5)) / sqrt(2 * pi)
        return multi * exp(- Rd * Texp) * ND / (Fwd * volA * sqrt(Texp))


def AsianFwdTheta(IsCall, Fwd, strike, RlzAvg, Vol, Texp, AvgPeriod, Rd):
    Fwd = float(Fwd)
    strike = float(strike)
    RlzAvg = float(RlzAvg)

    if AvgPeriod < Texp:
        return (AsianOptTW_Fwd(IsCall, Fwd, strike, RlzAvg, Vol, Texp + 1.0 / 252.0, AvgPeriod, Rd) - \
                AsianOptTW_Fwd(IsCall, Fwd, strike, RlzAvg, Vol, Texp - 1.0 / 252.0, AvgPeriod, Rd)) / 2.0
    else:
        SA = (RlzAvg * (AvgPeriod - Texp) + Fwd / 252.0) / (AvgPeriod - Texp + 1.0 / 252.0)
        return AsianOptTW_Fwd(IsCall, Fwd, strike, RlzAvg, Vol, Texp, AvgPeriod, Rd) - \
               AsianOptTW_Fwd(IsCall, Fwd, strike, SA, Vol, Texp - 1.0 / 252.0, AvgPeriod, Rd)


def AsianFwdVega(Fwd, strike, RlzAvg, Vol, Texp, AvgPeriod, Rd):
    Fwd = float(Fwd)
    strike = float(strike)
    RlzAvg = float(RlzAvg)

    if AvgPeriod > Texp:
        x = strike * (AvgPeriod / Texp) - RlzAvg * (AvgPeriod - Texp) / Texp
    else:
        x = strike
    tau = numpy.max([0, Texp - AvgPeriod])

    if AvgPeriod > 0:
        M = (2.0 * exp(Vol * Vol * Texp) - 2.0 * exp(Vol * Vol * tau) * (1.0 + Vol * Vol * (Texp - tau))) / \
            ((Vol ** 4) * ((Texp - tau) ** 2))
        volA = sqrt(log(M) / Texp)
    else:
        volA = Vol

    if x < 0:
        return 0
    else:
        if Texp < AvgPeriod:
            multi = Texp / AvgPeriod
        else:
            multi = 1.0
        if AvgPeriod > 0:
            dM = 4.0 * (exp(Vol * Vol * Texp) * Texp * Vol - exp(Vol * Vol * tau) \
                        * ((Vol ** 3) * tau * (Texp - tau) + Vol * Texp)) / \
                 ((Vol ** 4) * (Texp - tau) * (Texp - tau)) - \
                 8.0 * (exp(Vol * Vol * Texp) - exp(Vol * Vol * tau) * (1.0 + Vol * Vol * (Texp - tau))) / \
                 ((Vol ** 5) * (Texp - tau) * (Texp - tau))

            dvA = 1.0 / (2.0 * volA) / Texp / M * dM
        else:
            dvA = 1.0
        Asiand1 = (log(Fwd / x) + volA * volA * 0.5 * Texp) / (volA * sqrt(Texp))
        ND = exp(-(Asiand1 * Asiand1 * 0.5)) / sqrt(2 * pi)
        return multi * Fwd * exp(-Rd * Texp) * ND * sqrt(Texp) * dvA * 0.01
    
