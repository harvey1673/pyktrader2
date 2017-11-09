from cmq_rpc import RpcServer, RpcClient, DataPacker
from gui_misc import field2variable, variable2field
import base
import logging
import datetime
import sys
import time
import json

class ProxyRpcServer(RpcServer):
    def __init__(self, rep_address, pub_address, config = {}, tday = datetime.date.today()):
        super(ProxyRpcServer, self).__init__(rep_address, pub_address)
        self.scur_day = tday
        self.name = config.get('name', 'test_agent')
        agent_class = config.get('agent_class', 'agent.Agent')
        cls_str = agent_class.split('.')
        agent_cls = getattr(__import__(str(cls_str[0])), str(cls_str[1]))
        self.agent = agent_cls(config = config, tday = tday)
        self.restart()
        self.register(self.restart)
        self.register(self.get_agent_params)
        self.register(self.set_agent_params)
        self.register(self.set_gateway_params)
        self.register(self.get_strat_params)
        self.register(self.set_strat_params)
        self.register(self.run_agent_func)
        self.register(self.run_gateway_func)
        self.register(self.run_strat_func)
        self.register(self.get_hist_data)
        self.register(self.exit_agent)

    def restart(self):
        if self.agent != None:
            self.scur_day = self.agent.scur_day
        self.agent.restart()

    def get_agent_params(self, fields):
        res = {}
        for f in fields:
            field_list = f.split('.')
            field = field_list[0]
            if field not in res:
                res[field] = {}
            if field == 'Positions':
                positions = {}
                for gway in self.agent.gateways:
                    gateway = self.agent.gateways[gway]
                    positions[gway] = {}
                for inst in gateway.positions:
                    pos = gateway.positions[inst]
                    positions[gway][inst] = {'currlong' : pos.curr_pos.long,
                                       'currshort': pos.curr_pos.short,
                                       'locklong' : pos.locked_pos.long,
                                       'lockshort': pos.locked_pos.short,
                                       'ydaylong':  pos.pos_yday.long,
                                       'ydayshort': pos.pos_yday.short}
                res[field] = positions
            elif field == 'Risk':
                risk_list = field_list[1:]
                sum_risk, risk_dict = self.agent.risk_by_strats(risk_list)
                res[field] = {'total': sum_risk, 'strats': risk_dict }
            elif field == 'Account':
                gateway = self.agent.gateways[field_list[1]]
                res[field][gateway.gatewayName] = dict([(variable2field(var), gateway.account_info[var]) for var in gateway.account_info])
            elif field ==' Orderstats':
                gateway = self.agent.gateways[field_list[1]]
                res[field][gateway.gatewayName] = dict([(variable2field(var), gateway.order_stats[var]) for var in gateway.order_stats])
            elif field == 'Orders':
                order_list = []
                gateway = self.agent.gateways[field_list[1]]
                for o in gateway.id2order.values():
                    inst = o.position.instrument.name
                    order_list.append([o.order_ref, o.sys_id, inst, o.diretion, o.volume, o.filled_volume,  o.limit_price, o.status])
                res[field][gateway.gatewayName] = order_list
            elif field == 'Trades':
                trade_list = []
                for etrade in self.agent.etrades:
                    insts = ' '.join(etrade.instIDs)
                    volumes = ' '.join([str(i) for i in etrade.volumes])
                    filled_vol = ' '.join([str(i) for i in etrade.filled_vol])
                    filled_price = ' '.join([str(i) for i in etrade.filled_price])
                    trade_list.append([etrade.id, insts, volumes, filled_vol, filled_price, etrade.limit_price, etrade.valid_time,
                                  etrade.strategy, etrade.book, etrade.status])
                res[field] = trade_list
            elif field == 'Insts':
                if len(field_list) > 1:
                    insts = field_list[1:]
                else:
                    insts = self.agent.instruments.keys()
                inst_dict = {}
                for inst in insts:
                    inst_obj = self.agent.instruments[inst]
                    inst_dict[inst] = {'Name': inst, 'Price': inst_obj.price, 'MidPrice': inst_obj.mid_price,
                                 'BidPrice': inst_obj.bid_price1, 'BidVol': inst_obj.bid_vol1,
                                 'AskPrice': inst_obj.ask_price1, 'AskVol': inst_obj.ask_vol1,
                                 'PrevClose': inst_obj.prev_close, 'MarginRate': inst_obj.marginrate,
                                 'Updated': inst_obj.last_update, 'Traded': inst_obj.last_traded,
                                 'UpLimit': inst_obj.up_limit, 'DownLimit': inst_obj.down_limit,
                                 'Volume': inst_obj.volume, 'OI': inst_obj.open_interest }
                    if 'Option' in inst_obj.__class__.__name__:
                        inst_dict[inst]['PV'] = inst_obj.pv
                        inst_dict[inst]['Delta'] = inst_obj.delta
                        inst_dict[inst]['Gamma'] = inst_obj.gamma
                        inst_dict[inst]['Vega']  = inst_obj.vega
                        inst_dict[inst]['Theta'] = inst_obj.theta
                        inst_dict[inst]['Otype'] = inst_obj.otype
                        inst_dict[inst]['Strike'] = inst_obj.strike
                        inst_dict[inst]['Underlying'] = inst_obj.underlying
                        inst_dict[inst]['RiskPrice'] = inst_obj.risk_price
                        inst_dict[inst]['RiskUpdated'] = inst_obj.risk_updated
                res[field] = inst_dict
            elif field == 'Volgrids':
                prod = field_list[1]
                vg_param = {}
                if prod in self.agent.volgrids:
                    vg = self.agent.volgrids[prod]
                    for expiry in vg.volnode:
                        vg_param[expiry] = {}
                        vg_param[expiry]['Fwd'] = vg.fwd[expiry]
                        vg_param[expiry]['Updated'] = vg.last_update[expiry]
                        vg_param[expiry]['T2expiry'] = vg.t2expiry[expiry]
                        vg_param[expiry]['Under'] = vg.underlier[expiry]
                        vg_param[expiry]['Df'] = vg.df[expiry]
                        vol_param = vg.volparam[expiry]
                        vg_param[expiry]['Atm'] = vol_param[0]
                        vg_param[expiry]['V90'] = vol_param[1]
                        vg_param[expiry]['V75'] = vol_param[2]
                        vg_param[expiry]['V25'] = vol_param[3]
                        vg_param[expiry]['V10'] = vol_param[4]
                res[field] = {prod: vg_param}
            else:
                var = field2variable(field)
                res[field] = getattr(self.agent, var)
        return res

    def set_agent_params(self, params):
        for field in params:
            var = field2variable(field)
            value = params[field]
            setattr(self.agent, var, value)

    def set_gateway_params(self, gway, params):
        gateway = self.agent.gateways[gway]
        for field in params:
            var = field2variable(field)
            value = params[field]
            setattr(gateway, var, value)

    def get_strat_params(self, strat_name, fields):
        params = {}
        strat = self.agent.strategies[strat_name]
        for field in fields:
            var = field2variable(field)
            params[field] = getattr(strat, var)
        return params

    def set_strat_params(self, strat_name, params):
        strat = self.agent.strategies[strat_name]
        for field in params:
            var = field2variable(field)
            value = params[field]
            setattr(strat, var, value)

    def run_strat_func(self, strat_name, func_name):
        strat = self.agent.strategies[strat_name]
        getattr(strat, func_name)()

    def run_agent_func(self, func_name, params):
        return getattr(self.agent, func_name)(*params)

    def run_gateway_func(self, gway, func_name, params):
        gateway = self.agent.gateways[gway]
        return getattr(gateway, func_name)(*params)

    def get_hist_data(self, inst, freq, nlen = 20):
        data = []
        if freq in ['D', 'd']:
            if inst in self.agent.day_data:
                data = self.agent.day_data[inst].data[-nlen:]
        elif ('m' in freq) or ('M' in freq):
            f = int(freq[:-1])
            if (inst in self.agent.min_data) and (f in self.agent.min_data[inst]):
                data = self.agent.min_data[inst][f].data[-nlen:]
        return data

    def exit_agent(self):
        if self.agent != None:
            self.agent.exit()

def run_proxy_server(config_file, tday):
    with open(config_file, 'r') as infile:
        config = json.load(infile)
    name = config.get('name', 'test_agent')
    base.config_logging(name + "/" + name + ".log", level=logging.DEBUG,
                        format='%(name)s:%(funcName)s:%(lineno)d:%(asctime)s %(levelname)s %(message)s',
                        to_console=True,
                        console_level=logging.INFO)
    scur_day = datetime.datetime.strptime(tday, '%Y%m%d').date()
    rep_address = config.get('rep_address', 'tcp://*:10010')
    pub_address = config.get('pub_address', 'tcp://*:10020')
    proxy_app = ProxyRpcServer(rep_address, pub_address, config, scur_day)
    proxy_app.start()
    try:
        while 1:
            time.sleep(1)
    except KeyboardInterrupt:
        proxy_app.exit_agent()

def run_proxy_client(config_file, tday):
    pass

if __name__=="__main__":
    args = sys.argv[1:]
    app_name = args[0]
    params = (args[1], args[2],)
    getattr(sys.modules[__name__], app_name)(*params)