"""
finquant - 策略基类

事件驱动架构下的策略接口
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np


class Action(Enum):
    """交易动作"""
    BUY = 1
    SELL = -1
    HOLD = 0


@dataclass
class Signal:
    """交易信号"""
    action: Action
    code: str = ""  # 股票代码
    strength: float = 1.0
    price: float = 0
    reason: str = ""

    def __repr__(self):
        return f"Signal({self.action.name}, {self.code}, strength={self.strength})"


class Bar:
    """K线数据封装"""

    def __init__(self, code: str, trade_date, open: float, high: float,
                 low: float, close: float, volume: float):
        self.code = code
        self.trade_date = trade_date
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self._history_data: Optional[pd.DataFrame] = None

    def history(self, field: str, n: int) -> pd.Series:
        if self._history_data is None or self._history_data.empty:
            return pd.Series()
        return self._history_data[field].tail(n)

    def __repr__(self):
        return f"Bar({self.code}, {self.trade_date}, close={self.close})"


class Strategy(ABC):
    """策略基类（事件驱动版）"""

    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__
        self.params: Dict = {}
        self._position: Dict[str, int] = {}

    @property
    def position(self) -> Dict[str, int]:
        return self._position.copy()

    def update_position(self, code: str, shares: int) -> None:
        self._position[code] = shares

    def on_bar(self, bar: Bar) -> Optional[Signal]:
        return None

    def on_trade(self, code: str, action: Action, shares: int, price: float) -> None:
        pass

    def on_day_start(self, date) -> None:
        pass

    def on_day_end(self, date) -> None:
        pass

    def get_params(self) -> Dict:
        return self.params.copy()

    def set_params(self, **params) -> None:
        self.params.update(params)


def buy_signal(strength: float = 1.0, price: float = 0, reason: str = "") -> Signal:
    return Signal(Action.BUY, strength, price, reason)


def sell_signal(strength: float = 1.0, price: float = 0, reason: str = "") -> Signal:
    return Signal(Action.SELL, strength, price, reason)


def hold_signal(strength: float = 0, reason: str = "") -> Signal:
    return Signal(Action.HOLD, strength, 0, reason)
