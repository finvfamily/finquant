"""
finquant - 信号总线

接收、过滤、转发信号
"""

from typing import List, Callable, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import threading


class SignalBus:
    """
    信号总线

    - 接收策略信号
    - 过滤/验证信号
    - 转发到处理器
    """

    def __init__(self):
        self._handlers: List[Callable] = []
        self._filters: List[Callable[[Any], bool]] = []
        self._signal_history: List[Dict] = []
        self._lock = threading.Lock()

    def subscribe(self, handler: Callable[[Any], None]):
        """订阅信号"""
        self._handlers.append(handler)

    def unsubscribe(self, handler: Callable[[Any], None]):
        """取消订阅"""
        if handler in self._handlers:
            self._handlers.remove(handler)

    def add_filter(self, filter_fn: Callable[[Any], bool]):
        """添加信号过滤器"""
        self._filters.append(filter_fn)

    def publish(self, signal, context: Dict[str, Any] = None):
        """
        发布信号

        Args:
            signal: Signal 对象
            context: 附加上下文信息
        """
        if signal is None:
            return

        # 应用过滤器
        for filter_fn in self._filters:
            if not filter_fn(signal):
                return

        # 记录历史
        self._record(signal, context)

        # 转发到处理器
        for handler in self._handlers:
            try:
                handler(signal, context or {})
            except Exception as e:
                print(f"Signal handler error: {e}")

    def _record(self, signal, context: Dict):
        """记录信号历史"""
        record = {
            "timestamp": datetime.now(),
            "signal": signal,
            "context": context,
        }
        with self._lock:
            self._signal_history.append(record)

            # 限制历史数量
            if len(self._signal_history) > 1000:
                self._signal_history = self._signal_history[-500:]

    def get_history(self, limit: int = 100) -> List[Dict]:
        """获取信号历史"""
        with self._lock:
            return self._signal_history[-limit:]

    def clear_history(self):
        """清空历史"""
        with self._lock:
            self._signal_history.clear()


# ========== 内置过滤器 ==========

def signal_filter_by_action(actions: List[str]):
    """按动作过滤信号"""
    def filter_fn(signal):
        return signal.action.value in actions
    return filter_fn


def signal_filter_by_strength(min_strength: float = 0.5):
    """按信号强度过滤"""
    def filter_fn(signal):
        return signal.strength >= min_strength
    return filter_fn


def signal_filter_by_code(codes: List[str]):
    """按股票代码过滤"""
    def filter_fn(signal):
        return signal.code in codes
    return filter_fn


def signal_deduplicate(window_seconds: int = 60):
    """去重：同一股票在窗口期内不重复发信号"""
    last_signals: Dict[str, datetime] = {}

    def filter_fn(signal):
        now = datetime.now()
        key = signal.code

        if key in last_signals:
            elapsed = (now - last_signals[key]).total_seconds()
            if elapsed < window_seconds:
                return False

        last_signals[key] = now
        return True

    return filter_fn


__all__ = [
    "SignalBus",
    "signal_filter_by_action",
    "signal_filter_by_strength",
    "signal_filter_by_code",
    "signal_deduplicate",
]
