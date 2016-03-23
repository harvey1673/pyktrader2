import copy
import curve
import datetime
import graph
import hydra
import math
import plotxy
import pylab
import random
import tenor
import tsexprfns
import tsfns
import tweakmkt
import ww_test.BSHistVolTool as BSHistVol

TS_folder = '' #'ASG_MARKED_TS/'
def test_SingleTermStructure(und, startContract, endContract, Term = '1m', exceptionDateList = []):
    plotList =[]
    legendList = []
    mkt = hydra.db.read('/' + und)

    ContractList = mkt.ContractRange(startContract, endContract)

    for cont in ContractList:
        startD = datetime.date(1980,1,1)
        contString = und+'_'+ str(cont)
        expiryT = mkt.ExpirationDateByContract(cont)

        if expiryT !='N/A':
            endD = expiryT
        else:
            endD = datetime.date(2012,1,1)

        ts = tsfns.TimeSeries(contString, StartDate = startD, EndDate =endD, folder = TS_folder)
        if expiryT != endD:
            endD = expiryT = ts.Dates()[-1]

        IsCall = 1
        volTS = BSHistVol.BS_ATMVol_TermStr(IsCall, ts, expiryT, rd = 0.0, rf = 0.0, endVol = 0.0, termTenor=Term, rehedgingTenor ="1d", exceptionDateList=exceptionDateList)

        ToM = [ (expiryT - x).days/365.*12.0 for x in volTS.Dates()]
        vol = [ y*100.0 for y in volTS.Values()]
        plotList.append(zip(ToM,vol))
        legendList.append(str(cont))

    plotxy.PlotXY(plotList,Legends = legendList, xlabel='Time to expiry [months]', ylabel='BS Cumulative vol')

def test_SpreadTermStructure(undList, operator, startContract, endContract, Term, exceptionDateList):
    HRPlotList =[]
    HRLegendList = []
    CorrPlotList =[]
    CorrLegendList = []

    und1 = undList[0]
    und2 = undList[1]
    mkt1 = hydra.db.read('/' + und1)
    mkt2 = hydra.db.read('/' + und2)

    Op = operator
    ContractList = mkt2.ContractRange(startContract, endContract)

    for cont in ContractList:
        startD = datetime.date(1950,1,1)
        contString1 = und1 +'_'+ str(cont)
        contString2 = und2 +'_'+ str(cont)

        expiryT = min(mkt1.ExpirationDateByContract(cont), mkt2.ExpirationDateByContract(cont), cont)

        if expiryT !='N/A':
            endD = expiryT
        else:
            endD = datetime.date(2050,1,1)

        ts1 = tsfns.TimeSeries(contString1, StartDate = startD, EndDate =endD)
        ts2 = tsfns.TimeSeries(contString2, StartDate = startD, EndDate =endD)

        if expiryT != endD:
            endD = expiryT = min( ts1.Dates()[-1], ts2.Dates()[-1])


        HRVol, HRcorr, VolF1, VolF2 = BSHistVol.Spread_ATMVolCorr_TermStr(ts1 =ts1, ts2 =ts2, op =Op, expiryT =expiryT, r1 = 0.0, r2 = 0.0, termTenor=Term, exceptionDateList=exceptionDateList)

        ToM = [ (expiryT - x).days/365.*12.0 for x in HRVol.Dates()]
        cross_vol = [ y*100.0 for y in HRVol.Values()]
        corr = [ y*100.0 for y in HRcorr.Values()]

        HRPlotList.append(zip(ToM,cross_vol))
        HRLegendList.append(str(cont))
        CorrPlotList.append(zip(ToM,corr))
        CorrLegendList.append(str(cont))

    gridfig, ax, axF = plotxy.createFigure(pylab.figure(), GridEnabled=True)
    plotxy.PlotXY(HRPlotList,Legends = HRLegendList, xlabel='Time to expiry [months]', ylabel='HR BS Cumulative vol', figure=gridfig)

    gridfig, ax, axF = plotxy.createFigure(pylab.figure(), GridEnabled=True)
    plotxy.PlotXY(CorrPlotList,Legends = CorrLegendList, xlabel='Time to expiry [months]', ylabel='HR BS correlation', figure=gridfig)

def test_CSOTermStructure(und, spreadTenor, startContract, endContract, Term, exceptionDateList):
    CorrPlotList =[]
    LegendList = []
    HRPlotList = []

    mkt = hydra.db.read('/' + und)

    Op = '/'
    ContractList = mkt.ContractRange(startContract, endContract)

    for cont in ContractList:
        startD = datetime.date(1950,1,1)
        contEnd = cont + spreadTenor
        contString1 = und +'_'+ str(cont)
        contString2 = und +'_'+ str(contEnd)

        expiryT = min(mkt.ExpirationDateByContract(cont), cont)

        if expiryT !='N/A':
            endD = expiryT
        else:
            endD = datetime.date(2050,1,1)

        ts1 = tsfns.TimeSeries(contString1, StartDate = startD, EndDate =endD)
        ts2 = tsfns.TimeSeries(contString2, StartDate = startD, EndDate =endD)

        if expiryT != endD:
            endD = expiryT = ts1.Dates()[-1]


        HRVol, HRcorr, VolF1, VolF2 = BSHistVol.Spread_ATMVolCorr_TermStr(ts1 =ts1, ts2 =ts2, op =Op, expiryT =expiryT, r1 = 0.0, r2 = 0.0, termTenor=Term, exceptionDateList=exceptionDateList)

        ToM = [ (expiryT - x).days/365.*12.0 for x in HRVol.Dates()]
        corr = [ y*100.0 for y in HRcorr.Values()]
        hrvol = [ y*100.0 for y in HRVol.Values()]

        CorrPlotList.append(zip(ToM,corr))
        HRPlotList.append(zip(ToM, hrvol))
        LegendList.append(str(cont))

    gridfig, ax, axF = plotxy.createFigure(pylab.figure(), GridEnabled=True)
    plotxy.PlotXY(CorrPlotList,Legends = LegendList, xlabel='Time to expiry [months]', ylabel='HR BS correlation', figure=gridfig)

    gridfig, ax, axF = plotxy.createFigure(pylab.figure(), GridEnabled=True)
    plotxy.PlotXY(HRPlotList,Legends = LegendList, xlabel='Time to expiry [months]', ylabel='HR BS correlation', figure=gridfig)


def test_CCYCommodTermStr(und, ccyName, startContract, endContract, Term = '1m', exceptionDateList= []):
    HRPlotList =[]
    HRLegendList = []
    CorrPlotList =[]
    CorrLegendList = []

    ccyPair = ccyName+'-USD'
    pairObj = hydra.db[ '/' + ccyPair ]
    op = '*'

    mkt = hydra.db.read('/' + und)
    ContractList = mkt.ContractRange(startContract, endContract)

    for cont in ContractList:
        startD = datetime.date(1950,1,1)
        contString = und +'_'+ str(cont)
        expiryT = min(mkt.ExpirationDateByContract(cont), cont)

        if expiryT !='N/A':
            endD = expiryT
        else:
            endD = datetime.date(2012,1,1)

        ts1 = tsfns.TimeSeries(contString, StartDate = startD, EndDate =endD)

        if expiryT != endD:
            endD = expiryT = ts1.Dates()[-1]

        startD =ts1.Dates()[0]

        tsexprfns.StartDate = startD
        tsexprfns.EndDate = endD
        ts2 = tsexprfns.fxforwarddate(ccyPair, cont.strftime('%d%b%y'))

        HRVol, HRcorr, VolF1, VolF2 = BSHistVol.Spread_ATMVolCorr_TermStr(ts1 =ts1, ts2 =ts2, op =op, expiryT =expiryT, r1 = 0.0, r2 = 0.0, termTenor=Term, exceptionDateList= exceptionDateList)

        ToM = [ (expiryT - x).days/365.*12.0 for x in HRVol.Dates()]
        cross_vol = [ y*100.0 for y in HRVol.Values()]
        corr = [ y*100.0 for y in HRcorr.Values()]

        HRPlotList.append(zip(ToM,cross_vol))
        HRLegendList.append(str(cont))
        CorrPlotList.append(zip(ToM,corr))
        CorrLegendList.append(str(cont))

    gridfig, ax, axF = plotxy.createFigure(pylab.figure(), GridEnabled=True)
    plotxy.PlotXY(HRPlotList,Legends = HRLegendList, xlabel='Time to expiry [months]', ylabel='HR BS Cumulative vol', figure=gridfig)

    gridfig, ax, axF = plotxy.createFigure(pylab.figure(), GridEnabled=True)
    plotxy.PlotXY(CorrPlotList,Legends = CorrLegendList, xlabel='Time to expiry [months]', ylabel='HR BS correlation', figure=gridfig)

def test_CrackTermStructure(undList, weights, startContract, endContract, Term, exceptionDateList):
    undVolList = []
    CrkVolList = []
    legendList = []

    mkt = hydra.db.read('/' + undList[0])
    ContractList = mkt.ContractRange(startContract, endContract)

    for cont in ContractList:
        startD = datetime.date(2004,7,1)
        minDate = datetime.date(2050, 1, 1)
        tsList = []
        for und in undList:
            contString = und +'_'+ str(cont)
            mkt = hydra.db.read('/' + und)
            endD = min(mkt.ExpirationDateByContract(cont), cont)

            if endD =='N/A':
                endD = minDate

            ts = tsfns.TimeSeries(contString, StartDate = startD, EndDate =endD)
            tsList.append(ts)

            minDate = min(minDate, ts.Dates()[-1])

        endD= expiryT = minDate
        CrkVol, undVol = BSHistVol.Crack_ATMVol_TermStr(tsList, weights, expiryT, termTenor=Term, exceptionDateList=exceptionDateList)

        ToM = [ (expiryT - x).days/365.*12.0 for x in CrkVol.Dates()]
        crk_vol = [ y*100.0 for y in CrkVol.Values()]
        und_vol = [ y*100.0 for y in undVol.Values()]

        legendList.append(str(cont))
        CrkVolList.append(zip(ToM, crk_vol))
        undVolList.append(zip(ToM,und_vol))

    gridfig, ax, axF = plotxy.createFigure(pylab.figure(), GridEnabled=True)
    plotxy.PlotXY(undVolList, Legends = legendList, xlabel='Time to expiry [months]', ylabel='Underlier Cumulative Vol', figure=gridfig)

    gridfig, ax, axF = plotxy.createFigure(pylab.figure(), GridEnabled=True)
    plotxy.PlotXY(CrkVolList,Legends = legendList, xlabel='Time to expiry [months]', ylabel='Crack Vol', figure=gridfig)

def test_nearbyVolStructure(und, startD, endD, Term ='1m', exceptionDateList = []):
    plotList =[]
    legendList = []

    und = 'WTI_NYMEX'


    tsexprfns.StartDate = startD
    tsexprfns.EndDate = endD
    nearbyNum = 1
    ts = tsexprfns.nearbyfut(und, NearbyNum = nearbyNum)

    IsCall = 1
    volTS = BSHistVol.BS_ATMVol_TermStr(IsCall, ts, endD, rd = 0.0, rf = 0.0, endVol = 0.0, termTenor="15d", rehedgingTenor ="1d", exceptionDateList=exceptionDateList)
    plotList = [volTS]
    legendList = ['Vol']
    plotxy.PlotCurves(plotList,Legends = legendList)


def randTSGen(F0, Sigma, Kappa, StartDate ,EndDate):

    ts = curve.Curve()
    factors = len(Sigma)

    date = StartDate
    ts[date] = F0

    F =F0
    while tenor.RDateAdd('1d', date, Holidays=[]) <= EndDate:
        lastDate = date
        date = tenor.RDateAdd('1d', date, Holidays=[])

        dt = (date - lastDate).days/365.0
        tau = (EndDate - date).days/365.0

        x = 0.0
        for sig,kap in zip(Sigma, Kappa):
            x = x - 0.5* sig**2 * math.exp(-2*kap*tau) * dt + sig * math.exp(-kap*tau)* math.sqrt(dt) * random.gauss(0,1)

        F = F * math.exp(x)
        ts[date] = F

    return ts

def rand2DTSGen(F0, Sigma, Kappa, rho, StartDate ,EndDate):

    ts1 = curve.Curve()
    ts2 = curve.Curve()

    date = StartDate
    ts1[date] = F0[0]
    ts2[date] = F0[1]

    P = F0[0]
    G = F0[1]

    while tenor.RDateAdd('1d', date, Holidays=[]) <= EndDate:
        lastDate = date
        date = tenor.RDateAdd('1d', date, Holidays=[])

        dt = (date - lastDate).days/365.0
        tau = (EndDate - date).days/365.0

        y1 = random.gauss(0, 1)
        y2 = y1 * rho + math.sqrt(1-rho**2) * random.gauss(0, 1)

        x1 = -0.5 * Sigma[0]**2 * math.exp(-2*Kappa[0]*tau) * dt + Sigma[0] * math.exp(-Kappa[0]*tau)* math.sqrt(dt) * y1
        x2 = -0.5 * Sigma[1]**2 * math.exp(-2*Kappa[1]*tau) * dt + Sigma[1] * math.exp(-Kappa[1]*tau)* math.sqrt(dt) * y2

        P = P * math.exp(x1)
        G = G * math.exp(x2)

        ts1[date] = P
        ts2[date] = G

    return ts1, ts2

def test_SingleTermStrComp():
    IsCall = 1
    startD = datetime.date(2006,1,1)
    endD = datetime.date(2008,12,31)

    trueVol = curve.Curve()
    avgVol = curve.Curve()
    varVol = curve.Curve()

    expiryT = endD
    Sigma = [0.4, 0.2]
    Kappa = [2.0, 0.001]
    numPath = 100
    for i in range(numPath):
        ts = randTSGen(1, Sigma, Kappa, StartDate = startD, EndDate = endD)
        volTS = BSHistVol.BS_ATMVol_TermStr(IsCall, ts, expiryT, rd = 0.0, rf = 0.0, endVol = 0.0, termTenor="22d", rehedgingTenor ="1d", exceptionDateList=[])

        if i ==0:
            for d in volTS.Dates():
                tau = (expiryT-d).days/365.0
                x = 0.0
                for sig,kap in zip(Sigma, Kappa):
                    x = x+ sig**2*((1-math.exp(-2*kap*tau))/(2*kap*tau))

                x = math.sqrt(x)
                trueVol[d] = x
                avgVol[d] = 0.0
                varVol[d] = 0.0

        for d in volTS.Dates():
            avgVol[d] += volTS[d]/(numPath*1.0)
            varVol[d] += (volTS[d] - trueVol[d])**2/(numPath*1.0)

    plotList = [avgVol, trueVol]
    legendList = ['Vol', 'True Vol']
    plotxy.PlotCurves(plotList,Legends = legendList)
    diff = curve.Curve()
    rvar = curve.Curve()
    Texp = curve.Curve()
    for d in trueVol.Dates():
        diff[d] = avgVol[d] - trueVol[d]
        varVol[d] =math.sqrt(varVol[d])
        rvar[d] = varVol[d]/trueVol[d]
        Texp[d] = (expiryT-d).days/365.0*12.0

    DiffRatio = [ (Texp[d], diff[d], varVol[d], rvar[d]) for d in trueVol.Dates()]
    print DiffRatio

def test_CorrTestComp():
    IsCall = 1
    exceptionDateList = []
    op= '/'

    startD = datetime.date(2005,1,1)
    endD = datetime.date(2008,12,31)

    trueCorr = curve.Curve()
    avgCorr = curve.Curve()
    varCorr = curve.Curve()

    trueVol = curve.Curve()
    avgVol = curve.Curve()
    varVol = curve.Curve()

    expiryT = endD
    F = [1.0, 1.0]
    Sig = [0.8, 0.5]
    Kappa = [1.2, 0.8]
    rho = 0.9
    numPath = 200

    HRPlotList = []
    LegendList = []
    CorrPlotList = []

    for i in range(numPath):
        ts1, ts2 = rand2DTSGen(F, Sig, Kappa, rho, StartDate = startD, EndDate = endD)
        HRVol, HRcorr, VolF1, VolF2 = BSHistVol.Spread_ATMVolCorr_TermStr(ts1 =ts1, ts2 =ts2, op =op, expiryT =expiryT, r1 = 0.0, r2 = 0.0, termTenor="1m", exceptionDateList= exceptionDateList)

        ToM = [ (expiryT - x).days/365.*12.0 for x in HRVol.Dates()]
        cross_vol = [ y*100.0 for y in HRVol.Values()]
        corr = [ y*100.0 for y in HRcorr.Values()]

        HRPlotList.append(zip(ToM,cross_vol))
        LegendList.append(str(i))
        CorrPlotList.append(zip(ToM,corr))

        if i == 0:
            for d in HRVol.Dates():
                tau = (expiryT-d).days/365.0
                s1 = Sig[0]**2 * (1 - math.exp(-2 * Kappa[0] * tau))/(2 * Kappa[0] * tau)
                s2 = Sig[1]**2 * (1 - math.exp(-2 * Kappa[1] * tau))/(2 * Kappa[1] * tau)
                s12 = Sig[0] * Sig[1]* rho * (1 - math.exp(-(Kappa[0] + Kappa[1]) * tau))/((Kappa[0] + Kappa[1]) * tau)
                if op == '/':
                    s = math.sqrt(s1 + s2 - 2 * s12)
                else:
                    s = math.sqrt(s1 + s2 + 2 * s12)

                r = s12 / math.sqrt(s1 * s2)

                trueVol[d] = s
                trueCorr[d] = r
                avgVol[d] = 0.0
                varVol[d] = 0.0
                avgCorr[d] = 0.0
                varCorr[d] = 0.0

        for d in HRVol.Dates():
            avgVol[d] += HRVol[d]/(numPath*1.0)
            varVol[d] += (HRVol[d] - trueVol[d])**2/(numPath*1.0)
            avgCorr[d] += HRcorr[d]/(numPath*1.0)
            varCorr[d] += (HRcorr[d] - trueCorr[d])**2/(numPath*1.0)


    #gridfig, ax, axF = plotxy.createFigure(pylab.figure(), GridEnabled=True)
    #plotxy.PlotXY(HRPlotList,Legends = LegendList, figure=gridfig)
    #gridfig, ax, axF = plotxy.createFigure(pylab.figure(), GridEnabled=True)
    #plotxy.PlotXY(CorrPlotList,Legends = LegendList, figure=gridfig)

    plotList = [avgVol, trueVol]
    legendList = ['Vol', 'True Vol']
    gridfig, ax, axF = plotxy.createFigure(pylab.figure(), GridEnabled=True)
    plotxy.PlotCurves(plotList,Legends = legendList, figure=gridfig)

    plotList = [avgCorr, trueCorr]
    legendList = ['Corr', 'True Corr']
    gridfig, ax, axF = plotxy.createFigure(pylab.figure(), GridEnabled=True)
    plotxy.PlotCurves(plotList,Legends = legendList, figure=gridfig)

    diff = curve.Curve()
    rcorr = curve.Curve()
    Texp = curve.Curve()
    for d in trueVol.Dates():
        diff[d] = avgCorr[d] - trueCorr[d]
        varCorr[d] =math.sqrt(varCorr[d])
        rcorr[d] = varCorr[d]/trueCorr[d]
        Texp[d] = (expiryT-d).days/365.0*12.0

    DiffRatio = [ (Texp[d], diff[d], varCorr[d], rcorr[d]) for d in trueCorr.Dates()]
    print DiffRatio

def test_ConstDelta_VolSurface(und, Contract, Term = '1m', exceptionDateList = []):
    plotList =[]
    legendList = []
    mkt = hydra.db.read('/' + und)

    startD = datetime.date(2001,1,1)
    contString = und+'_'+ str(Contract)
    expiryT = mkt.ExpirationDateByContract(Contract)
    if expiryT !='N/A':
        endD = expiryT
    else:
        endD = datetime.date(2012,1,1)

    ts = tsfns.TimeSeries(contString, StartDate = startD, EndDate =endD)
    if expiryT != endD:
        endD = expiryT = ts.Dates()[-1]

    moneynessList = [0.95, 1.0, 1.05]
    volTS = BSHistVol.BS_ConstDelta_VolSurf(ts, moneynessList, expiryT, rd = 0.0, rf = 0.0, exceptionDateList=[])

    ToM  = []
    crvList = [[]]* len(moneynessList)
    for d in volTS.Dates():
        ToM += [(expiryT - d).days/365.*12.0]
        for n in range(len(moneynessList)):
            crvList[n].append(volTS[d][n]*100.0)

    for n in range(len(moneynessList)):
        plotList.append(zip(ToM,crvList[n]))
        legendList.append(str(moneynessList[n]))

    plotxy.PlotXY(plotList,Legends = legendList, xlabel='Time to expiry [months]', ylabel='BS Cumulative vol')

def main():
    und = 'WTI_NYMEX'
    startContract = 'Jan01'
    endContract = 'Dec02'
    Term = '1m'
    exceptionDateList = []
    # for NG_NYMEX Apr08:
    # exceptionDateList = [datetime.date(2006,5,29)]
    # for GO_0.05_SING
    #exceptionDateList = [datetime.date(2007,9,26), datetime.date(2007,9,27),datetime.date(2007,9,28),datetime.date(2007,10,1), datetime.date(2007,10,2),datetime.date(2007,10,3), datetime.date(2007,10,4), datetime.date(2007, 10, 18), datetime.date(2009, 3, 17)]
    # for KERO_SING
    # exceptionDateList = [datetime.date(2007,10,18), datetime.date(2009, 3, 17)]

    #test_SingleTermStructure(und, startContract, endContract, Term, exceptionDateList)


    #startD = datetime.date(2008,1,1)
    #endD = datetime.date(2008,12,29)
    # test_nearbyVolStructure(und, startD, endD, Term, exceptionDateList)

    undList = [ 'DUBAI', 'FO_380CST_SING_CARGOES']
    startContract = 'Sep08'
    endContract = 'May09'
    Term = '1m'
    #weights = [1.0, -0.1538 ]
    operator = '/'

    test_SpreadTermStructure(undList, operator, startContract, endContract, Term, exceptionDateList)
    #test_CrackTermStructure(undList, weights, startContract, endContract, Term, exceptionDateList)
    #ccyName = 'EUR'
    #test_CCYCommodTermStr(und, ccyName, startContract, endContract, Term = '1m', exceptionDateList= [])

    # test_SingleTermStrComp()
    # Contract = tenor.EnergyTenor('Jan09')
    # test_ConstDelta_VolSurface(und, Contract, Term = '1m', exceptionDateList = [])

    #test_CorrTestComp()
    #spreadTenor = '12m'
    #test_CSOTermStructure(und, spreadTenor, startContract, endContract, Term, exceptionDateList)