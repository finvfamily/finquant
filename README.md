# finquant V2.0.0

[官方网站](https://meepoquant.com) | 轻量级 Python 量化回测工具

## 特性

- **事件驱动架构**：解耦策略与引擎，支持多策略组合
- **本地缓存**：Parquet 格式缓存，支持增量更新，避免重复请求
- **完整风控体系**：止损止盈、最大回撤控制、仓位管理
- **执行精度模拟**：滑点、部分成交、市场冲击建模
- **参数优化**：贝叶斯优化、Walk-Forward、敏感性分析
- **多资产支持**：股票、ETF、LOF、科创板混合回测
- **详细交易日志**：每笔交易记录成本、收益、持仓盈亏

## 核心优势与解决的问题

### 1. 数据获取效率问题

**问题**：每次回测都从网络获取数据，重复请求耗时且浪费资源。

**解决**：
- 本地 Parquet 缓存，数据持久化
- 增量更新（3天容差），只请求新数据
- 多数据源自动切换（EastMoney → Tencent → Sina → Tdx → BaoStock）

### 2. 回测精度问题

**问题**：简单回测无法模拟真实交易场景，滑点、手续税计算不准确。

**解决**：
- 完整手续费计算（佣金、印花税、过户费）
- 滑点模拟（买入时高价、卖出时低价）
- A股最小买入单位（100股整数倍）
- 持仓市值实时计算

### 3. 策略开发效率问题

**问题**：策略代码与引擎耦合，难以独立单元测试。

**解决**：
- 事件驱动架构，策略完全独立
- `on_bar(bar)` 方法，策略只需关注信号生成
- `bar.history()` 获取历史数据，无需关心数据来源

### 4. 结果分析不完整问题

**问题**：传统回测只显示最终收益，缺乏详细持仓和盈亏分析。

**解决**：
- 每笔交易详细日志（日期、数量、成本、手续费、总资产）
- 按标的统计（已实现盈亏 + 未实现盈亏）
- 最终持仓详情（开仓日期、成本、现价、浮动盈亏）
- 完整权益曲线

### 对比其他框架

| 特性 | backtrader | backtesting.py | vectorbt | finquant |
|------|------------|-----------------|----------|----------|
| 事件驱动 | ✓ | ✗ | ✗ | ✓ |
| 本地缓存 | ✗ | ✗ | ✗ | ✓ (Parquet) |
| 增量更新 | ✗ | ✗ | ✗ | ✓ |
| A股支持 | △ | △ | △ | ✓ (100股最小单位) |
| 详细日志 | △ | △ | ✗ | ✓ |
| 多资产 | ✓ | ✗ | ✓ | ✓ |

### 典型使用场景

1. **快速验证策略想法**
   ```python
   from finquant import bt
   result = bt("SH600519", "ma_cross", short=5, long=20)
   ```

2. **完整回测分析**
   ```python
   data = get_kline(codes, start="2024-01-01")
   engine = BacktestEngineV2(config)
   result = engine.run(data, strategy)
   # 查看详细日志、持仓分析
   ```

3. **参数优化**
   ```python
   optimizer = BayesianOptimizer(param_bounds)
   best = optimizer.optimize(objective)
   ```

## 整体流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           finquant 量化回测流程                          │
└─────────────────────────────────────────────────────────────────────────┘

     ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
     │ 获取数据   │───▶│ 开发策略  │───▶│ 运行回测 │───▶│ 结果分析 │
     │ get_kline │    │ Strategy │    │ Engine   │    │ Plotter  │
     └──────────┘    └──────────┘    └──────────┘    └──────────┘
          │                │                │                │
          ▼                ▼                ▼                ▼
     ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
     │ 本地缓存   │    │ Signal   │    │ Broker   │    │ 收益分析 │
     │ Parquet   │    │ 生成信号  │    │ 订单执行 │    │ 可视化   │
     └──────────┘    └──────────┘    └──────────┘    └──────────┘

详细流程:

┌────────────────────────────────────────────────────────────────────────┐
│ 1. 数据获取 (get_kline)                                               │
│    ┌─────────────────────────────────────────────────────────────┐    │
│    │ • 多数据源: EastMoney, Tencent, Sina, Tdx, BaoStock     │    │
│    │ • 本地缓存: ~/.finquant/cache/ (Parquet 格式)            │    │
│    │ • 增量更新: 3天容差，避免重复请求                          │    │
│    │ • 自动缓存更新                                             │    │
│    └─────────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 2. 策略开发 (Strategy)                                                │
│    ┌─────────────────────────────────────────────────────────────┐    │
│    │ class MyStrategy(Strategy):                                │    │
│    │     def on_bar(self, bar) -> Signal:                      │    │
│    │         # 计算指标 MA, RSI, MACD, Bollinger...              │    │
│    │         # 生成信号 BUY/SELL/HOLD                            │    │
│    │         return Signal(Action.BUY, code=bar.code)           │    │
│    └─────────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 3. 回测引擎 (BacktestEngineV2)                                       │
│                                                                        │
│   ┌──────────────────────────────────────────────────────────────┐   │
│   │ 事件驱动循环:                                                  │   │
│   │   for date in trade_dates:                                   │   │
│   │       for each stock:                                         │   │
│   │           1. 触发 BarEvent (推送K线)                        │   │
│   │           2. 策略生成 Signal (on_bar)                        │   │
│   │           3. SignalEvent → 转换为 Order                     │   │
│   │           4. Broker 执行订单 (计算手续费/滑点)               │   │
│   │           5. 更新持仓和现金                                   │   │
│   │           6. 记录每日权益                                      │   │
│   └──────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 4. 结果分析 (BacktestResult)                                          │
│    ┌─────────────────────────────────────────────────────────────┐    │
│    │ • 收益率 (总收益、年化收益)                                  │    │
│    │ • 风险指标 (夏普比率、最大回撤)                             │    │
│    │ • 交易统计 (交易次数、胜率)                                 │    │
│    │ • 权益曲线 (每日资产变化)                                   │    │
│    │ • 按标的统计 (已实现盈亏+未实现盈亏)                        │    │
│    │ • 最终持仓 (开仓日期、成本、现价、盈亏)                      │    │
│    └─────────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────────┘
```

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              finquant 架构                              │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                              应用层 (API)                                │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐     │
│  │   bt()  │  │backtest│  │ optimize│  │ compare │  │  plot   │     │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                              核心模块                                    │
│                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │   strategy  │  │    core     │  │    data     │                  │
│  │             │  │             │  │             │                  │
│  │ Strategy    │  │ BacktestEng │  │ get_kline   │                  │
│  │ Signal     │  │ Broker      │  │ DataCache   │ ← 本地 Parquet  │
│  │ Action     │  │ EventBus    │  │ Loader      │ ← 增量更新      │
│  │ Bar        │  │ RiskMgr     │  │             │                  │
│  └─────────────┘  └─────────────┘  └─────────────┘                  │
│         │                │                │                            │
│         └────────────────┼────────────────┘                            │
│                          ▼                                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │   risk      │  │  optimize   │  │ visualize   │                  │
│  │             │  │             │  │             │                  │
│  │ RiskManager │  │ BayesianOpt │  │ Plotter     │                  │
│  │ Slippage    │  │ WalkForward │  │ compare     │                  │
│  │ FillPolicy  │  │ Sensitivity │  │             │                  │
│  └─────────────┘  └─────────────┘  └─────────────┘                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                              外部依赖                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │   finshare  │  │   pandas   │  │   numpy    │  │  scipy     │   │
│  │  (数据源)   │  │   (计算)   │  │  (计算)    │  │ (优化)     │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## 事件驱动架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           事件驱动流程                                  │
└─────────────────────────────────────────────────────────────────────────┘

     ┌─────────────┐
     │  BarEvent   │  (每个交易日每只股票)
     └──────┬──────┘
            │
            ▼
     ┌─────────────┐
     │ 策略.on_bar  │  ← 获取历史数据 bar.history()
     └──────┬──────┘
            │
            ▼  Signal (BUY/SELL/HOLD)
     ┌─────────────┐
     │ SignalEvent │
     └──────┬──────┘
            │
     ┌──────┴──────────────────────────────────┐
     │                                         │
     ▼                                         ▼
┌─────────────┐                         ┌─────────────┐
│ 风控检查     │                         │  风控检查    │
│ RiskManager │                         │ RiskManager  │
└──────┬──────┘                         └──────┬──────┘
       │                                        │
       ▼                                        ▼
┌─────────────┐                         ┌─────────────┐
│  转为 Order  │                         │  拒绝信号    │
└──────┬──────┘                         └─────────────┘
       │
       ▼
┌─────────────┐
│ Broker      │  ← 资金检查 / 持仓检查
│ 执行订单    │
└──────┬──────┘
       │
       ▼  FillEvent
┌─────────────┐
│ 更新持仓    │  ← 更新现金 / 更新持仓 / 记录交易
│ 更新现金    │
└─────────────┘
```

## 安装

### 环境要求

- Python 3.8+
- pandas >= 1.3.0
- numpy >= 1.20.0

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/finvfamily/finquant.git
cd finquant

# 2. 创建虚拟环境 (推荐)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 安装 finquant
pip install -e .

# 5. 验证安装
python -c "from finquant import get_kline; print('安装成功!')"
```

### 快速验证

```bash
# 运行示例
python examples/01_basic.py

# 运行完整测试
python examples/08_multi_assets_test.py
```

## finshare 数据源

> finquant 基于 finshare 构建，finshare 为 finquant 提供稳定的数据支持

[finshare](https://github.com/finvfamily/finshare) 是一个纯开源的 A股数据获取库（GitHub: github.com/finvfamily/finshare），完全免费，致力于解决 Python 量化投资的数据获取难题。

### finshare 特性

- **完全开源**：MIT 许可证，代码开源
- **多数据源**：EastMoney、腾讯、新浪、通达信、baostock 自动切换
- **支持全市场**：股票、ETF、LOF、基金、指数
- **实时行情**：支持批量实时行情获取
- **简单易用**：一行代码获取数据

### finshare 支持的数据源

| 数据源 | 说明 |
|--------|------|
| EastMoney (东方财富) | 默认首选，数据全面 |
| Tencent (腾讯) | 备用源 |
| Sina (新浪) | 备用源 |
| Tdx (通达信) | 备用源 |
| BaoStock (baostock) | 备用源 |

### finshare 安装

finshare 会作为 finquant 的依赖自动安装，也可单独安装：

```bash
pip install finshare
```

### 使用示例

```python
import finshare as fs

# 获取股票数据
data = fs.get_historical_data("SH600519", start="2024-01-01", end="2024-12-31")

# 获取实时行情
quote = fs.get_batch_snapshots(["SH600519", "SH000001"])
```

### finquant 中的数据获取

finquant 封装了 finshare，通过 `get_kline` 统一调用：

```python
from finquant import get_kline

# 获取多只股票
data = get_kline(["SH600519", "SH000001"], start="2024-01-01", end="2024-12-31")

# 获取 ETF
data = get_kline(["SH510300", "SH512880"], start="2024-01-01", end="2024-12-31")

# 获取 LOF
data = get_kline(["SH161039"], start="2024-01-01", end="2024-12-31")
```

### 代码格式说明

- `SH` + 6位数字：上海市场（SH600519, SH510300）
- `SZ` + 6位数字：深圳市场（SZ000001, SZ300750）
- `BJ` + 6位数字：北京市场

## 快速开始

```python
from finquant import bt

# 一行代码完成回测
result = bt("SH600519", "ma_cross", short=5, long=20, start="2024-01-01", end="2025-01-01")

# 查看结果
print(result.summary())
```

## 策略示例

```python
from finquant import (
    get_kline,
    MAStrategy,     # 均线交叉
    RSIStrategy,    # RSI 策略
    BacktestEngineV2,
)

# 获取数据
data = get_kline(["000001", "600000"], start="2024-01-01", end="2025-01-01")

# 创建策略
strategy = MAStrategy(short_period=5, long_period=20)

# 运行回测
engine = BacktestEngineV2(initial_capital=100000)
result = engine.run(data, strategy)

print(result.summary())
```

## 自定义策略

```python
from finquant import Strategy, Signal, Action, Bar

class BreakoutStrategy(Strategy):
    """价格突破20日高点买入"""

    def __init__(self):
        super().__init__("BreakoutStrategy")
        self.period = 20

    def on_bar(self, bar: Bar) -> Signal:
        history = bar.history('close', self.period + 1)
        if len(history) < self.period:
            return None

        current = history.iloc[-1]
        high_20 = history.rolling(20).max().iloc[-1]

        if current > high_20:
            return Signal(Action.BUY, reason="突破20日高点")

        return None
```

## 风控

```python
from finquant import RiskManager, RiskConfig, create_risk_manager

config = RiskConfig(
    stop_loss=0.05,      # 5% 止损
    take_profit=0.15,   # 15% 止盈
    max_drawdown=0.20,  # 20% 最大回撤
)

risk_mgr = create_risk_manager(config)
```

## 参数优化

```python
from finquant import bayesian_optimize, BacktestEngineV2, get_kline

data = get_kline(["000001"], start="2023-01-01", end="2024-12-31")

def objective(params):
    engine = BacktestEngineV2()
    result = engine.run(data, MAStrategy(**params))
    return result.sharpe_ratio

# 贝叶斯优化
best_params, score = bayesian_optimize(
    param_bounds={"short_period": (3, 20), "long_period": (20, 60)},
    objective_fn=objective,
    n_iter=50,
)
```

## 缓存说明

### 缓存位置

数据默认缓存在 `~/.finquant/cache/` 目录，格式为 Parquet。

### 缓存策略

- **首次请求**: 从网络获取数据，保存到本地缓存
- **增量更新**: 再次请求时，如果缓存数据与请求范围差距 > 3 天，自动增量更新
- **强制更新**: 删除缓存文件后重新获取

### 手动管理缓存

```python
from finquant.data.loader import DataCache

# 查看缓存位置
cache = DataCache()
print(cache.cache_dir)

# 清理缓存
cache.clear()
```

## 包结构

```
finquant/
├── __init__.py          # 统一导出
├── api.py               # 简洁 API (bt, backtest, compare...)
│
├── core/                # 核心模块
│   ├── __init__.py
│   ├── engine.py        # 回测引擎 (BacktestEngineV2)
│   ├── broker.py        # 券商 (持仓/订单/资金)
│   ├── event.py         # 事件系统 (EventBus/Event)
│   └── multi_asset.py   # 多资产支持
│
├── strategy/            # 策略模块
│   ├── __init__.py
│   ├── base.py         # 策略基类 (Strategy/Signal/Bar)
│   └── v2.py           # 内置策略 (MA/RSI/Boll...)
│
├── data/               # 数据模块
│   ├── __init__.py
│   ├── loader.py       # 数据加载 (get_kline/DataCache)
│   ├── cache.py        # 指标缓存
│   └── factors.py       # 因子库
│
├── risk/               # 风控模块
│   ├── __init__.py
│   └── risk.py         # 风险管理
│
├── optimize/           # 优化模块
│   ├── __init__.py
│   ├── bayesian.py     # 贝叶斯优化
│   └── walkforward.py  # Walk-Forward
│
└── visualize/          # 可视化
    ├── __init__.py
    └── plot.py         # 绘图
```

## 运行测试

```bash
pytest tests/ -v
```

## 依赖

- pandas >= 1.3.0
- numpy >= 1.20.0
- finshare >= 1.0.2 (数据源)
- scipy >= 1.8.0 (参数优化)

## 相关链接

- 官方网站: [https://meepoquant.com](https://meepoquant.com)
- GitHub: https://github.com/finvfamily/finquant

## 致谢

finquant 的开发参考和借鉴了以下开源项目：

### 回测框架

- **[backtrader](https://www.backtrader.com/)** - Python 经典回测框架，事件驱动架构的参考
- **[backtesting.py](https://github.com/kernc/backtesting.py)** - 简洁的 Python 回测库
- **[vectorbt](https://github.com/polygon-io/vectorbt)** - 向量化回测框架，性能优化参考

### 数据源

- **[finshare](https://github.com/finvfamily/finshare)** ⭐ - 纯开源 A股数据库（我们开源的项目！），finquant 的数据后端
- **[akshare](https://akshare.akfamily.xyz/)** - A股数据开源库，多数据源设计参考
- **[baostock](https://www.baostock.com/)** - 证券数据开源库

### 量化策略

- **[ta-lib](https://ta-lib.org/)** - 技术分析库，指标计算参考
- **[pandas-ta](https://github.com/twopirllc/pandas-ta)** - Pandas 技术分析扩展

### 其他

- **[numpy](https://numpy.org/)** - 数值计算基础
- **[pandas](https://pandas.pydata.org/)** - 数据分析基础
- **[scipy](https://scipy.org/)** - 科学计算，贝叶斯优化依赖

感谢以上开源项目的作者和贡献者！

## License

MIT License
