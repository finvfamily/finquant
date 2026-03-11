"""
finquant - 交易模块

包含信号系统、账户管理、信号发布、券商适配器
"""

from finquant.trading.signal import (
    Action,
    OrderType,
    SignalType,
    Signal,
    buy_signal,
    sell_signal,
    hold_signal,
)

from finquant.trading.portfolio import (
    OrderStatus,
    Position,
    Order,
    Portfolio,
)

from finquant.trading.signal_bus import (
    SignalBus,
    signal_filter_by_action,
    signal_filter_by_strength,
    signal_filter_by_code,
    signal_deduplicate,
)

from finquant.trading.publisher import (
    SignalHandler,
    SignalPublisher,
    WebhookHandler,
    ConsoleHandler,
    FileHandler,
    RedisHandler,
)

from finquant.trading.broker import (
    BrokerOrderStatus,
    BrokerOrder,
    BrokerPosition,
    BrokerAccount,
    BrokerAdapter,
    BacktestBroker,
)

__all__ = [
    # 信号
    "Action",
    "OrderType",
    "SignalType",
    "Signal",
    "buy_signal",
    "sell_signal",
    "hold_signal",
    # 账户
    "OrderStatus",
    "Position",
    "Order",
    "Portfolio",
    # 信号总线
    "SignalBus",
    "signal_filter_by_action",
    "signal_filter_by_strength",
    "signal_filter_by_code",
    "signal_deduplicate",
    # 发布器
    "SignalHandler",
    "SignalPublisher",
    "WebhookHandler",
    "ConsoleHandler",
    "FileHandler",
    "RedisHandler",
    # 券商
    "BrokerOrderStatus",
    "BrokerOrder",
    "BrokerPosition",
    "BrokerAccount",
    "BrokerAdapter",
    "BacktestBroker",
]
