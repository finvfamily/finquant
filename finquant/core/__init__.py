"""
finquant - 核心模块

包含事件系统、订单管理、回测引擎、多资产管理
"""

from finquant.core.event import (
    EventBus,
    Event,
    EventType,
    BarEvent,
    SignalEvent,
    OrderEvent,
    FillEvent,
)

from finquant.core.broker import (
    Broker,
    Order,
    Position,
    OrderType,
    OrderStatus,
)

from finquant.core.engine import (
    BacktestEngineV2,
    BacktestConfig,
    backtest,
)

from finquant.core.multi_asset import (
    AssetType,
    AssetConfig,
    Position,
    MultiAssetBroker,
    MultiAssetEngine,
    create_stock,
    create_futures,
    create_fund,
)

__all__ = [
    # 事件
    "EventBus",
    "Event",
    "EventType",
    "BarEvent",
    "SignalEvent",
    "OrderEvent",
    "FillEvent",
    # Broker
    "Broker",
    "Order",
    "Position",
    "OrderType",
    "OrderStatus",
    # 引擎
    "BacktestEngineV2",
    "BacktestConfig",
    "backtest",
    # 多资产
    "AssetType",
    "AssetConfig",
    "MultiAssetBroker",
    "MultiAssetEngine",
    "create_stock",
    "create_futures",
    "create_fund",
]
