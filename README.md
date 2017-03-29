基于ctp接口，使用tkinter作为GUI（可选择关掉）的python交易平台

主要功能：

(1)本地仓位管理，保证金计算，开仓平昨平今的逻辑

(2) 增加trade level以支持多腿下单，屏蔽开仓平仓逻辑，可以做跨合约套利

(3) 支持多品种，多策略同时运行并可手动更改交易参数

(4) 策略层增加tradepos level以便对trail profit, stop loss等增加支持

(5) 基于mySQL数据库，对实时数据tick,minute,daily进行保存

(6) 具有option pricng C++库swig接口

(7) 具有option模块和相应GUI(vol grid marker), 可以对波动率曲面调整，根据选择校准市场当前波动率

(8) 具有分钟级回测CTA策略，可以做vectorized回测和循环回测

(9) 支持仿真交易(历史数据paper trading)和实时模拟交易(实时数据paper trading)

(10) 初步使用算法交易模块

(11) 简单的系统内部交易匹配(order book)，以避免自成交和降低手续费

需要改进的方向：
(1) 提高backtest的效率，力求统一回测与实盘的代码
(2) 增加xspeed接口和股票接口
(3) 股票回测

有兴趣合作联系
QQ: 1940877918
