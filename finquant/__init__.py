"""
finquant - 轻量级量化回测工具

纯 Python 脚本，无需服务端和数据缓存
使用 finshare 获取实时数据

V2 事件驱动架构:
- 向量化指标预计算
- 完全向量化信号生成
- 事件驱动架构
- 策略与引擎解耦
"""

__version__ = "2.0.0"
__author__ = "MeepoQuant"

# ========== 核心模块 ==========

# 事件系统
from finquant.core.event import (
    EventBus,
    Event,
    EventType,
    BarEvent,
    SignalEvent,
    OrderEvent,
    FillEvent,
)

# Broker
from finquant.core.broker import (
    Broker,
    Order,
    Position,
    OrderType,
    OrderStatus,
)

# 回测引擎
from finquant.core.engine import (
    BacktestEngineV2,
    BacktestConfig,
    backtest,
)

# 多资产
from finquant.core.multi_asset import (
    AssetType,
    AssetConfig,
    MultiAssetBroker,
    MultiAssetEngine,
    create_stock,
    create_futures,
    create_fund,
)

# ========== 策略模块 ==========

# 策略接口
from finquant.strategy.base import (
    Strategy,
    Signal,
    Action,
    Bar,
)

from finquant.strategy import (
    CompositeStrategy,
    MAStrategy,
    RSIStrategy,
    get_vectorized_strategy,
)

# 指标缓存
from finquant.data.cache import (
    IndicatorCache,
    IndicatorBuilder,
    get_indicator_cache,
    cached_indicator,
)

# ========== 数据模块 ==========

from finquant.data import (
    get_kline,
    get_realtime_quote,
    DataCache,
    get_data_cache,
    cached_data,
    DataLoader,
    FactorLoader,
    add_factor,
    FactorLibrary,
    FACTOR_REGISTRY,
    get_factor,
)

# ========== 风控模块 ==========

from finquant.risk import (
    RiskLevel,
    RiskConfig,
    RiskState,
    RiskManager,
    create_risk_manager,
    SlippageModel,
    FillPolicy,
    MarketCondition,
    OrderExecutor,
    create_executor,
    simple_backtest_with_slippage,
)

# ========== 优化模块 ==========

from finquant.optimize import (
    BayesianConfig,
    BayesianOptimizer,
    bayesian_optimize,
    WalkForwardConfig,
    WalkForwardOptimizer,
    walk_forward_optimize,
    SensitivityAnalyzer,
    ParameterStability,
)

# ========== API ==========

from finquant.api import (
    backtest,
    bt,
    compare,
    compare_strats,
    optimize,
    opt,
    quick_backtest,
)

# ========== 可视化 ==========

from finquant.visualize import (
    BacktestPlotter,
    plot,
    compare_results,
)

# ========== 交易模块 ==========

from finquant.trading import (
    Signal,
    Action,
    OrderType,
    SignalType,
    buy_signal,
    sell_signal,
    hold_signal,
    Portfolio,
    Position,
    SignalBus,
    signal_filter_by_action,
    signal_filter_by_strength,
    signal_filter_by_code,
    signal_deduplicate,
    SignalPublisher,
    WebhookHandler,
    ConsoleHandler,
    BacktestBroker,
)

# ========== 结果 ==========

from finquant.result import BacktestResult, compare_strategies

__all__ = [
    # 核心
    "EventBus",
    "Event",
    "EventType",
    "BarEvent",
    "SignalEvent",
    "OrderEvent",
    "FillEvent",
    "Broker",
    "Order",
    "Position",
    "OrderType",
    "OrderStatus",
    "BacktestEngineV2",
    "BacktestConfig",
    "backtest",
    "MultiAssetBroker",
    "MultiAssetEngine",
    "AssetType",
    "AssetConfig",
    "create_stock",
    "create_futures",
    "create_fund",
    # 策略
    "Strategy",
    "Signal",
    "Action",
    "Bar",
    "CompositeStrategy",
    "MAStrategy",
    "RSIStrategy",
    "get_vectorized_strategy",
    "IndicatorCache",
    "IndicatorBuilder",
    "get_indicator_cache",
    "cached_indicator",
    # 数据
    "get_kline",
    "get_realtime_quote",
    "DataCache",
    "get_data_cache",
    "cached_data",
    "DataLoader",
    "FactorLoader",
    "add_factor",
    "FactorLibrary",
    "FACTOR_REGISTRY",
    "get_factor",
    # 风控
    "RiskLevel",
    "RiskConfig",
    "RiskState",
    "RiskManager",
    "create_risk_manager",
    "SlippageModel",
    "FillPolicy",
    "MarketCondition",
    "OrderExecutor",
    "create_executor",
    "simple_backtest_with_slippage",
    # 优化
    "BayesianConfig",
    "BayesianOptimizer",
    "bayesian_optimize",
    "WalkForwardConfig",
    "WalkForwardOptimizer",
    "walk_forward_optimize",
    "SensitivityAnalyzer",
    "ParameterStability",
    # 交易
    "Signal",
    "Action",
    "OrderType",
    "SignalType",
    "buy_signal",
    "sell_signal",
    "hold_signal",
    "Portfolio",
    "Position",
    "SignalBus",
    "signal_filter_by_action",
    "signal_filter_by_strength",
    "signal_filter_by_code",
    "signal_deduplicate",
    "SignalPublisher",
    "WebhookHandler",
    "ConsoleHandler",
    "BacktestBroker",
    # API
    "bt",
    "compare",
    "compare_strats",
    "optimize",
    "opt",
    "quick_backtest",
    # 可视化
    "BacktestPlotter",
    "plot",
    "compare_results",
    # 结果
    "BacktestResult",
    "compare_strategies",
]
