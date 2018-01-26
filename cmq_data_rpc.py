from cmq_rpc import RpcServer, DataPacker, RpcClient
from threading import Thread
from time import sleep
from eventEngine import *
from eventType import *

def test_data_api(*args, **kwargs):
    return {}

class DataServer(RpcServer):
    def __init__(self, settings):
        super(DataServer, self).__init__(settings['rep_addr'], settings['pub_addr'])
        self.instruments = settings.get('instruments', [])
        self.poll_period = settings.get('period', 1)
        api_str = settings.get('data_api', 'test_data_api')
        api_str_split = api_str.split('.')
        if len(api_str_split) <= 1:
            self.data_api = eval(api_str)
        else:
            api_module = __import__('.'.join(api_str_split[:-1]))
            for i in range(1, len(api_str_split)):
                api_module = getattr(api_module, api_str_split[i])
            self.data_api = api_module
        self.register(self.subscribe)
        self.register(self.unsubscribe)
        self.register(self.set_poll_flag)
        self.poll_thread = Thread(target=self.poll_data)
        self.poll_flag = False

    def start(self):
        super(DataServer, self).start()
        self.set_poll_flag(True)
        if not self.thread.isAlive():
            self.thread.start()

    def stop(self):
        super(DataServer, self).stop()
        self.set_poll_flag(False)
        if self.thread.isAlive():
            self.thread.join()
            self.thread = None

    def subscribe(self, inst):
        if inst not in self.instruments:
            self.instruments.append(inst)
        return True

    def unsubscribe(self, inst):
        if inst in self.instruments:
            self.instruments.remove(inst)
        return True

    def _get_data(self):
        return self.data_api(*self.instruments)

    def set_poll_flag(self, flag):
        self.poll_flag = flag

    def _decode_data(self, data):
        return data

    def poll_data(self):
        while self.__active:
            data = self._get_data()
            results = self._decode_data(data)
            for inst in self.instruments:
                if inst in results:
                    self.publish(inst, results[inst])
            sleep(self.poll_period)

class PassiveDataServer(DataServer):
    def __init__(self, settings):
        super(PassiveDataServer, self).__init__(settings)

    def callback_func(self):
        pass

class DataClient(RpcClient):
    def __init__(self, settings, event_engine):
        super(DataClient, self).__init__(settings['req_addr'], settings['sub_addr'])
        self.event_engine = event_engine
        self.instruments = settings.get('instruments', [])

    def callback(self, topic, data):
        event = Event(type=EVENT_MARKETDATA)
        data['instID'] = topic
        event.dict['data'] = data
        self.event_engine.put(event)

    def add_instrument(self, instID):
        self.instruments.append(instID)
        self.subscribe_topic(instID)
        self.subscribe(instID)

    def suspend_server(self):
        self.set_poll_flag(False)

    def resume_server(self):
        self.set_poll_flag(True)

def test_data_conn():
    settings = {
            'rep_addr': "tcp://*:10050",
            'pub_addr': "tcp://*:10060",
            'instruments': ['RB1805', 'HC1805', 'I1805','J1805'],
            'period': 2.0,
            'data_api': 'web_data.sina_fut_live',
            'req_addr': 'tcp://localhost:10050',
            'sub_addr': 'tcp://localhost:10060',
            }
    server = DataServer(settings)
    ee = PriEventEngine(1.0)
    ee.register(EVENT_MARKETDATA, test_callback)
    client = DataClient(settings, ee)
    ee.start()
    client.subscribe_topic('RB1805')
    sleep(10)
    client.stop()
    server.stop()
    ee.stop()

def test_callback(event):
    inst = event.dict['instID']
    data = event.dict['data']
    print inst, data

if __name__ == '__main__':
    test_data_conn()
