# -*- coding: utf-8 -*-
from cmq_rpc import RpcServer
import pandas as pd
import json
import time
from WindPy import w

SERVER_SETTING = {'rep': 'tcp://0.0.0.0:8100', 'pub': 'tcp://0.0.0.0:8110'}

class WindServer(RpcServer):
    def __init__(self, rep, pub):
        super(WindServer, self).__init__(rep, pub)
        self.register(self.wsd)
        self.register(self.wsi)
        w.start()

    def wsd(self, *args, **kwargs):
        try:
            raw_data = w.wsd(*args, **kwargs)
            if raw_data.ErrorCode < 0:
                return json.dumps(raw_data.Codes)
            df = pd.DataFrame(raw_data.Data)
            df = df.transpose()
            df.columns = [f.lower() for f in raw_data.Fields]
            df['date'] = raw_data.Times
            df.set_index(['date'])
            return df.to_json()
        except:
            return json.dumps({'error': 'something wrong in calculation'})

    def wsi(self, *args, **kwargs):
        try:
            raw_data = w.wsi(*args, **kwargs)
            if raw_data.ErrorCode < 0:
                return json.dumps(raw_data.Codes)
            df = pd.DataFrame(raw_data.Data)
            df = df.transpose()
            df.columns = [f.lower() for f in raw_data.Fields]
            df['datetime'] = raw_data.Times
            df = df.set_index(['datetime'])
            return df.to_json()
        except:
            return json.dumps({'error': 'something wrong in calculation'})

def run_wind_server(setting = SERVER_SETTING):
    server = WindServer(setting['rep'], setting['pub'])
    try:
        server.start()
        while 1:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()

if __name__ == '__main__':
    run_wind_server()

