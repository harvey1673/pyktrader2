# encoding: UTF-8
import os
import pyctp.futures as py_ctp
from base import *
from misc import *
from gateway import *
from ctp_gateway import *
import logging
import datetime

class PyctpGateway(CtpGateway):
    def __init__(self, agent, gatewayName='CTP'):
        super(PyctpGateway, self).__init__(agent, gatewayName, md_api = 'ctp.pyctp_gateway.PyctpMdApi', td_api = 'ctp.pyctp_gateway.PyctpTdApi')
    
########################################################################
class PyctpMdApi(py_ctp.MdApi):
    """CTP行情API实现"""

    #----------------------------------------------------------------------
    ApiStruct = py_ctp.ApiStruct
    def __init__(self, gateway):
        """Constructor"""
        super(PyctpMdApi, self).__init__()
        
        self.gateway = gateway                  # gateway对象
        self.gatewayName = gateway.gatewayName  # gateway对象名称
        self.reqID = EMPTY_INT              # 操作请求编号
        self.connectionStatus = False       # 连接状态
        self.loginStatus = False            # 登录状态
        self.userID = EMPTY_STRING          # 账号
        self.password = EMPTY_STRING        # 密码
        self.brokerID = EMPTY_STRING        # 经纪商代码
        self.address = EMPTY_STRING         # 服务器地址
        self.trading_day = 20160101
        
    #----------------------------------------------------------------------
    def OnFrontConnected(self):
        """服务器连接"""
        self.connectionStatus = True
        logContent = u'行情服务器连接成功'
        self.gateway.onLog(logContent, level = logging.INFO)
        self.login()
    
    #----------------------------------------------------------------------  
    def OnFrontDisconnected(self, n):
        """服务器断开"""
        self.connectionStatus = False
        self.loginStatus = False
        self.gateway.mdConnected = False
        logContent = u'行情服务器连接断开'
        self.gateway.onLog(logContent, level = logging.INFO)      
        
    #---------------------------------------------------------------------- 
    def OnHeartBeatWarning(self, n):
        """心跳报警"""
        # 因为API的心跳报警比较常被触发，且与API工作关系不大，因此选择忽略
        pass
    
    #----------------------------------------------------------------------   
    def OnRspError(self, info, request_id, isLast):
        """错误回报"""
        err = VtErrorData()
        err.gatewayName = self.gatewayName
        err.errorID = info.ErrorID
        err.errorMsg = info.ErrorMsg.decode('gbk')
        self.gateway.onError(err)
        
    #----------------------------------------------------------------------
    def OnRspUserLogin(self, userlogin, info, rid, is_last):
        """登陆回报"""
        # 如果登录成功，推送日志信息
        if (info.ErrorID == 0) and is_last:
            self.loginStatus = True
            self.gateway.mdConnected = True
            logContent = u'行情服务器登录完成'
            self.gateway.onLog(logContent, level = logging.INFO)
            # 重新订阅之前订阅的合约
            for instID in self.gateway.instruments:
                self.subscribe(instID)
            trade_day_str = self.GetTradingDay()
            if len(trade_day_str) > 0:
                try:
                    self.trading_day = int(trade_day_str)
                    tradingday = datetime.datetime.strptime(trade_day_str, '%Y%m%d').date()
                    if tradingday > self.gateway.agent.scur_day:
                        event = Event(type=EVENT_DAYSWITCH)
                        event.dict['log'] = u'换日: %s -> %s' % (self.gateway.agent.scur_day, self.trading_day)
                        event.dict['date'] = tradingday
                        self.gateway.eventEngine.put(event)
                except ValueError:
                    pass
        # 否则，推送错误信息
        else:
            err = VtErrorData()
            err.gatewayName = self.gatewayName
            err.errorID = info.ErrorID
            err.errorMsg = info.ErrorMsg.decode('gbk')
            self.gateway.onError(err)
                
    #---------------------------------------------------------------------- 
    def OnRspUserLogout(self, userlogout, info, rid, is_last):
        """登出回报"""
        # 如果登出成功，推送日志信息
        if info.ErrorID == 0:
            self.loginStatus = False
            self.gateway.tdConnected = False
            logContent = u'行情服务器登出完成'
            self.gateway.onLog(logContent, level = logging.INFO)
                
        # 否则，推送错误信息
        else:
            err = VtErrorData()
            err.gatewayName = self.gatewayName
            err.errorID = info.ErrorID
            err.errorMsg = info.ErrorMsg.decode('gbk')
            self.gateway.onError(err)
        
    #----------------------------------------------------------------------  
    def OnRspSubMarketData(self, sub_market_data, info, rid, is_last):
        """订阅合约回报"""
        # 通常不在乎订阅错误，选择忽略
        pass
        
    #----------------------------------------------------------------------  
    def OnRspUnSubMarketData(self, unsub_market_data, info, rid, is_last):
        """退订合约回报"""
        # 同上
        pass  
        
    #----------------------------------------------------------------------  
    def OnRtnDepthMarketData(self, dp):
        """行情推送"""
        if (dp.LastPrice > dp.UpperLimitPrice) or (dp.LastPrice < dp.LowerLimitPrice) or \
                (dp.AskPrice1 >= dp.UpperLimitPrice and dp.BidPrice1 <= dp.LowerLimitPrice) or \
                (dp.BidPrice1 >= dp.AskPrice1):
            logContent = u'MD:error in market data for %s LastPrice=%s, BidPrice=%s, AskPrice=%s' % \
                             (dp.InstrumentID, dp.LastPrice, dp.BidPrice1, dp.AskPrice1)
            self.gateway.onLog(logContent, level = logging.DEBUG)
            return
        event = Event(type = EVENT_MARKETDATA + self.gatewayName)
        event.dict['data'] = dict((name, getattr(dp, name)) for name in dir(dp) if not name.startswith('_'))
        event.dict['gateway'] = self.gatewayName
        self.gateway.eventEngine.put(event)
        
    #---------------------------------------------------------------------- 
    def OnRspSubForQuoteRsp(self, data, error, n, last):
        """订阅期权询价"""
        pass
        
    #----------------------------------------------------------------------
    def OnRspUnSubForQuoteRsp(self, data, error, n, last):
        """退订期权询价"""
        pass 
        
    #---------------------------------------------------------------------- 
    def OnRtnForQuoteRsp(self, data):
        """期权询价推送"""
        pass        
        
    #----------------------------------------------------------------------
    def connect(self, userID, password, brokerID, address):
        """初始化连接"""
        self.userID = userID                # 账号
        self.password = password            # 密码
        self.brokerID = brokerID            # 经纪商代码
        self.address = address              # 服务器地址

        # 如果尚未建立服务器连接，则进行连接
        if not self.connectionStatus:
            # 创建C++环境中的API对象，这里传入的参数是需要用来保存.con文件的文件夹路径
            path = self.gateway.file_prefix + 'tmp' + os.path.sep
            if not os.path.exists(path):
                os.makedirs(path)

            self.Create(str(path))
            # 注册服务器地址
            self.RegisterFront(self.address)
            
            # 初始化连接，成功会调用onFrontConnected
            self.Init()
            
        # 若已经连接但尚未登录，则进行登录
        else:
            if not self.loginStatus:
                self.login()
        
    #----------------------------------------------------------------------
    def subscribe(self, symbol):
        """订阅合约"""
        # 这里的设计是，如果尚未登录就调用了订阅方法
        # 则先保存订阅请求，登录完成后会自动订阅
        if self.loginStatus:
            self.SubscribeMarketData([str(symbol)])
        if symbol not in self.gateway.instruments:
            self.gateway.instruments.append(symbol)
        
    #----------------------------------------------------------------------
    def login(self):
        """登录"""
        # 如果填入了用户名密码等，则登录
        if self.userID and self.password and self.brokerID:
            req = {}
            req['UserID'] = self.userID
            req['Password'] = self.password
            req['BrokerID'] = self.brokerID
            req_data = self.ApiStruct.ReqUserLogin(**req)
            self.reqID += 1
            self.ReqUserLogin(req_data, self.reqID)    

    def logout(self):
        if self.userID and self.brokerID:
            req = {}
            req['UserID'] = self.userID
            req['BrokerID'] = self.brokerID
            req_data = self.ApiStruct.ReqUserLogout(**req)
            self.reqID += 1
            self.ReqUserLogout(req_data, self.reqID)

    #----------------------------------------------------------------------
    def close(self):
        """关闭"""
        pass


########################################################################
class PyctpTdApi(py_ctp.TraderApi):
    """CTP交易API实现"""
    
    #----------------------------------------------------------------------
    ApiStruct = py_ctp.ApiStruct
    def __init__(self, gateway):
        """API对象的初始化函数"""
        super(PyctpTdApi, self).__init__()
        
        self.gateway = gateway                  # gateway对象
        self.gatewayName = gateway.gatewayName  # gateway对象名称
        
        self.reqID = EMPTY_INT              # 操作请求编号
        self.orderRef = EMPTY_INT           # 订单编号
        
        self.connectionStatus = False       # 连接状态
        self.loginStatus = False            # 登录状态
        
        self.userID = EMPTY_STRING          # 账号
        self.password = EMPTY_STRING        # 密码
        self.brokerID = EMPTY_STRING        # 经纪商代码
        self.address = EMPTY_STRING         # 服务器地址
        
        self.frontID = EMPTY_INT            # 前置机编号
        self.sessionID = EMPTY_INT          # 会话编号
        
    #----------------------------------------------------------------------
    def isRspSuccess(self, error):
        return error == None or error.ErrorID == 0

    def OnFrontConnected(self):
        """服务器连接"""
        self.connectionStatus = True
        logContent = u'交易服务器连接成功'
        self.gateway.onLog(logContent, level = logging.INFO)
        
        self.login()
    
    #----------------------------------------------------------------------
    def OnFrontDisconnected(self, n):
        """服务器断开"""
        self.connectionStatus = False
        self.loginStatus = False
        self.gateway.tdConnected = False

        logContent = u'交易服务器连接断开'
        self.gateway.onLog(logContent, level = logging.INFO)
    
    #----------------------------------------------------------------------
    def OnHeartBeatWarning(self, n):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspAuthenticate(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspUserLogin(self, data, info, rid, is_last):
        """登陆回报"""
        # 如果登录成功，推送日志信息
        if info.ErrorID == 0:
            self.frontID = str(data.FrontID)
            self.sessionID = str(data.SessionID)
            self.loginStatus = True
            logContent = u'交易服务器登录完成'
            self.gateway.onLog(logContent, level = logging.INFO)
            
            # 确认结算信息
            req = {}
            req['BrokerID'] = self.brokerID
            req['InvestorID'] = self.userID
            self.reqID += 1
            req_data = self.ApiStruct.SettlementInfoConfirm(**req)
            self.ReqSettlementInfoConfirm(req_data, self.reqID)			
                
        # 否则，推送错误信息
        else:
            self.loginStatus = False
            self.gateway.tdConnected = False
            err = VtErrorData()
            err.gatewayName = self.gateway
            err.errorID = info.ErrorID
            err.errorMsg = info.ErrorMsg.decode('gbk')
            self.gateway.onError(err)			
            time.sleep(30)
            self.login()
    
    #----------------------------------------------------------------------
    def OnRspUserLogout(self, data, info, rid, is_last):
        """登出回报"""
        # 如果登出成功，推送日志信息
        if info.ErrorID == 0:
            self.loginStatus = False
            self.gateway.tdConnected = False
            logContent = u'交易服务器登出完成'
            self.gateway.onLog(logContent, level = logging.INFO)
                
        # 否则，推送错误信息
        else:
            err = VtErrorData()
            err.gatewayName = self.gatewayName
            err.errorID = info.ErrorID
            err.errorMsg = info.ErrorMsg.decode('gbk')
            self.gateway.onError(err)
    
    #----------------------------------------------------------------------
    def OnRspUserPasswordUpdate(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspTradingAccountPasswordUpdate(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspOrderInsert(self, data, error, n, last):
        """发单错误（柜台）"""
        err = VtErrorData()
        err.gatewayName = self.gatewayName
        err.errorID = error.ErrorID
        err.errorMsg = error.ErrorMsg.decode('gbk')
        self.gateway.onError(err)

        if data != None:
            event2 = Event(type=EVENT_ERRORDERINSERT + self.gatewayName)
            event2.dict['data'] = dict((name, getattr(data, name)) for name in dir(data) if not name.startswith('_'))
            event2.dict['error'] = dict((name, getattr(error, name)) for name in dir(error) if not name.startswith('_'))
            event2.dict['gateway'] = self.gatewayName
            self.gateway.eventEngine.put(event2)
    
    #----------------------------------------------------------------------
    def OnRtnOrder(self, data):
        """报单回报"""
        # 更新最大报单编号
        if data != None:
            event = Event(type=EVENT_RTNORDER + self.gatewayName)
            event.dict['data'] = dict((name, getattr(data, name)) for name in dir(data) if not name.startswith('_'))
            self.gateway.eventEngine.put(event)
    
    #----------------------------------------------------------------------
    def OnRtnTrade(self, data):
        """成交回报"""
        # 创建报单数据对象
        if data != None:
            event = Event(type=EVENT_RTNTRADE+self.gatewayName)
            event.dict['data'] = dict((name, getattr(data, name)) for name in dir(data) if not name.startswith('_'))
            self.gateway.eventEngine.put(event)
    
    #----------------------------------------------------------------------
    def OnErrRtnOrderInsert(self, data, error):
        """发单错误回报（交易所）"""
        if data != None:
            event = Event(type=EVENT_ERRORDERINSERT + self.gatewayName)
            event.dict['data'] = dict((name, getattr(data, name)) for name in dir(data) if not name.startswith('_'))
            event.dict['error'] = dict((name, getattr(error, name)) for name in dir(error) if not name.startswith('_'))
            self.gateway.eventEngine.put(event)

        err = VtErrorData()
        err.gatewayName = self.gatewayName
        err.errorID = error.ErrorID
        err.errorMsg = error.ErrorMsg.decode('gbk')
        self.gateway.onError(err)
    
    #----------------------------------------------------------------------
    def OnErrRtnOrderAction(self, data, error):
        """撤单错误回报（交易所）"""
        if data != None:
            event = Event(type=EVENT_ERRORDERCANCEL + self.gatewayName)
            event.dict['data'] = dict((name, getattr(data, name)) for name in dir(data) if not name.startswith('_'))
            event.dict['error'] = dict((name, getattr(error, name)) for name in dir(error) if not name.startswith('_'))
            event.dict['gateway'] = self.gatewayName
            self.gateway.eventEngine.put(event)

        err = VtErrorData()
        err.gatewayName = self.gatewayName
        err.errorID = error.ErrorID
        err.errorMsg = error.ErrorMsg.decode('gbk')
        self.gateway.onError(err)

    #----------------------------------------------------------------------
    def OnRspOrderAction(self, data, error, n, last):
        """撤单错误（柜台）"""
        err = VtErrorData()
        err.gatewayName = self.gatewayName
        err.errorID = error.ErrorID
        err.errorMsg = error.ErrorMsg.decode('gbk')
        self.gateway.onError(err)
        if data != None:
            event2 = Event(type=EVENT_ERRORDERCANCEL + self.gatewayName)
            event2.dict['data'] = dict((name, getattr(data, name)) for name in dir(data) if not name.startswith('_'))
            event2.dict['error'] = dict((name, getattr(error, name)) for name in dir(error) if not name.startswith('_'))
            event2.dict['gateway'] = self.gatewayName
            self.gateway.eventEngine.put(event2)

    #----------------------------------------------------------------------
    def OnRspQueryMaxOrderVolume(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspSettlementInfoConfirm(self, data, error, n, last):
        """确认结算信息回报"""
        self.gateway.tdConnected = True
        event = Event(type=EVENT_TDLOGIN+self.gatewayName)
        self.gateway.eventEngine.put(event)

        # 查询合约代码
        # self.reqID += 1
        # self.reqQryInstrument({}, self.reqID)
        logContent = u'结算信息确认完成'
        self.gateway.onLog(logContent, level = logging.INFO)
    
    #----------------------------------------------------------------------
    def OnRspQryTradingAccount(self, data, error, n, last):
        """资金账户查询回报"""
        if self.isRspSuccess(error):
            items =  dict((name, getattr(data, name)) for name in dir(data) if not name.startswith('_'))
            if len(items) > 0:
                event = Event(type=EVENT_QRYACCOUNT + self.gatewayName )
                event.dict['data'] = items
                event.dict['last'] = last
                self.gateway.eventEngine.put(event)
        else:
            logContent = u'资金账户查询回报，错误代码：' + unicode(error.ErrorID) + u',' + u'错误信息：' + error.ErrorMsg.decode('gbk')
            self.gateway.onLog(logContent, level = logging.DEBUG)

    #----------------------------------------------------------------------
    def OnRspParkedOrderInsert(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspParkedOrderAction(self, data, error, n, last):
        """"""
        pass
        
    #----------------------------------------------------------------------
    def OnRspRemoveParkedOrder(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspRemoveParkedOrderAction(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspExecOrderInsert(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspExecOrderAction(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspForQuoteInsert(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQuoteInsert(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQuoteAction(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQryOrder(self, data, error, n, last):
        """"""
        '''请求查询报单响应'''
        if self.isRspSuccess(error):
            if data != None:
                event = Event(type=EVENT_QRYORDER + self.gatewayName )
                event.dict['data'] = dict((name, getattr(data, name)) for name in dir(data) if not name.startswith('_'))
                event.dict['error'] = dict((name, getattr(error, name)) for name in dir(error) if not name.startswith('_'))
                event.dict['last'] = last
                self.gateway.eventEngine.put(event)
        else:
            logContent = u'交易错误回报，错误代码：' + unicode(error.ErrorID) + u',' + u'错误信息：' + error.ErrorMsg.decode('gbk')
            self.gateway.onLog(logContent, level = logging.DEBUG)
    
    #----------------------------------------------------------------------
    def OnRspQryTrade(self, data, error, n, last):
        """"""
        if self.isRspSuccess(error):
            if data != None:
                event = Event(type=EVENT_QRYTRADE + self.gatewayName )
                event.dict['data'] = dict((name, getattr(data, name)) for name in dir(data) if not name.startswith('_'))
                event.dict['error'] = dict((name, getattr(error, name)) for name in dir(error) if not name.startswith('_'))
                event.dict['last'] = last
                self.gateway.eventEngine.put(event)
        else:
            event = Event(type=EVENT_LOG)
            logContent = u'交易错误回报，错误代码：' + unicode(error.ErrorID) + u',' + u'错误信息：' + error.ErrorMsg.decode('gbk')
            self.gateway.onLog(logContent, level = logging.DEBUG)
    
    #----------------------------------------------------------------------
    def OnRspQryInvestorPosition(self, data, error, n, last):
        """持仓查询回报"""
        if self.isRspSuccess(error):
            if data != None:
                event = Event(type=EVENT_QRYPOSITION + self.gatewayName )
                event.dict['data'] = dict((name, getattr(data, name)) for name in dir(data) if not name.startswith('_'))
                event.dict['error'] = dict((name, getattr(error, name)) for name in dir(error) if not name.startswith('_'))
                event.dict['last'] = last
                self.gateway.eventEngine.put(event)
        else:
            logContent = u'持仓查询回报，错误代码：' + unicode(error.ErrorID) + u',' + u'错误信息：' + error.ErrorMsg.decode('gbk')
            self.gateway.onLog(logContent, level = logging.DEBUG)

    #----------------------------------------------------------------------
    def OnRspQryInvestor(self, data, error, n, last):
        """投资者查询回报"""
        if self.isRspSuccess(error):
            if data != None:
                event = Event(type=EVENT_QRYINVESTOR + self.gatewayName )
                event.dict['data'] = dict((name, getattr(data, name)) for name in dir(data) if not name.startswith('_'))
                event.dict['error'] = dict((name, getattr(error, name)) for name in dir(error) if not name.startswith('_'))
                event.dict['last'] = last
                self.gateway.eventEngine.put(event)
        else:
            logContent = u'合约投资者回报，错误代码：' + unicode(error.ErrorID) + u',' + u'错误信息：' + error.ErrorMsg.decode('gbk')
            self.gateway.onLog(logContent, level = logging.DEBUG)
    
    #----------------------------------------------------------------------
    def OnRspQryTradingCode(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQryInstrumentMarginRate(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQryInstrumentCommissionRate(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQryExchange(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQryProduct(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQryInstrument(self, data, error, n, last):
        """合约查询回报"""
        if self.isRspSuccess(error):
            if data != None:
                event = Event(type=EVENT_QRYINSTRUMENT + self.gatewayName )
                event.dict['data'] = dict((name, getattr(data, name)) for name in dir(data) if not name.startswith('_'))
                event.dict['error'] = dict((name, getattr(error, name)) for name in dir(error) if not name.startswith('_'))
                event.dict['last'] = last
                self.gateway.eventEngine.put(event)
        else:
            logContent = u'交易错误回报，错误代码：' + unicode(error.ErrorID) + u',' + u'错误信息：' + error.ErrorMsg.decode('gbk')
            self.gateway.onLog(logContent, level = logging.DEBUG)
    
    #----------------------------------------------------------------------
    def OnRspQryDepthMarketData(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQrySettlementInfo(self, data, error, n, last):
        """查询结算信息回报"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQryTransferBank(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQryInvestorPositionDetail(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQryNotice(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQrySettlementInfoConfirm(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQryInvestorPositionCombineDetail(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQryCFMMCTradingAccountKey(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQryEWarrantOffset(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQryInvestorProductGroupMargin(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQryExchangeMarginRate(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQryExchangeMarginRateAdjust(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQryExchangeRate(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQrySecAgentACIDMap(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQryOptionInstrTradeCost(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQryOptionInstrCommRate(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQryExecOrder(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQryForQuote(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQryQuote(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQryTransferSerial(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQryAccountregister(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspError(self, error, n, last):
        """错误回报"""
        err = VtErrorData()
        err.gatewayName = self.gatewayName
        err.errorID = error.ErrorID
        err.errorMsg = error.ErrorMsg.decode('gbk')
        self.gateway.onError(err)
    
    #----------------------------------------------------------------------
    def OnRtnInstrumentStatus(self, data):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRtnTradingNotice(self, data):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRtnErrorConditionalOrder(self, data):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRtnExecOrder(self, data):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnErrRtnExecOrderInsert(self, data, error):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnErrRtnExecOrderAction(self, data, error):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnErrRtnForQuoteInsert(self, data, error):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRtnQuote(self, data):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnErrRtnQuoteInsert(self, data, error):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnErrRtnQuoteAction(self, data, error):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRtnForQuoteRsp(self, data):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQryContractBank(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQryParkedOrder(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQryParkedOrderAction(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQryTradingNotice(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQryBrokerTradingParams(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQryBrokerTradingAlgos(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRtnFromBankToFutureByBank(self, data):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRtnFromFutureToBankByBank(self, data):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRtnRepealFromBankToFutureByBank(self, data):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRtnRepealFromFutureToBankByBank(self, data):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRtnFromBankToFutureByFuture(self, data):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRtnFromFutureToBankByFuture(self, data):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRtnRepealFromBankToFutureByFutureManual(self, data):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRtnRepealFromFutureToBankByFutureManual(self, data):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRtnQueryBankBalanceByFuture(self, data):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnErrRtnBankToFutureByFuture(self, data, error):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnErrRtnFutureToBankByFuture(self, data, error):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnErrRtnRepealBankToFutureByFutureManual(self, data, error):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnErrRtnRepealFutureToBankByFutureManual(self, data, error):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnErrRtnQueryBankBalanceByFuture(self, data, error):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRtnRepealFromBankToFutureByFuture(self, data):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRtnRepealFromFutureToBankByFuture(self, data):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspFromBankToFutureByFuture(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspFromFutureToBankByFuture(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRspQueryBankAccountMoneyByFuture(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRtnOpenAccountByBank(self, data):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRtnCancelAccountByBank(self, data):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def OnRtnChangeAccountByBank(self, data):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def connect(self, userID, password, brokerID, address):
        """初始化连接"""
        self.userID = userID                # 账号
        self.password = password            # 密码
        self.brokerID = brokerID            # 经纪商代码
        self.address = address              # 服务器地址
        
        # 如果尚未建立服务器连接，则进行连接
        if not self.connectionStatus:
            # 创建C++环境中的API对象，这里传入的参数是需要用来保存.con文件的文件夹路径
            path = self.gateway.file_prefix + 'tmp' + os.path.sep
            if not os.path.exists(path):
                os.makedirs(path)
            self.Create(str(path))

            # THOST_TERT_RESTART = 0, THOST_TERT_RESUME = 1, THOST_TERT_QUICK = 2
            self.SubscribePublicTopic(self.gateway.td_conn_mode)
            self.SubscribePrivateTopic(self.gateway.td_conn_mode)
            # 注册服务器地址
            self.RegisterFront(self.address)
            
            # 初始化连接，成功会调用onFrontConnected
            self.Init()
            
        # 若已经连接但尚未登录，则进行登录
        else:
            if not self.loginStatus:
                self.login()    
    
    #----------------------------------------------------------------------
    def login(self):
        """连接服务器"""
        # 如果填入了用户名密码等，则登录
        if self.userID and self.password and self.brokerID:
            req = {}
            req['UserID'] = self.userID
            req['Password'] = self.password
            req['BrokerID'] = self.brokerID
            req_data = self.ApiStruct.ReqUserLogin( **req )
            self.reqID += 1
            self.ReqUserLogin(req_data, self.reqID)   
        
    #----------------------------------------------------------------------
    def qryOrder(self):
        self.reqID += 1
        req = {}
        req['BrokerID'] = self.brokerID
        req['InvestorID'] = self.userID
        req_data = self.ApiStruct.QryOrder(**req)
        self.ReqQryOrder(req_data, self.reqID)

    #----------------------------------------------------------------------
    def qryTrade(self):
        self.reqID += 1
        req = {}
        req['BrokerID'] = self.brokerID
        req['InvestorID'] = self.userID
        req_data = self.ApiStruct.QryTrade(**req)
        self.ReqQryTrade(req_data, self.reqID)

    #----------------------------------------------------------------------
    def qryAccount(self):
        """查询账户"""
        req = {}
        self.reqID += 1
        req['BrokerID'] = self.brokerID
        req['InvestorID'] = self.userID
        req_data = self.ApiStruct.QryTradingAccount(**req)
        self.ReqQryTradingAccount(req_data, self.reqID)
        
    #----------------------------------------------------------------------
    def qryPosition(self):
        """查询持仓"""
        self.reqID += 1
        req = {}
        req['BrokerID'] = self.brokerID
        req['InvestorID'] = self.userID
        req_data = self.ApiStruct.QryInvestorPosition(**req)
        self.ReqQryInvestorPosition(req_data, self.reqID)
    
    #----------------------------------------------------------------------
    def qryInstrument(self):
        self.reqID += 1
        req = {}
        req_data = self.ApiStruct.QryInstrument(**req)
        self.ReqQryInstrument(req_data, self.reqID)

    #----------------------------------------------------------------------
    def sendOrder(self, iorder):
        """发单"""
        self.reqID += 1
        self.orderRef = max(self.orderRef, iorder.local_id)
        req = {}
        req['InstrumentID'] = str(iorder.instrument.name)
        req['LimitPrice'] = iorder.limit_price
        req['VolumeTotalOriginal'] = iorder.volume
        
        # 下面如果由于传入的类型本接口不支持，则会返回空字符串
        req['Direction'] = iorder.direction
        req['CombOffsetFlag'] = iorder.action_type
        req['OrderPriceType'] = iorder.price_type
        req['TimeCondition'] = defineDict['THOST_FTDC_TC_GFD']               # 今日有效
        req['VolumeCondition'] = defineDict['THOST_FTDC_VC_AV']              # 任意成交量
        if iorder.price_type == OPT_FAK_ORDER:
            req['OrderPriceType'] = defineDict["THOST_FTDC_OPT_LimitPrice"]
            req['TimeCondition'] = defineDict['THOST_FTDC_TC_IOC']
            req['VolumeCondition'] = defineDict['THOST_FTDC_VC_AV']
        elif iorder.price_type == OPT_FOK_ORDER:
            req['OrderPriceType'] = defineDict["THOST_FTDC_OPT_LimitPrice"]
            req['TimeCondition'] = defineDict['THOST_FTDC_TC_IOC']
            req['VolumeCondition'] = defineDict['THOST_FTDC_VC_CV']
        req['OrderRef'] = str(iorder.local_id)
        req['InvestorID'] = self.userID
        req['UserID'] = self.userID
        req['BrokerID'] = self.brokerID
        req['CombHedgeFlag'] = defineDict['THOST_FTDC_HF_Speculation']       # 投机单
        req['ContingentCondition'] = defineDict['THOST_FTDC_CC_Immediately'] # 立即发单
        req['ForceCloseReason'] = defineDict['THOST_FTDC_FCC_NotForceClose'] # 非强平
        req['IsAutoSuspend'] = 0                                             # 非自动挂起
        req['MinVolume'] = 1                                                 # 最小成交量为1
        req_data = self.ApiStruct.InputOrder(**req)
        self.ReqOrderInsert(req_data, self.reqID)
    
    #----------------------------------------------------------------------
    def cancelOrder(self, iorder):
        """撤单"""
        inst = iorder.instrument
        self.reqID += 1
        req = {}
        req['InstrumentID'] = iorder.instrument.name
        req['ExchangeID'] = inst.exchange
        req['ActionFlag'] = defineDict['THOST_FTDC_AF_Delete']
        req['BrokerID'] = self.brokerID
        req['InvestorID'] = self.userID

        if len(iorder.sys_id) >0:
            req['OrderSysID'] = iorder.sys_id
        else:
            req['OrderRef'] = str(iorder.local_id)
            req['FrontID'] = self.frontID
            req['SessionID'] = self.sessionID
        req_data = self.ApiStruct.InputOrderAction(**req)
        self.ReqOrderAction(req_data, self.reqID)
        
    #----------------------------------------------------------------------
    def close(self):
        """关闭"""
        pass
        
if __name__ == '__main__':
    pass
