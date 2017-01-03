基于ctp, xspeed接口，使用tkinter作为GUI（可选择关掉）的python交易平台

主要功能：

(1)本地仓位管理，保证金计算，开仓平昨平今的逻辑

(2) 增加trade level以支持多腿下单，屏蔽开仓平仓逻辑，可以做跨合约套利

(3) 支持多品种，多策略同时运行并可手动更改交易参数

(4) 策略层增加tradepos level以便对trail profit, stop loss等增加支持

(5) 基于mySQL数据库，对实时数据tick,minute,daily进行保存

(6) 具有option pricng C++库

(7) 具有option模块和相应GUI

(8) 具有分钟级回测CTA策略，可以做vectorized回测和循环回测

(9) 支持仿真交易(历史数据paper trading)和实时模拟交易(实时数据paper trading)

对1.0版本的提高与改进：
(1) 去掉实盘中用pandas的bar结构，改用numpy的struct array结构提速
(2) 改进回测
(3) 增加xspeed
(4) 对Position类增强以便准许某些品种避免高额平今手续费

需要改进的方向：
(1) 提高backtest的效率，力求统一回测与实盘的代码
(2) 增加trade execution的模块，引入执行算法
(3) 改进strategy/tradepos/trade/order的机制效率


有兴趣合作联系
QQ: 1940877918
