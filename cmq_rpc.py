# encoding: UTF-8
import threading
import traceback
import signal
import zmq
import msgpack
import json
import cPickle
import time

signal.signal(signal.SIGINT, signal.SIG_DFL)

class DataPacker(object):
    def __init__(self):
        self.use_msgpack()
        self.use_json()
        # self.use_pickle()

    def pack(self, data):
        pass

    def unpack(self, data):
        pass

    def __json_pack(self, data):
        return json.dumps(data)

    def __json_unpack(self, data):
        return json.loads(data)

    def __msgpack_pack(self, data):
        return msgpack.packb(data)

    def __msgpack_unpack(self, data):
        return msgpack.unpackb(data)

    def __pickle_pack(self, data):
        return cPickle.dumps(data)

    def __pickle_unpack(self, data):
        return cPickle.loads(data)

    def use_json(self):
        self.pack = self.__json_pack
        self.unpack = self.__json_unpack

    def use_msgpack(self):
        self.pack = self.__msgpack_pack
        self.unpack = self.__msgpack_unpack

    def use_pickle(self):
        self.pack = self.__pickle_pack
        self.unpack = self.__pickle_unpack

class RpcServer(DataPacker):
    def __init__(self, rep_addr, pub_addr):
        super(RpcServer, self).__init__()
        self.__func_map = {}
        self.__context = zmq.Context()
        self.__rep_socket = self.__context.socket(zmq.REP)  # 请求回应socket
        self.__rep_socket.bind(rep_addr)
        self.__pub_socket = self.__context.socket(zmq.PUB)  # 数据广播socket
        self.__pub_socket.bind(pub_addr)
        self.__active = False  # server status
        self.__thread = threading.Thread(target=self.run)  # 服务器的工作线程

    def start(self):
        self.__active = True
        if not self.__thread.isAlive():
            self.__thread.start()

    def stop(self):
        self.__active = False
        if self.__thread.isAlive():
            self.__thread.join()
        self.__context.destroy()

    def run(self):
        while self.__active:
            if not self.__rep_socket.poll(1000):
                continue
            reqb = self.__rep_socket.recv()
            req = self.unpack(reqb)
            name, args, kwargs = req
            try:
                func = self.__func_map[name]
                r = func(*args, **kwargs)
                rep = [True, r]
            except Exception as e:
                rep = [False, traceback.format_exc()]
            repb = self.pack(rep)
            self.__rep_socket.send(repb)

    def publish(self, topic, data):
        datab = self.pack(data)
        self.__pub_socket.send_multipart([topic, datab])

    def register(self, func):
        self.__func_map[func.__name__] = func

class RpcClient(DataPacker):
    def __init__(self, req_addr, sub_addr):
        super(RpcClient, self).__init__()
        self.__req_addr = req_addr
        self.__sub_addr = sub_addr

        self.__context = zmq.Context()
        self.__req_socket = self.__context.socket(zmq.REQ)  # 请求发出socket
        self.__sub_socket = self.__context.socket(zmq.SUB)  # 广播订阅socket
        self.__active = False  # work status
        self.__thread = threading.Thread(target=self.run)

    # ----------------------------------------------------------------------
    def __getattr__(self, name):
        def dorpc(*args, **kwargs):
            req = [name, args, kwargs]
            reqb = self.pack(req)
            self.__req_socket.send(reqb)
            repb = self.__req_socket.recv()
            rep = self.unpack(repb)
            if rep[0]:
                return rep[1]
            else:
                raise RemoteException(rep[1])
        return dorpc

    def start(self):
        self.__req_socket.connect(self.__req_addr)
        self.__sub_socket.connect(self.__sub_addr)
        self.__active = True
        if not self.__thread.isAlive():
            self.__thread.start()

    def stop(self):
        self.__active = False
        if self.__thread.isAlive():
            self.__thread.join()

    def run(self):
        while self.__active:
            if not self.__sub_socket.poll(1000):
                continue
            topic, datab = self.__sub_socket.recv_multipart()
            data = self.unpack(datab)
            self.callback(topic, data)

    def callback(self, topic, data):
        raise NotImplementedError

    def subscribe_topic(self, topic):
        self.__sub_socket.setsockopt(zmq.SUBSCRIBE, topic)

class RemoteException(Exception):
    def __init__(self, value):
        self.__value = value

    # ----------------------------------------------------------------------
    def __str__(self):
        return self.__value

class TestRpcServer(RpcServer):
    def __init__(self, rep_address, pub_address):
        super(TestRpcServer, self).__init__(rep_address, pub_address)
        self.register(self.add)

    def add(self, a, b):
        print 'receiving: %s, %s' % (a, b)
        return a + b


class TestRpcClient(RpcClient):
    def __init__(self, req_addr, sub_addr):
        super(TestRpcClient, self).__init__(req_addr, sub_addr)

    def callback(self, topic, data):
        print 'client received topic:', topic, ', data:', data

def test_client():
    req_address = 'tcp://localhost:10010'
    sub_address = 'tcp://localhost:10020'
    tc = TestRpcClient(req_address, sub_address)
    tc.subscribe_topic('')
    tc.start()
    while 1:
        print tc.add(1, 3)
        time.sleep(2)

def test_server():
    rep_address = 'tcp://*:10010'
    pub_address = 'tcp://*:10020'
    ts = TestRpcServer(rep_address, pub_address)
    ts.start()
    while 1:
        content = 'current server time is %s' % time.time()
        print content
        ts.publish('test', content)
        time.sleep(2)
