from agent import *

class SaveAgent(Agent):
    def init_init(self):
        self.save_flag = True
        self.live_trading = False
        #self.prepare_data_env(mid_day = True)
        for key in self.gateways:
            gateway = self.gateways[key]
            gway_class = type(gateway).__name__
            if 'Ctp' in gway_class:
                self.type2gateway['CTP'] = gateway
            elif 'Lts' in gway_class:
                self.type2gateway['LTS'] = gateway
            elif 'Ib' in gway_class:
                self.type2gateway['IB'] = gateway
            elif 'Ksgold' in gway_class:
                self.type2gateway['KSGOLD'] = gateway
            elif 'Ksotp' in gway_class:
                self.type2gateway['KSOTP'] = gateway
            elif 'Femas' in gway_class:
                self.type2gateway['FEMAS'] = gateway
        self.register_event_handler()

    def restart(self):
        self.eventEngine.start()
        for gway in self.gateways:
            gateway = self.gateways[gway]
            gateway.connect()

    def register_event_handler(self):
        for key in self.gateways:
            gateway = self.gateways[key]
            gateway.register_event_handler()
        self.eventEngine.register(EVENT_DB_WRITE, self.write_mkt_data)
        self.eventEngine.register(EVENT_LOG, self.log_handler)
        self.eventEngine.register(EVENT_TICK, self.run_tick)
        self.eventEngine.register(EVENT_DAYSWITCH, self.day_switch)
        self.eventEngine.register(EVENT_TIMER, self.check_commands)
        if 'CTP' in self.type2gateway:
            self.eventEngine.register(EVENT_TDLOGIN + self.type2gateway['CTP'].gatewayName, self.ctp_qry_instruments)
            self.eventEngine.register(EVENT_QRYINSTRUMENT + self.type2gateway['CTP'].gatewayName, self.add_ctp_instruments)
            self.type2gateway['CTP'].setAutoDbUpdated(True)

    def ctp_qry_instruments(self, event):
        dtime = datetime.datetime.now()
        min_id = get_min_id(dtime)
        if min_id < 250:
            gateway = self.type2gateway['CTP']
            gateway.qry_commands.append(gateway.tdApi.qryInstrument)

    def add_ctp_instruments(self, event):
        data = event.dict['data']
        last = event.dict['last']
        if last:
            gateway = self.type2gateway['CTP']
            for symbol in gateway.qry_instruments:
                if symbol not in self.instruments:
                    self.add_instrument(symbol)

    def exit(self):
        for inst in self.instruments:
            self.min_switch(inst, False)
        self.eventEngine.stop()
        for name in self.gateways:
            gateway = self.gateways[name]
            gateway.close()
            gateway.mdApi = None
            gateway.tdApi = None
