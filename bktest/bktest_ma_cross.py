import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)
import data_handler as dh
from backtest import *
import trade_position

class MACrossSim(StratSim):
    def __init__(self, config):
        super(MACrossSim, self).__init__(config)

    def process_config(self, config):
        self.offset = config['offset']
        self.win_list = config['win_list']
        self.ma_func = eval(config['ma_func'])
        self.use_chan = config.get('use_chan', False)
        self.close_daily = config['close_daily']
        self.data_freq = config['data_freq']
        self.tcost = config['trans_cost']
        self.unit = config['unit']
        self.proc_func = config['proc_func']
        self.proc_args = config['proc_args']
        self.chan_ratio = config['channel_ratio']
        if self.chan_ratio > 0:
            self.use_chan = True
            self.channel = int(self.chan_ratio * self.win_list[-1])
        else:
            self.use_chan = False
            self.channel = 0
        self.chan_func = config['channel_func']
        self.chan_high = eval(self.chan_func[0])
        self.chan_low  = eval(self.chan_func[1])
        self.high_args = config['channel_args'][0]
        self.low_args = config['channel_args'][1]

    def process_data(self, df):
        if (self.data_freq == 'm') and (self.freq > 1):
            xdf = self.proc_func(df, **self.proc_args)
            xdf['contract'] = self.df.ix[xdf.index, 'contract']
        else:
            xdf = df
        for idx, win in enumerate(self.win_list):
            xdf['MA' + str(idx + 1)] = self.ma_func(xdf, win).shift(1)
        if self.use_chan:
            xdf['chan_h'] = self.chan_high(xdf, self.channel, **self.chan_func['high']['args']).shift(2)
            xdf['chan_l'] = self.chan_low(xdf, self.channel, **self.chan_func['low']['args']).shift(2)
        else:
            xdf['chan_h'] = pd.Series(0, index = xdf.index)
            xdf['chan_l'] = pd.Series(0, index = xdf.index)
        self.df = xdf.dropna()

    def run_vec_sim(self):
        xdf = self.df.copy()
        long_signal = pd.Series(np.nan, index = xdf.index)
        last = len(self.win_list)
        long_flag = (xdf['MA1'] > xdf['MA2']) & (xdf['MA1'] > xdf['MA'+str(last)])
        if self.use_chan:
            long_flag = long_flag & (xdf['open'] >= xdf['chan_h'])
        long_signal[long_flag] = 1
        cover_flag = (xdf['MA1'] <= xdf['MA'+str(last)])
        if self.use_chan:
            cover_flag = cover_flag | (xdf['open'] < xdf['chan_l'])
        long_signal[cover_flag] = 0
        long_signal = long_signal.fillna(method='ffill').fillna(0)
        short_signal = pd.Series(np.nan, index = xdf.index)
        short_flag = (xdf['MA1'] <= xdf['MA2']) & (xdf['MA1'] <= xdf['MA'+str(last)])
        if self.use_chan:
            short_flag = short_flag & (xdf['open'] <= xdf['chan_l'])
        short_signal[short_flag] = -1
        cover_flag = (xdf['MA1'] > xdf['MA'+str(last)])
        if self.use_chan:
            cover_flag = cover_flag | (xdf['open'] > xdf['chan_h'])
        short_signal[cover_flag] = 0
        short_signal = short_signal.fillna(method='ffill').fillna(0)
        if len(xdf[(long_signal>0) & (short_signal<0)])>0:
            print xdf[(long_signal > 0) & (short_signal < 0)]
            print "something wrong with the position as long signal and short signal happen the same time"
        xdf['pos'] = long_signal + short_signal
        xdf.ix[-1, 'pos'] = 0.0
        xdf['cost'] = abs(xdf['pos'] - xdf['pos'].shift(1)) * (self.offset + xdf['open'] * self.tcost)
        xdf['cost'] = xdf['cost'].fillna(0.0)
        xdf['traded_price'] = xdf.open
        closed_trades = simdf_to_trades1(xdf, slippage = self.offset )
        return ([xdf], closed_trades)

def gen_config_file(filename):
    sim_config = {}
    sim_config['sim_func']  = 'run_vec_sim'
    sim_config['sim_class'] = 'bktest.bktest_ma_cross.MACrossSim'
    sim_config['scen_keys'] = ['win_list']
    sim_config['sim_freq'] = 'm'
    sim_config['sim_name']   = 'MA2_181028'
    sim_config['products']   = ['rb', 'hc', 'i', 'j','jm']
    sim_config['start_date'] = '20150901'
    sim_config['end_date']   = '20181028'
    space = 2
    sim_config['win_list'] = [[2+j*space, 3+i*space] for i in range(1,20) for j in range(i)]
    sim_config['pos_class'] = 'trade_position.TradePos'
    sim_config['proc_func'] = 'dh.day_split'
    sim_config['offset']    = 1
    config = {'capital': 10000,
              'trans_cost': 0.0,
              'unit': 1,
              'freq': 15,
              'stoploss': 0.0,
              'ma_func': 'dh.MA',
              'channel_func': ['dh.DONCH_H', 'dh.DONCH_L'],
              'channel_args': [{}, {}],
              'channel_ratio': 0.0,
              'proc_args': {'minlist': []},
              }
    sim_config['config'] = config
    with open(filename, 'w') as outfile:
        json.dump(sim_config, outfile)
    return sim_config

if __name__=="__main__":
    args = sys.argv[1:]
    if len(args) < 1:
        print "need to input a file name for config file"
    else:
        gen_config_file(args[0])
    pass