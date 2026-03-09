# finquant

[官方网站](https://meepoquant.com) | 轻量级 Python 量化回测工具

## 特性

- **纯 Python 脚本**：无需数据库、无需服务端，开箱即用
- **灵活的数据源**：使用 [finshare](https://meepoquant.com) 获取实时股票数据
- **多种策略支持**：内置均线交叉、RSI、MACD、布林带等常用策略
- **仓位控制**：支持固定仓位，金字塔、倒金字塔、ATR 等多种仓位管理方式
- **参数优化**：网格搜索参数优化

## 安装

```bash
# 克隆项目
git clone https://github.com/meepo-quant/finquant.git
cd finquant

# 安装依赖
pip install -r requirements.txt

# 安装 finquant
pip install -e .
```

## 快速开始

```python
from datetime import date, timedelta
from finquant import get_kline, MACrossStrategy, BacktestEngine

# 获取数据（支持短码如 "000001"）
data = get_kline(["000001", "600000"], start="2024-01-01", end="2025-01-01")

# 创建策略
strategy = MACrossStrategy(short_period=5, long_period=20)

# 创建回测引擎
engine = BacktestEngine(initial_capital=100000)

# 运行回测
result = engine.run(data, strategy)

# 查看结果
print(result.summary())
```

## 策略示例

### 内置策略

```python
from finquant import (
    get_kline,
    MACrossStrategy,   # 均线交叉
    RSIStrategy,       # RSI 策略
    MACDStrategy,      # MACD 策略
    BollStrategy,      # 布林带策略
    DualEMAStrategy,   # 双重 EMA
)

# RSI 策略
strategy = RSIStrategy(period=14, oversold=30, overbought=70)

# MACD 策略
strategy = MACDStrategy(fast_period=12, slow_period=26, signal_period=9)
```

### 自定义策略

```python
import pandas as pd
from finquant import BaseStrategy, BacktestEngine, get_kline

class BreakoutStrategy(BaseStrategy):
    """价格突破20日高点买入，跌破20日低点卖出"""

    def __init__(self):
        super().__init__({"period": 20})

    def generate_signals(self, data: pd.DataFrame, code: str, current_date):
        stock_data = data[(data["code"] == code) & (data["trade_date"] <= current_date)]
        stock_data = stock_data.sort_values("trade_date")

        if len(stock_data) < 21:
            return 0

        stock_data["high20"] = stock_data["high"].rolling(20).max()
        stock_data["low20"] = stock_data["low"].rolling(20).min()

        last_close = stock_data["close"].iloc[-1]
        last_high = stock_data["high20"].iloc[-1]
        last_low = stock_data["low20"].iloc[-1]

        if last_close > last_high:
            return 1   # 买入
        elif last_close < last_low:
            return -1  # 卖出
        return 0

# 运行回测
data = get_kline(["000001"], start="2024-01-01", end="2025-01-01")
engine = BacktestEngine(initial_capital=100000)
result = engine.run(data, BreakoutStrategy())
print(result.summary())
```

## 仓位控制

```python
from finquant import (
    BacktestEngine,
    FixedPositionSizer,           # 固定仓位
    DynamicPositionSizer,          # 动态仓位
    PyramidPositionSizer,          # 金字塔仓位
    CounterPyramidPositionSizer,  # 倒金字塔仓位
)

# 固定半仓
engine = BacktestEngine(
    initial_capital=100000,
    position_sizer=FixedPositionSizer(0.5),
    max_positions=3,              # 最多3只持仓
    max_single_position=0.3,      # 单票最多30%仓位
)

# 金字塔仓位（浮盈加仓）
engine = BacktestEngine(
    initial_capital=100000,
    position_sizer=PyramidPositionSizer(
        base_ratio=0.2,   # 基础仓位 20%
        max_ratio=1.0,    # 最大仓位 100%
        step=0.1,         # 每10%浮盈加仓一次
    ),
)
```

## 参数优化

```python
from finquant import get_kline, MACrossStrategy, BacktestEngine
from finquant.optimize import GridSearchOptimizer

# 获取数据
data = get_kline(["000001"], start="2023-01-01", end="2024-12-31")

# 定义参数网格
param_grid = {
    "short_period": [5, 10, 15],
    "long_period": [20, 30, 40],
}

# 运行优化
optimizer = GridSearchOptimizer(
    data=data,
    strategy_class=MACrossStrategy,
    param_grid=param_grid,
    start_date="2024-01-01",
    end_date="2024-12-31",
)

results = optimizer.optimize(objective="sharpe_ratio")

# 获取最佳参数
best_params = optimizer.get_best_params()
print(f"最佳参数: {best_params}")
```

## 多策略比较

```python
from finquant import (
    get_kline, BacktestEngine,
    MACrossStrategy, RSIStrategy, MACDStrategy
)
from finquant.result import compare_strategies

data = get_kline(["000001"], start="2023-01-01", end="2024-12-31")

strategies = {
    "MA5-20": MACrossStrategy(5, 20),
    "MA10-30": MACrossStrategy(10, 30),
    "RSI": RSIStrategy(14, 30, 70),
    "MACD": MACDStrategy(12, 26, 9),
}

results = []
for name, strategy in strategies.items():
    engine = BacktestEngine(initial_capital=100000)
    result = engine.run(data, strategy)
    result.backtest_id = name
    results.append(result)

# 比较结果
comparison = compare_strategies(results)
print(comparison)
```

## API 参考

### 数据获取

| 函数 | 说明 |
|------|------|
| `get_kline(codes, start, end, adjust)` | 获取 K 线数据 |
| `get_realtime_quote(codes)` | 获取实时行情 |
| `ensure_full_code(code)` | 格式化股票代码 |

### 策略

| 策略类 | 说明 |
|--------|------|
| `MACrossStrategy` | 均线交叉策略 |
| `RSIStrategy` | RSI 策略 |
| `MACDStrategy` | MACD 策略 |
| `BollStrategy` | 布林带策略 |
| `DualEMAStrategy` | 双重 EMA 策略 |

### 仓位控制

| 仓位控制器 | 说明 |
|------------|------|
| `FixedPositionSizer` | 固定仓位比例 |
| `DynamicPositionSizer` | 动态仓位 |
| `PyramidPositionSizer` | 金字塔仓位 |
| `CounterPyramidPositionSizer` | 倒金字塔仓位 |

### 回测结果

```python
result.total_return     # 总收益率
result.annual_return    # 年化收益率
result.max_drawdown    # 最大回撤
result.sharpe_ratio    # 夏普比率
result.win_rate        # 胜率
result.total_trades    # 交易次数
result.trades          # 交易记录列表
result.get_trades_df() # 交易记录 DataFrame
```

## 依赖

- pandas >= 1.3.0
- numpy >= 1.20.0
- finshare >= 0.1.0

## 相关链接

- 官方网站: [https://meepoquant.com](https://meepoquant.com)
- finshare 数据源: [https://meepoquant.com](https://meepoquant.com)

## License

MIT License
