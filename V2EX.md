# finquant - 轻量级 Python 量化回测工具

---

## 项目介绍

大家好，分享一个我开发的轻量级 Python 量化回测工具 **finquant**。

完全开源：https://github.com/finvfamily/finquant

## 特性

- **纯 Python 脚本**：无需数据库、无需服务端，开箱即用
- **数据源**：使用 finshare 获取实时股票数据，支持 A 股
- **内置策略**：均线交叉、RSI、MACD、布林带、双 EMA 等
- **仓位控制**：固定仓位、金字塔、倒金字塔、ATR 波动率仓位
- **参数优化**：网格搜索参数优化

## 快速开始

```python
from finquant import get_kline, MACrossStrategy, BacktestEngine

# 获取数据（支持短码）
data = get_kline(["000001", "600000"], start="2024-01-01", end="2025-01-01")

# 创建策略和回测引擎
engine = BacktestEngine(initial_capital=100000)
result = engine.run(data, MACrossStrategy(short_period=5, long_period=20))

# 查看结果
print(result.summary())
```

## 仓位控制示例

```python
from finquant import (
    BacktestEngine,
    PyramidPositionSizer,  # 金字塔仓位（浮盈加仓）
)

engine = BacktestEngine(
    initial_capital=100000,
    position_sizer=PyramidPositionSizer(
        base_ratio=0.2,  # 基础仓位 20%
        max_ratio=1.0,   # 最大仓位 100%
        step=0.1,       # 每 10% 浮盈加仓一次
    ),
    max_positions=3,     # 最多 3 只持仓
    max_single_position=0.3,  # 单票最多 30%
)
```

## 安装

```bash
git clone https://github.com/finvfamily/finquant.git
cd finquant
pip install -r requirements.txt
pip install -e .
```

## 官方网站

https://meepoquant.com

---

欢迎 Star 和 Fork！

---
