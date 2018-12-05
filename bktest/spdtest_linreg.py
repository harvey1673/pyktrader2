import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)
import data_handler as dh
from backtest import *
import trade_position

class SpdLinRegSim(StratSim):
    def __init__(self, config):
        super(SpdLinRegSim, self).__init__(config)

    def process_data(self, df):
        self.df = df

    def process_config(self, config):
        self.assets = config['assets']
        self.offset = config['offset']
        self.reg_param = config['reg_param']
        self.reg_stdev = config['reg_stdev']
        self.reg_win = config.get('reg_win', 250)
        self.ma_win = config.get('ma_win', 0)
        self.entry_level = config['entry_level']
        self.exit_level = config['exit_level']
        #self.SL = config['stoploss']
        #self.pos_update = config['pos_update']
        #self.pos_class = config['pos_class']
        #self.pos_args  = config['pos_args']
        self.tcost = config['trans_cost']
        self.unit = config['unit']
        self.weights = config.get('weights', [1])

    def run_vec_sim(self):
        last_elem = len(self.assets)
        if len(self.assets) > len(self.reg_param):
            last_elem -= 1
            self.df[(self.assets[-2], 'close')] = self.df[(self.assets[-2], 'close')]/self.df[(self.assets[-1], 'close')]
        self.df['residual'] = self.df[(self.assets[0], 'close')]
        for asset, coeff in zip(self.assets[1:last_elem], self.reg_param[:-1]):
            self.df['residual'] -= self.df[(asset, 'close')] * coeff
        self.df['residual'] -= self.reg_param[-1]
        self.df['z_val'] = self.df['residual']/self.reg_stdev
        if self.ma_win > 0:
            self.df['z_ma'] = dh.EMA(self.df, self.ma_win, field = 'z_val')
        self.df['trade_signal'] = np.nan
        long_entry = self.df['z_val'] <= -self.entry_level
        short_entry = self.df['z_val'] >= self.entry_level
        long_exit = self.df['z_val'] >= -self.exit_level
        short_exit = self.df['z_val'] <= self.exit_level
        if self.ma_win > 0:
            long_entry = long_entry & (self.df['z_val'] >= self.df['z_ma'])
            short_entry = short_entry & (self.df['z_val'] <= self.df['z_ma'])
        switch_cont = pd.Series(False, index=self.df.index)
        for asset in self.assets:
            if (asset, 'contract') in self.df.columns:
                sht_cont = pd.Series(self.df[(asset, 'contract')].shift(-1), index=self.df.index)
                switch_cont = switch_cont | (self.df[(asset, 'contract')] != sht_cont)
        self.df['long_signal'] = np.nan
        self.df['short_signal'] = np.nan
        self.df.ix[long_entry, 'long_signal'] = 1.0
        self.df.ix[long_exit | switch_cont, 'long_signal'] = 0.0
        self.df['long_signal'] = self.df['long_signal'].fillna(method = 'ffill')
        self.df['long_signal'] = self.df['long_signal'].fillna(0.0)
        self.df.ix[short_entry, 'short_signal'] = -1.0
        self.df.ix[short_exit | switch_cont, 'short_signal'] = 0.0
        self.df['short_signal'] = self.df['short_signal'].fillna(method='ffill')
        self.df['short_signal'] = self.df['short_signal'].fillna(0.0)
        self.df['pos'] = self.df['long_signal'] + self.df['short_signal']
        self.df.ix[-1, 'pos'] = 0.0
        self.df['traded_price'] = self.df['residual']
        self.df['close'] = self.df['traded_price']
        self.df['cost'] = abs(self.df['pos'] - self.df['pos'].shift(1)) * (self.offset[0] + self.df[(self.assets[0], 'close')] * self.tcost)
        self.closed_trades = simdf_to_trades1(self.df, slippage=0.0)
        return ([self.df], self.closed_trades)

def gen_config_file(filename):
    sim_config = {}
    sim_config['sim_class']  = 'bktest.spdtest_linreg.SpdLinRegSim'
    sim_config['sim_func'] = 'run_vec_sim'
    sim_config['sim_freq'] = 'd'
    sim_config['scen_keys'] = ['ma_win', 'entry_level', 'exit_level']
    sim_config['sim_name']   = 'spd_linreg_static_180928'
    sim_config['products']   = [['plt_hrc_sea$spot', 'hc$1$-35b$fut', 'USDCNY$fx'],]
    sim_config['start_date'] = '20150901'
    sim_config['end_date']   = '20180928'
    sim_config['entry_level']  =  [0.5, 1.0, 1.5, 2.0]
    sim_config['exit_level'] = [0.2, 0, -0.2]
    sim_config['ma_win'] = [0, 10, 20]
    sim_config['pos_class'] = 'trade_position.TradePos'
    sim_config['offset']    = 1
    sim_config['sim_by_product'] = [{'reg_param': [0.83767, 79.18], 'reg_stdev': 20.0}, ]
    config = {'capital': 10000,
              'trans_cost': 0.0,
              'unit': 1,
              'pos_args': {},
              'pos_update': False,
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