#-*- coding=utf-8 -*-
from pyctp.futures import ApiStruct, TraderApi, MdApi
from ctp.ctp_gateway import *
import time
import threading
import datetime
from base import *
from misc import *

THOST_TERT_RESTART  = ApiStruct.TERT_RESTART
THOST_TERT_RESUME   = ApiStruct.TERT_RESUME
THOST_TERT_QUICK    = ApiStruct.TERT_QUICK

class MyMarketData(MdApi):
    '''
        将行情信息转发到Agent
        并自行处理杂务
    '''
    def __init__(self,
            instruments, #合约映射 name ==>c_instrument
            broker_id,   #期货公司ID
            investor_id, #投资者ID
            passwd, #口令
        ):
        self.instruments = instruments
        self.broker_id =broker_id
        self.investor_id = investor_id
        self.passwd = passwd
        self.request_id = 0

    def inc_request_id(self):
        self.request_id += 1
        return self.request_id

    def user_login(self, broker_id, investor_id, passwd):
        req = ApiStruct.ReqUserLogin(BrokerID=broker_id, UserID=investor_id, Password=passwd)
        r=self.ReqUserLogin(req, self.inc_request_id())

    def OnRspUserLogin(self, userlogin, info, rid, is_last):
        print userlogin, info, rid, is_last
        self.subscribe_market_data(self.instruments)

    def OnFrontDisConnected(self, reason):
        print u'行情服务器连接断开'

    def subscribe_market_data(self, instruments):
        self.SubscribeMarketData(instruments)

    def OnFrontConnected(self):
        print u'行情服务器连接成功'
        self.user_login(self.broker_id, self.investor_id, self.passwd)

    def OnRtnDepthMarketData(self, dp):
        #print dp
        pass

class MyTraderApi(TraderApi):
    def __init__(self, broker_id,
                 investor_id, passwd, *args,**kwargs):
        self.requestid = 0
        self.orderRef = 0
        self.broker_id =broker_id
        self.investor_id = investor_id
        self.passwd = passwd
        self.lastupdate = datetime.datetime.now()
        self.instruments={'CFFEX':[], 'CZCE':[], 'DCE':[], 'SHFE':[]}

    def OnRspError(self, info, RequestId, IsLast):
        print " Error"
        self.isErrorRspInfo(info)

    def isErrorRspInfo(self, info):
        if info.ErrorID !=0:
            print "ErrorID=", info.ErrorID, ", ErrorMsg=", info.ErrorMsg
        return info.ErrorID !=0

    def OnFrontDisConnected(self, reason):
        print "onFrontDisConnected:", reason

    def OnHeartBeatWarning(self, time):
        print "onHeartBeatWarning", time

    def OnFrontConnected(self):
        print "OnFrontConnected:"
        self.user_login(self.broker_id, self.investor_id, self.passwd)

    def user_login(self, broker_id, investor_id, passwd):
        req = ApiStruct.ReqUserLogin(BrokerID=broker_id, UserID=investor_id, Password=passwd)
        self.requestid+=1
        r=self.ReqUserLogin(req, self.requestid)        

    def OnRspUserLogin(self, userlogin, info, rid, is_last):
        print userlogin
        print 'errMsg=%s' %(info.ErrorMsg,)
        #print "OnRspUserLogin", is_last, info
        #if is_last and not self.isErrorRspInfo(info):
        #    print "get today's trading day:", repr(self.GetTradingDay())
        #    self.subscribe_market_data(self.instruments)
        self.query_settlement_confirm() 
        
    def query_settlement_confirm(self):
        req = ApiStruct.QrySettlementInfoConfirm(BrokerID=self.broker_id,InvestorID=self.investor_id)
        self.requestid += 1
        self.ReqQrySettlementInfoConfirm(req,self.requestid)

    def OnRspQrySettlementInfoConfirm(self, pSettlementInfoConfirm, pRspInfo, nRequestID, bIsLast):
        '''请求查询结算信息确认响应'''
        self.query_settlement_info()

    def query_settlement_info(self):
        #不填日期表示取上一天结算单,并在响应函数中确认
        #print u'TD:取上一日结算单信息并确认,BrokerID=%s,investorID=%s' % (self.broker_id,self.investor_id)
        req = ApiStruct.QrySettlementInfo(BrokerID=self.broker_id,InvestorID=self.investor_id,TradingDay=u'')
        #print req.BrokerID,req.InvestorID,req.TradingDay
        #time.sleep(0.5)
        self.requestid += 1
        self.ReqQrySettlementInfo(req,self.requestid)

    def OnRspQrySettlementInfo(self, pSettlementInfo, pRspInfo, nRequestID, bIsLast):
        '''请求查询投资者结算信息响应'''
        #print u'Rsp 结算单查询'
        if(self.resp_common(pRspInfo,bIsLast,u'结算单查询')>0):
            #print u'结算单查询完成,准备确认'
            #try:
            #    print u'TD:结算单内容:%s' % pSettlementInfo.Content
            #except Exception,inst:
            #    print u'TD-ORQSI-A 结算单内容错误:%s' % str(inst)
            self.confirm_settlement_info()
        else:  #这里是未完成分支,需要直接忽略
            #try:
            #    print u'TD:结算单接收中...:%s' % pSettlementInfo.Content
            #except Exception,inst:
            #    print u'TD-ORQSI-B 结算单内容错误:%s' % str(inst)
            #self.agent.initialize()
            pass
        
    def confirm_settlement_info(self):
        #print u'TD-CSI:准备确认结算单'
        req = ApiStruct.SettlementInfoConfirm(BrokerID=self.broker_id,InvestorID=self.investor_id)
        self.requestid += 1
        self.ReqSettlementInfoConfirm(req,self.requestid)
    
    def OnRspSettlementInfoConfirm(self, pSettlementInfoConfirm, pRspInfo, nRequestID, bIsLast):
        '''投资者结算结果确认响应'''
        if(self.resp_common(pRspInfo,bIsLast,u'结算单确认')>0):
            pass
            #print u'TD:结算单确认时间: %s-%s' %(pSettlementInfoConfirm.ConfirmDate,pSettlementInfoConfirm.ConfirmTime)
            #print "start initialized"
            
    def isRspSuccess(self,RspInfo):
        return RspInfo == None or RspInfo.ErrorID == 0
    
    def resp_common(self,rsp_info,bIsLast,name='默认'):
        #self.logger.debug("resp: %s" % str(rsp_info))
        if not self.isRspSuccess(rsp_info):
            #print u"TD:%s失败" % name
            return -1
        elif bIsLast and self.isRspSuccess(rsp_info):
            #print u"TD:%s成功" % name
            return 1
        else:
            #print u"TD:%s结果: 等待数据接收完全..." % name
            return 0

    def queryDepthMarketData(self, instrument):
        req = ApiStruct.QryDepthMarketData(InstrumentID=instrument)
        self.requestid = self.requestid+1
        self.ReqQryDepthMarketData(req, self.requestid)
    
    def OnRspQryDepthMarketData(self, depth_market_data, pRspInfo, nRequestID, bIsLast):                    
        #print nRequestID
        #print pRspInfo
        print depth_market_data
        #t = datetime.datetime.now()
        #print t
        #if (t - self.lastupdate)>datetime.timedelta(seconds=1):
        #    self.lock.release()
        #    print "release the lock"

    def fetch_instrument_marginrate(self,instrument_id):
        req = ApiStruct.QryInstrumentMarginRate(BrokerID=self.broker_id,
                        InvestorID=self.investor_id,
                        InstrumentID=instrument_id,
                        HedgeFlag = ApiStruct.HF_Speculation
                )
        self.requestid += 1
        r = self.ReqQryInstrumentMarginRate(req,self.requestid)
        print u'A:查询保证金率%s, 函数发出返回值:%s' % (instrument_id, r)

    def OnRspQryInstrumentMarginRate(self, pInstrumentMarginRate, pRspInfo, nRequestID, bIsLast):
        '''
            保证金率回报。返回的必然是绝对值
        '''
        if bIsLast and self.isRspSuccess(pRspInfo):
            print pInstrumentMarginRate
        else:
            #logging
            pass
        
    def fetch_instrument(self,instrument_id):
        req = ApiStruct.QryInstrument(
                        InstrumentID=instrument_id,
                )
        self.requestid += 1
        r = self.ReqQryInstrument(req,self.requestid)
        print u'A:查询合约, 函数发出返回值:%s' % r
        
    def OnRspQryInstrument(self, pInst, pRspInfo, nRequestID, bIsLast):
        '''
            合约回报。
        '''
        #print pInst.InstrumentID, pInst.ProductClass, pInst.ExchangeID
        if bIsLast and self.isRspSuccess(pRspInfo):
            if (pInst.ExchangeID in self.instruments) and (pInst.ProductClass=='1'):
                cont = {}
                cont['instID'] = pInst.InstrumentID
                cont['margin_l'] = pInst.LongMarginRatio
                cont['margin_s'] = pInst.ShortMarginRatio
                cont['start_date'] = datetime.datetime.strptime(pInst.OpenDate,'%Y%M%d').date()
                cont['expiry'] = datetime.datetime.strptime(pInst.ExpireDate,'%Y%M%d').date()
                cont['product_code'] = pInst.ProductID
                self.instruments[pInst.ExchangeID].append(cont)
        else:
            if (str(pInst.ExchangeID) in self.instruments) and (pInst.ProductClass=='1'):
                cont = {}
                cont['instID'] = pInst.InstrumentID
                cont['margin_l'] = pInst.LongMarginRatio
                cont['margin_s'] = pInst.ShortMarginRatio
                cont['start_date'] = datetime.datetime.strptime(pInst.OpenDate,'%Y%m%d').date()
                cont['expiry'] = datetime.datetime.strptime(pInst.ExpireDate,'%Y%m%d').date()
                cont['product_code'] = pInst.ProductID
                self.instruments[pInst.ExchangeID].append(cont)

    def OnRtnOrder(self, pOrder):
        print pOrder

    def OnRtnTrade(self, pTrade):
        print pTrade

    def OnErrRtnOrderInsert(self, data, error):
        print data, error

    def OnErrRtnOrderAction(self, data, error):
        print data, error

    def OnRspOrderAction(self, data, error, n, last):
        print data, error, n, last
    
    def fetch_trading_account(self):
        #获取资金帐户
        
        print u'A:获取资金帐户..'
        req = ApiStruct.QryTradingAccount(BrokerID=self.broker_id, InvestorID=self.investor_id)
        self.requestid += 1
        r=self.ReqQryTradingAccount(req,self.requestid)
        #logging.info(u'A:查询资金账户, 函数发出返回值:%s' % r)

    def fetch_investor_position(self,instrument_id):
        #获取合约的当前持仓
        print u'A:获取合约%s的当前持仓..' % (instrument_id,)
        req = ApiStruct.QryInvestorPosition(BrokerID=self.broker_id, InvestorID=self.investor_id,InstrumentID=instrument_id)
        self.requestid += 1
        r=self.ReqQryInvestorPosition(req,self.requestid)
        #logging.info(u'A:查询持仓, 函数发出返回值:%s' % rP)
    
    def fetch_investor_position_detail(self,instrument_id):
        '''
            获取合约的当前持仓明细，目前没用
        '''
        
        print u'A:获取合约%s的当前持仓..' % (instrument_id,)
        req = ApiStruct.QryInvestorPositionDetail(BrokerID=self.broker_id, InvestorID=self.investor_id,InstrumentID=instrument_id)
        self.requestid += 1
        r=self.ReqQryInvestorPositionDetail(req,self.requestid)

    def fetch_order(self, t_start='09:00:00', t_end='15:15:00'):
        req = ApiStruct.QryOrder(
                        BrokerID=self.broker_id, 
                        InvestorID=self.investor_id,
                        InstrumentID='',
                        ExchangeID = '', #交易所代码, char[9]
                        #OrderSysID = '', #报单编号, char[21]
                        InsertTimeStart = '', #开始时间, char[9]
                        InsertTimeEnd = '', #结束时间, char[9]
                )
        self.requestid += 1
        r = self.ReqQryOrder(req, self.requestid)

    def fetch_trade(self, t_start='09:00:00', t_end='15:15:00'):
        req = ApiStruct.QryTrade(
                        BrokerID=self.broker_id, 
                        InvestorID=self.investor_id,
                        InstrumentID='',
                        ExchangeID ='', #交易所代码, char[9]
                        #TradeID = '', #报单编号, char[21]
                        TradeTimeStart = '', #开始时间, char[9]
                        TradeTimeEnd = '', #结束时间, char[9]
                )
        self.requestid += 1
        r = self.ReqQryTrade(req, self.requestid)
        
    def OnRspQryTradingAccount(self, pTradingAccount, pRspInfo, nRequestID, bIsLast):
        '''
            请求查询资金账户响应
        '''
        print u'查询资金账户响应', pTradingAccount
        if bIsLast and self.isRspSuccess(pRspInfo):
            print pTradingAccount
        else:
            #logging
            pass

    def OnRspQryInvestorPosition(self, pInvestorPosition, pRspInfo, nRequestID, bIsLast):
        '''请求查询投资者持仓响应'''
        if self.isRspSuccess(pRspInfo): #每次一个单独的数据报
            print pInvestorPosition, "True"
        else:
            #logging
            print pInvestorPosition, "False"
            pass

    def OnRspQryInvestorPositionDetail(self, pInvestorPositionDetail, pRspInfo, nRequestID, bIsLast):
        print u'请求查询投资者持仓明细响应'
        if self.isRspSuccess(pRspInfo): #每次一个单独的数据报
            print pInvestorPositionDetail
        else:
            #logging
            pass

    def OnRspQryOrder(self, pOrder, pRspInfo, nRequestID, bIsLast):
        '''请求查询报单响应'''
        if bIsLast and self.isRspSuccess(pRspInfo):
            print 'last:%s' % pOrder
        else:
            print 'first: %s' % pOrder

    def OnRspQryTrade(self, pTrade, pRspInfo, nRequestID, bIsLast):
        '''请求查询成交响应'''
        if bIsLast and self.isRspSuccess(pRspInfo):
            print 'last:%s' % pTrade
        else:
            print 'first: %s' % pTrade

    def fetch_instruments_by_exchange(self,exchange_id):
        '''不能单独用exchange_id,因此没有意义
        '''
        req = ApiStruct.QryInstrument(
                        ExchangeID=exchange_id,
                )
        self.requestid += 1
        r = self.ReqQryInstrument(req,self.requestid)
        print u'A:查询合约, 函数发出返回值:%s' % r
        
    def OnRtnDepthMarketData(self, depth_market_data):
        print "OnRtnDepthMarketData"
        #print depth_market_data.BidPrice1,depth_market_data.BidVolume1,depth_market_data.AskPrice1,depth_market_data.AskVolume1,depth_market_data.LastPrice,depth_market_data.Volume,depth_market_data.UpdateTime,depth_market_data.UpdateMillisec,depth_market_data.InstrumentID

    def sendOrder(self, req):
        """发单"""
        self.requestid += 1
        req['InvestorID'] = self.investor_id
        req['UserID'] = self.investor_id
        req['BrokerID'] = self.broker_id
        req_data = ApiStruct.InputOrder(**req)
        self.ReqOrderInsert(req_data, self.requestid)

def main():
    insts = ['m1701'] #'SPC a1701&m1701', 'SP a1701&a1705']
    tdcfg1 = BaseObject( broker_id="9999",
                         investor_id="066419",
                         passwd="801289",
                         ports=["tcp://180.168.146.187:10000"])
    tdcfg2 = BaseObject( broker_id="9999",
                         investor_id="066419",
                         passwd="801289",
                         ports=["tcp://180.168.146.187:10030"])
    mdcfg1 = BaseObject( broker_id="9999",
                         investor_id="066419",
                         passwd="801289",
                         ports=["tcp://180.168.146.187:10010"])
    mdcfg2 = BaseObject( broker_id="9999",
                         investor_id="066419",
                         passwd="801289",
                         ports=["tcp://180.168.146.187:10031"])
    tdcfg = tdcfg1 #PROD_TRADER
    mdcfg = mdcfg1 #PROD_USER
    md = MyMarketData(instruments= insts,
                        broker_id = mdcfg.broker_id,
                        investor_id= mdcfg.investor_id,
                        passwd= mdcfg.passwd,
                    )
    md.Create("ctp_md_tester")
    md.RegisterFront(mdcfg.ports[0])
    md.Init()

    user = MyTraderApi(broker_id = tdcfg.broker_id,
                       investor_id = tdcfg.investor_id,
                       passwd=tdcfg.passwd)
    user.Create("ctp_trader_tester")
    user.SubscribePublicTopic(THOST_TERT_QUICK)
    user.SubscribePrivateTopic(THOST_TERT_QUICK)
    user.RegisterFront(tdcfg.ports[0])
    user.Init()
    time.sleep(2)
    #user.queryDepthMarketData('SPC a1701&m1701')
    #time.sleep(2)
    #user.fetch_investor_position('')
    #time.sleep(2)
    #user.fetch_trading_account()
    req = {}
    price_type = OPT_FAK_ORDER
    req['InstrumentID'] = 'ni1701' #'SPC a1701&m1701'
    req['LimitPrice'] = 83730.0
    req['VolumeTotalOriginal'] = 2
    # 下面如果由于传入的类型本接口不支持，则会返回空字符串
    req['Direction'] = ORDER_BUY
    req['CombOffsetFlag'] = OF_OPEN
    req['OrderPriceType'] = price_type
    req['TimeCondition'] = defineDict['THOST_FTDC_TC_GFD']               # 今日有效
    req['VolumeCondition'] = defineDict['THOST_FTDC_VC_AV']              # 任意成交量
    if price_type == OPT_FAK_ORDER:
        req['OrderPriceType'] = defineDict["THOST_FTDC_OPT_LimitPrice"]
        req['TimeCondition'] = defineDict['THOST_FTDC_TC_IOC']
        req['VolumeCondition'] = defineDict['THOST_FTDC_VC_AV']
    elif price_type == OPT_FOK_ORDER:
        req['OrderPriceType'] = defineDict["THOST_FTDC_OPT_LimitPrice"]
        req['TimeCondition'] = defineDict['THOST_FTDC_TC_IOC']
        req['VolumeCondition'] = defineDict['THOST_FTDC_VC_CV']
    req['OrderRef'] = '004'
    req['CombHedgeFlag'] = defineDict['THOST_FTDC_HF_Speculation']       # 投机单
    req['ContingentCondition'] = defineDict['THOST_FTDC_CC_Immediately'] # 立即发单
    req['ForceCloseReason'] = defineDict['THOST_FTDC_FCC_NotForceClose'] # 非强平
    req['IsAutoSuspend'] = 0                                             # 非自动挂起
    req['MinVolume'] = 1                                                 # 最小成交量为1
    user.sendOrder(req)
    time.sleep(60)
    #for exch in user.instruments:
    #    print 'exch = %s, num = %s' % ( exch, len(user.instruments[exch]))
    #    for inst in user.instruments[exch]:
    #        mysqlaccess.insert_cont_data(inst)
    #return True

if __name__=="__main__": main()
