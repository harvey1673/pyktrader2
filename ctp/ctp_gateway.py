# -*- coding: utf-8 -*-

'''
vn.ctp的gateway接入
考虑到现阶段大部分CTP中的ExchangeID字段返回的都是空值
vtSymbol直接使用symbol
'''
import os
import json
from base import *
from misc import *
from gateway import *
from ctpDataType import *
from vtConstant import *
import logging
import datetime
import position
import order

# 以下为一些VT类型和CTP类型的映射字典
# 价格类型映射
priceTypeMap = {}
priceTypeMap[PRICETYPE_LIMITPRICE] = defineDict["THOST_FTDC_OPT_LimitPrice"]
priceTypeMap[PRICETYPE_MARKETPRICE] = defineDict["THOST_FTDC_OPT_AnyPrice"]
priceTypeMapReverse = {v: k for k, v in priceTypeMap.items()}

# 方向类型映射
directionMap = {}
directionMap[DIRECTION_LONG] = defineDict['THOST_FTDC_D_Buy']
directionMap[DIRECTION_SHORT] = defineDict['THOST_FTDC_D_Sell']
directionMapReverse = {v: k for k, v in directionMap.items()}

# 开平类型映射
offsetMap = {}
offsetMap[OFFSET_OPEN] = defineDict['THOST_FTDC_OF_Open']
offsetMap[OFFSET_CLOSE] = defineDict['THOST_FTDC_OF_Close']
offsetMap[OFFSET_CLOSETODAY] = defineDict['THOST_FTDC_OF_CloseToday']
offsetMap[OFFSET_CLOSEYESTERDAY] = defineDict['THOST_FTDC_OF_CloseYesterday']
offsetMapReverse = {v:k for k,v in offsetMap.items()}

# 交易所类型映射
exchangeMap = {}
#exchangeMap[EXCHANGE_CFFEX] = defineDict['THOST_FTDC_EIDT_CFFEX']
#exchangeMap[EXCHANGE_SHFE] = defineDict['THOST_FTDC_EIDT_SHFE']
#exchangeMap[EXCHANGE_CZCE] = defineDict['THOST_FTDC_EIDT_CZCE']
#exchangeMap[EXCHANGE_DCE] = defineDict['THOST_FTDC_EIDT_DCE']
exchangeMap[EXCHANGE_CFFEX] = 'CFFEX'
exchangeMap[EXCHANGE_SHFE] = 'SHFE'
exchangeMap[EXCHANGE_CZCE] = 'CZCE'
exchangeMap[EXCHANGE_DCE] = 'DCE'
exchangeMap[EXCHANGE_DCE] = 'INE'
exchangeMap[EXCHANGE_UNKNOWN] = ''
exchangeMapReverse = {v:k for k,v in exchangeMap.items()}

# 持仓类型映射
posiDirectionMap = {}
posiDirectionMap[DIRECTION_NET] = defineDict["THOST_FTDC_PD_Net"]
posiDirectionMap[DIRECTION_LONG] = defineDict["THOST_FTDC_PD_Long"]
posiDirectionMap[DIRECTION_SHORT] = defineDict["THOST_FTDC_PD_Short"]
posiDirectionMapReverse = {v:k for k,v in posiDirectionMap.items()}

TERT_RESTART = 0 #从本交易日开始重传
TERT_RESUME = 1 #从上次收到的续传
TERT_QUICK = 2 #只传送登录后的流内容

class CtpGateway(GrossGateway):
    """CTP接口"""

    #----------------------------------------------------------------------
    def __init__(self, agent, gatewayName='CTP', md_api = 'ctp.vnctp_gateway.VnctpMdApi', td_api = 'ctp.vnctp_gateway.VnctpTdApi'):
        """Constructor"""
        super(CtpGateway, self).__init__(agent, gatewayName)

        md_str_split = md_api.split('.')
        if len(md_str_split) > 1:
            mod_str = '.'.join(md_str_split[:-1])
            md_module = __import__(mod_str, fromlist = [md_str_split[-1]])
            mdApi_cls = getattr(md_module, md_str_split[-1])
        else:
            mdApi_cls = getattr(md_str_split[0])
        self.mdApi = mdApi_cls(self)
        td_str_split = td_api.split('.')
        if len(td_str_split) > 1:
            mod_str = '.'.join(td_str_split[:-1])
            td_module = __import__(mod_str, fromlist = [td_str_split[-1]])
            tdApi_cls = getattr(td_module, td_str_split[-1])
        else:
            tdApi_cls = getattr(td_str_split[0])        
        self.tdApi = tdApi_cls(self)
        self.mdConnected = False        # 行情API连接状态，登录完成后为True
        self.tdConnected = False        # 交易API连接状态
        self.auto_db_update = False
        self.qryEnabled = True         # 是否要启动循环查询
        self.qry_count = 0           # 查询触发倒计时
        self.qry_trigger = 2         # 查询触发点
        self.qry_commands = []
        self.qry_instruments = {}
        self.system_orders = []
        self.md_data_buffer = 0
        self.td_conn_mode = TERT_QUICK
        self.intraday_close_ratio = {}
        self.product_info = 'Zeno'
        
    #----------------------------------------------------------------------
    def get_pos_class(self, inst):
        ratio = 1
        pos_args = {}
        if inst.name in self.intraday_close_ratio:
            pos_args['intraday_close_ratio'] = self.intraday_close_ratio[inst.name]
        if inst.exchange == 'SHFE':
            pos_cls = position.SHFEPosition
        else:
            pos_cls = position.GrossPosition
        return (pos_cls, pos_args)

    def connect(self):
        """连接"""
        # 载入json文件
        fileName = self.file_prefix + 'connect.json'
        try:
            f = file(fileName)
        except IOError:
            logContent = u'读取连接配置出错，请检查'
            self.onLog(logContent, level = logging.WARNING)
            return

        # 解析json文件
        setting = json.load(f)
        try:
            userID = str(setting['userID'])
            password = str(setting['password'])
            brokerID = str(setting['brokerID'])
            tdAddress = str(setting['tdAddress'])
            mdAddress = str(setting['mdAddress'])
            self.intraday_close_ratio = setting.get('intraday_close_ratio', {})
            self.product_info = setting.get('product_info', 'Zeno')
        except KeyError:
            logContent = u'连接配置缺少字段，请检查'
            self.onLog(logContent, level = logging.WARNING)
            return            
        
        # 创建行情和交易接口对象
        self.mdApi.connect(userID, password, brokerID, mdAddress)
        self.mdConnected = False

        self.tdApi.connect(userID, password, brokerID, tdAddress)
        self.tdConnected = False
    
    #----------------------------------------------------------------------
    def subscribe(self, subscribeReq):
        """订阅行情"""
        instID = subscribeReq.symbol
        self.add_instrument(instID)
        self.mdApi.subscribe(instID)

    #----------------------------------------------------------------------
    def sendOrder(self, iorder):
        """发单"""
        inst = self.agent.instruments[iorder.instrument]
        if not self.order_stats[inst.name]['status']:
            iorder.on_cancel()
            if iorder.trade_ref > 0:
                event = Event(type=EVENT_ETRADEUPDATE)
                event.dict['trade_ref'] = iorder.trade_ref
                self.eventEngine.put(event)
            logContent = 'Canceling order = %s for instrument = %s is disabled for trading due to position control' % (iorder.local_id, inst.name)
            self.onLog( logContent, level = logging.WARNING)
            return
        # 上期所不支持市价单
        if (iorder.price_type == OPT_MARKET_ORDER):
            if (inst.exchange == 'SHFE' or inst.exchange == 'CFFEX'):
                iorder.price_type = OPT_LIMIT_ORDER
                if iorder.direction == ORDER_BUY:
                    iorder.limit_price = inst.up_limit
                else:
                    iorder.limit_price = inst.down_limit
                self.onLog('sending limiting local_id=%s inst=%s for SHFE and CFFEX, change to limit order' % (iorder.local_id, inst.name), level = logging.DEBUG)
            else:
                iorder.limit_price = 0.0
        iorder.status = order.OrderStatus.Sent
        self.tdApi.sendOrder(iorder)
        self.order_stats[inst.name]['submit'] += 1
        self.order_stats['total_submit'] += 1
        if self.order_stats[inst.name]['submit'] >= self.order_constraints['submit_limit']:
            self.order_stats[inst.name]['status'] = False
        if self.order_stats['total_submit'] >= self.order_constraints['total_submit']:
            for instID in self.order_stats:
                self.order_stats[instID]['status'] = False
        return

    #----------------------------------------------------------------------
    def cancelOrder(self, iorder):
        """撤单"""
        self.tdApi.cancelOrder(iorder)        
        self.order_stats[iorder.instrument]['cancel'] += 1
        self.order_stats['total_cancel'] += 1
        self.onLog( u'A_CC:取消命令: OrderRef=%s, OrderSysID=%s, instID=%s, volume=%s, filled=%s, cancelled=%s' % (iorder.local_id, \
                            iorder.sys_id, iorder.instrument, iorder.volume, iorder.filled_volume, iorder.cancelled_volume), level = logging.DEBUG)             
        
    #----------------------------------------------------------------------
    def qryAccount(self):
        """查询账户资金"""
        self.tdApi.qryAccount()
        
    #----------------------------------------------------------------------
    def qryPosition(self):
        """查询持仓"""
        self.tdApi.qryPosition()

    def qryTrade(self):
        """查询账户资金"""
        self.tdApi.qryTrade()

    #----------------------------------------------------------------------
    def qryOrder(self):
        """查询持仓"""
        self.tdApi.qryOrder()

    #----------------------------------------------------------------------
    def close(self):
        """关闭"""
        if self.mdConnected:
            self.mdApi.close()
        if self.tdConnected:
            self.tdApi.close()
    
    #----------------------------------------------------------------------
    def query(self, event):
        """注册到事件处理引擎上的查询函数"""
        if self.qryEnabled:
            self.qry_count += 1
            if self.qry_count > self.qry_trigger:
                self.qryCount = 0
                if len(self.qry_commands)>0:
                    self.qry_commands[0]()
                    del self.qry_commands[0]
    
    #----------------------------------------------------------------------
    def setQryEnabled(self, qryEnabled):
        """设置是否要启动循环查询"""
        self.qryEnabled = qryEnabled

    def setAutoDbUpdated(self, db_update):
        self.auto_db_update = db_update

    def register_event_handler(self):
        self.eventEngine.register(EVENT_MARKETDATA+self.gatewayName, self.rsp_market_data)
        self.eventEngine.register(EVENT_QRYACCOUNT+self.gatewayName, self.rsp_qry_account)
        self.eventEngine.register(EVENT_QRYPOSITION+self.gatewayName, self.rsp_qry_position)
        self.eventEngine.register(EVENT_QRYTRADE+self.gatewayName, self.rsp_qry_order)
        self.eventEngine.register(EVENT_QRYORDER+self.gatewayName, self.rsp_qry_order)
        self.eventEngine.register(EVENT_QRYINVESTOR+self.gatewayName, self.rsp_qry_investor)
        self.eventEngine.register(EVENT_QRYINSTRUMENT+self.gatewayName, self.rsp_qry_instrument)
        self.eventEngine.register(EVENT_ERRORDERINSERT+self.gatewayName, self.err_order_insert)
        self.eventEngine.register(EVENT_ERRORDERCANCEL+self.gatewayName, self.err_order_action)
        self.eventEngine.register(EVENT_RTNTRADE+self.gatewayName, self.rtn_trade)
        self.eventEngine.register(EVENT_RTNORDER+self.gatewayName, self.rtn_order)
        self.eventEngine.register(EVENT_TIMER, self.query)
        self.eventEngine.register(EVENT_TDLOGIN+self.gatewayName, self.rsp_td_login)

    def rsp_td_login(self, event):
        self.qry_commands.append(self.qryAccount)
        self.qry_commands.append(self.qryPosition)
        self.qry_commands.append(self.qryOrder)
        self.qry_commands.append(self.qryTrade)

    def onOrder(self, order):
        pass

    def onTrade(self, trade):
        pass

    def rtn_order(self, event):
        data = event.dict['data']
        newref = data['OrderRef']
        if not newref.isdigit():
            return
        local_id = int(newref)
        self.tdApi.orderRef = max(self.tdApi.orderRef, local_id)
        if (local_id not in self.id2order):
            logContent = 'receive order update from other agents, InstID=%s, OrderRef=%s' % (data['InstrumentID'], local_id)
            self.onLog(logContent, level = logging.WARNING)
            return
        myorder = self.id2order[local_id]
        # only update sysID,
        status = myorder.on_order(sys_id = data['OrderSysID'], price = data['LimitPrice'], volume = 0)
        if data['OrderStatus'] in [ '5', '2']:
            myorder.on_cancel()
            status = True
        if myorder.trade_ref <= 0:
            order = VtOrderData()
            order.gatewayName = self.gatewayName
            # 保存代码和报单号
            order.symbol = data['InstrumentID']
            order.exchange = exchangeMapReverse[data['ExchangeID']]
            order.instID = order.symbol #'.'.join([order.symbol, order.exchange])
            order.orderID = local_id
            order.orderSysID = data['OrderSysID']
            # 方向
            if data['Direction'] == '0':
                order.direction = DIRECTION_LONG
            elif data['Direction'] == '1':
                order.direction = DIRECTION_SHORT
            else:
                order.direction = DIRECTION_UNKNOWN
            # 开平
            if data['CombOffsetFlag'] == '0':
                order.offset = OFFSET_OPEN
            elif data['CombOffsetFlag'] == '1':
                order.offset = OFFSET_CLOSE
            else:
                order.offset = OFFSET_UNKNOWN
            # 状态
            if data['OrderStatus'] == '0':
                order.status = STATUS_ALLTRADED
            elif data['OrderStatus'] == '1':
                order.status = STATUS_PARTTRADED
            elif data['OrderStatus'] == '3':
                order.status = STATUS_NOTTRADED
            elif data['OrderStatus'] == '5':
                order.status = STATUS_CANCELLED
            else:
                order.status = STATUS_UNKNOWN
            # 价格、报单量等数值
            order.price = data['LimitPrice']
            order.totalVolume = data['VolumeTotalOriginal']
            order.tradedVolume = data['VolumeTraded']
            order.orderTime = data['InsertTime']
            order.cancelTime = data['CancelTime']
            order.frontID = data['FrontID']
            order.sessionID = data['SessionID']
            order.order_ref = myorder.order_ref
            self.onOrder(order)
            return
        else:
            if status:
                event = Event(type=EVENT_ETRADEUPDATE)
                event.dict['trade_ref'] = myorder.trade_ref
                self.eventEngine.put(event)

    def rtn_trade(self, event):
        data = event.dict['data']
        newref = data['OrderRef']
        if not newref.isdigit():
            return
        local_id = int(newref)
        if local_id in self.id2order:
            myorder = self.id2order[local_id]
            myorder.on_trade(price = data['Price'], volume=data['Volume'], trade_id = data['TradeID'])
            if myorder.trade_ref <= 0:
                trade = VtTradeData()
                trade.gatewayName = self.gatewayName
                # 保存代码和报单号
                trade.symbol = data['InstrumentID']
                trade.exchange = exchangeMapReverse[data['ExchangeID']]
                trade.vtSymbol = trade.symbol #'.'.join([trade.symbol, trade.exchange])
                trade.tradeID = data['TradeID']
                trade.vtTradeID = '.'.join([self.gatewayName, trade.tradeID])
                trade.orderID = local_id
                trade.order_ref = myorder.order_ref
                # 方向
                trade.direction = directionMapReverse.get(data['Direction'], '')
                # 开平
                trade.offset = offsetMapReverse.get(data['OffsetFlag'], '')
                # 价格、报单量等数值
                trade.price = data['Price']
                trade.volume = data['Volume']
                trade.tradeTime = data['TradeTime']
                # 推送
                self.onTrade(trade)
            else:
                event = Event(type=EVENT_ETRADEUPDATE)
                event.dict['trade_ref'] = myorder.trade_ref
                self.eventEngine.put(event)
        else:
            logContent = 'receive trade update from other agents, InstID=%s, OrderRef=%s' % (data['InstrumentID'], local_id)
            self.onLog(logContent, level = logging.WARNING)

    def rsp_market_data(self, event):
        data = event.dict['data']
        if self.mdApi.trading_day == 0:
            self.mdApi.trading_day = int(data['TradingDay'])
        timestr = str(self.mdApi.trading_day) + ' '+ str(data['UpdateTime']) + ' ' + str(data['UpdateMillisec']) + '000'
        try:
            timestamp = datetime.datetime.strptime(timestr, '%Y%m%d %H:%M:%S %f')
        except:
            logContent =  "Error to convert timestr = %s" % timestr
            self.onLog(logContent, level = logging.INFO)
            return
        tick_id = get_tick_id(timestamp)
        if data['ExchangeID'] == 'CZCE':
            if (len(data['TradingDay'])>0):
                if (self.trading_day > int(data['TradingDay'])) and (tick_id >= 600000):
                    rtn_error = BaseObject(errorMsg="tick data is wrong, %s" % data)
                    self.onError(rtn_error)
                    return
        tick = VtTickData()
        tick.gatewayName = self.gatewayName
        tick.symbol = data['InstrumentID']
        tick.instID = tick.symbol #'.'.join([tick.symbol, EXCHANGE_UNKNOWN])
        tick.exchange = exchangeMapReverse.get(data['ExchangeID'], u'未知')
        product = inst2product(tick.instID)
        hrs = trading_hours(product, tick.exchange)
        bad_tick = True
        for ptime in hrs:
            if (tick_id>=ptime[0]*1000-self.md_data_buffer) and (tick_id< ptime[1]*1000+self.md_data_buffer):
                bad_tick = False
                break
        if bad_tick:
            return
        tick.timestamp = timestamp
        tick.date = timestamp.date()
        tick.tick_id = tick_id
        tick.price = data['LastPrice']
        tick.volume = data['Volume']
        tick.openInterest = data['OpenInterest']
        # CTP只有一档行情
        tick.open = data['OpenPrice']
        tick.high = data['HighestPrice']
        tick.low = data['LowestPrice']
        tick.prev_close = data['PreClosePrice']
        tick.upLimit = data['UpperLimitPrice']
        tick.downLimit = data['LowerLimitPrice']
        tick.bidPrice1 = data['BidPrice1']
        tick.bidVol1 = data['BidVolume1']
        tick.askPrice1 = data['AskPrice1']
        tick.askVol1 = data['AskVolume1']
        # 通用事件
        event1 = Event(type=EVENT_TICK)
        event1.dict['data'] = tick
        self.eventEngine.put(event1)
        
        # 特定合约代码的事件
        event2 = Event(type=EVENT_TICK+tick.instID)
        event2.dict['data'] = tick
        self.eventEngine.put(event2)

    def rsp_qry_account(self, event):
        data = event.dict['data']
        self.qry_account['preBalance'] = data['PreBalance']
        self.qry_account['available'] = data['Available']
        self.qry_account['commission'] = data['Commission']
        self.qry_account['margin'] = data['CurrMargin']
        self.qry_account['closeProfit'] = data['CloseProfit']
        self.qry_account['positionProfit'] = data['PositionProfit']
        
        # 这里的balance和快期中的账户不确定是否一样，需要测试
        self.qry_account['balance'] = (data['PreBalance'] - data['PreCredit'] - data['PreMortgage'] +
                           data['Mortgage'] - data['Withdraw'] + data['Deposit'] +
                           data['CloseProfit'] + data['PositionProfit'] + data['CashIn'] -
                           data['Commission'])

    def rsp_qry_instrument(self, event):
        data = event.dict['data']
        last = event.dict['last']
        if data['ProductClass'] in ['1', '2'] and data['ExchangeID'] in ['CZCE', 'DCE', 'SHFE', 'CFFEX', 'INE',]:
            cont = {}
            cont['instID'] = data['InstrumentID']           
            margin_l = data['LongMarginRatio']
            if margin_l >= 1.0:
                margin_l = 0.0
            cont['margin_l'] = margin_l
            margin_s = data['ShortMarginRatio']
            if margin_s >= 1.0:
                margin_s = 0.0
            cont['margin_s'] = margin_s
            cont['start_date'] =data['OpenDate']
            cont['expiry'] = data['ExpireDate']
            cont['product_code'] = data['ProductID']
            #cont['exchange'] = data['ExchangeID']
            instID = cont['instID']
            self.qry_instruments[instID] = cont
        if last and self.auto_db_update:
            print "update contract table, new inst # = %s" % len(self.qry_instruments)
            for instID in self.qry_instruments:
                expiry = self.qry_instruments[instID]['expiry']
                try:
                    expiry_date = datetime.datetime.strptime(expiry, '%Y%m%d')
                    dbaccess.insert_cont_data(self.qry_instruments[instID])
                except:
                    print instID, expiry
                    continue
            #print "logout TD"
            #self.tdApi.logout()

    def rsp_qry_investor(self, event):
        pass

    def rsp_qry_position(self, event):
        pposition = event.dict['data']
        isLast = event.dict['last']
        instID = pposition['InstrumentID']
        if len(instID) ==0:
            return
        if (instID not in self.qry_pos):
            self.qry_pos[instID]   = {'tday': [0, 0], 'yday': [0, 0]}
        key = 'yday'
        idx = 1
        if pposition['PosiDirection'] == '2':
            if pposition['PositionDate'] == '1':
                key = 'tday'
                idx = 0
            else:
                idx = 0
        else:
            if pposition['PositionDate'] == '1':
                key = 'tday'
        self.qry_pos[instID][key][idx] = pposition['Position']
        self.qry_pos[instID]['yday'][idx] = pposition['YdPosition']
        if isLast:
            print self.qry_pos

    def rsp_qry_order(self, event):
        sorder = event.dict['data']
        isLast = event.dict['last']
        if (len(sorder['OrderRef']) == 0):
            return
        if not sorder['OrderRef'].isdigit():
            return
        local_id = int(sorder['OrderRef'])
        if (local_id in self.id2order):
            iorder = self.id2order[local_id]
            self.system_orders.append(local_id)
            if iorder.status not in [order.OrderStatus.Cancelled, order.OrderStatus.Done]:
                status = iorder.on_order(sys_id = sorder['OrderSysID'], price = sorder['LimitPrice'], volume = sorder['VolumeTraded'])
                if status:
                    event = Event(type=EVENT_ETRADEUPDATE)
                    event.dict['trade_ref'] = iorder.trade_ref
                    self.eventEngine.put(event)
                elif sorder['OrderStatus'] in ['3', '1', 'a']:
                    if iorder.status != order.OrderStatus.Sent:
                        iorder.status = order.OrderStatus.Sent                        
                        logContent = 'order status for OrderSysID = %s, Inst=%s is set to %s, but should be waiting in exchange queue' % (iorder.sys_id, iorder.instrument, iorder.status)
                        self.onLog(logContent, level = logging.INFO)
                elif sorder['OrderStatus'] in ['5', '2', '4']:
                    if iorder.status != order.OrderStatus.Cancelled:
                        iorder.on_cancel()
                        event = Event(type=EVENT_ETRADEUPDATE)
                        event.dict['trade_ref'] = iorder.trade_ref
                        self.eventEngine.put(event)
                        logContent = 'order status for OrderSysID = %s, Inst=%s is set to %s, but should be cancelled' % (iorder.sys_id, iorder.instrument.name, iorder.status)
                        self.onLog(logContent, level = logging.INFO)
        if isLast:
            for local_id in self.id2order:
                if (local_id not in self.system_orders):
                    iorder = self.id2order[local_id]
                    if iorder.status in order.Alive_Order_Status:
                        iorder.on_cancel()
                        event = Event(type=EVENT_ETRADEUPDATE)
                        event.dict['trade_ref'] = iorder.trade_ref
                        self.eventEngine.put(event)
                        logContent = 'order_ref=%s (Inst=%s,status=%s)is canncelled by qryOrder' % (local_id, iorder.instrument, iorder.status)
                        self.onLog(logContent, level=logging.WARNING)
            self.system_orders = []

    def err_order_insert(self, event):
        '''
            ctp/交易所下单错误回报，不区分ctp和交易所正常情况下不应当出现
        '''
        porder = event.dict['data']
        error = event.dict['error']
        if not porder['OrderRef'].isdigit():
            return
        local_id = int(porder['OrderRef'])
        inst = porder['InstrumentID']
        if local_id in self.id2order:
            myorder = self.id2order[local_id]
            inst = myorder.instrument
            myorder.on_cancel()
            event = Event(type=EVENT_ETRADEUPDATE)
            event.dict['trade_ref'] = myorder.trade_ref
            self.eventEngine.put(event)
        logContent = 'OrderInsert is not accepted by CTP, local_id=%s, instrument=%s. ' % (local_id, inst)
        if inst not in self.order_stats:
            self.order_stats[inst] = {'submit': 0, 'cancel':0, 'failure': 0, 'status': True }
        self.order_stats[inst]['failure'] += 1
        #self.order_stats['total_failure'] += 1
        if self.order_stats[inst]['failure'] >= self.order_constraints['failure_limit']:
            self.order_stats[inst]['status'] = False
            logContent += 'Failed order reaches the limit, disable instrument = %s' % inst
        self.onLog(logContent, level = logging.WARNING)

    def err_order_action(self, event):
        '''
            ctp/交易所撤单错误回报，不区分ctp和交易所必须处理，如果已成交，撤单后必然到达这个位置
        '''
        porder = event.dict['data']
        error = event.dict['error']
        inst = porder['InstrumentID']        
        if porder['OrderRef'].isdigit():
            local_id = int(porder['OrderRef'])
            myorder = self.id2order[local_id]
            inst = myorder.instrument
            if int(error['ErrorID']) in [25,26] and myorder.status not in [order.OrderStatus.Cancelled, order.OrderStatus.Done]:
                #myorder.on_cancel()
                #event = Event(type=EVENT_ETRADEUPDATE)
                #event.dict['trade_ref'] = myorder.trade_ref
                #self.eventEngine.put(event)
                self.qry_commands.append(self.tdApi.qryOrder)
        else:
            self.qry_commands.append(self.tdApi.qryOrder)
        logContent = 'Order Cancel is wrong, local_id=%s, instrument=%s. ' % (porder['OrderRef'], inst)
        if inst not in self.order_stats:
            self.order_stats[inst] = {'submit': 0, 'cancel':0, 'failure': 0, 'status': True }
        self.order_stats[inst]['failure'] += 1
        #self.order_stats['total_failure'] += 1
        if self.order_stats[inst]['failure'] >= self.order_constraints['failure_limit']:
            self.order_stats[inst]['status'] = False
            logContent += 'Failed order reaches the limit, disable instrument = %s' % inst
        self.onLog(logContent, level = logging.WARNING)


if __name__ == '__main__':
    pass
