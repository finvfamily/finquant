"""
finquant - 组合策略
"""

from typing import List
import numpy as np

from finquant.strategy.base import Strategy, Signal, Action


class CompositeStrategy(Strategy):
    """组合多个子策略的信号"""

    def __init__(self, strategies: List[Strategy], combine_method: str = "vote"):
        super().__init__("CompositeStrategy")
        self.strategies = strategies
        self.combine_method = combine_method

    def on_bar(self, bar) -> Signal:
        signals = []
        for strategy in self.strategies:
            signal = strategy.on_bar(bar)
            if signal:
                signals.append(signal)

        if not signals:
            return None

        if self.combine_method == "vote":
            return self._combine_vote(signals)
        elif self.combine_method == "avg":
            return self._combine_avg(signals)
        return signals[0]

    def _combine_vote(self, signals: List[Signal]) -> Signal:
        buy = sum(1 for s in signals if s.action == Action.BUY)
        sell = sum(1 for s in signals if s.action == Action.SELL)
        hold = sum(1 for s in signals if s.action == Action.HOLD)

        if buy > sell and buy > hold:
            return Signal(Action.BUY, buy / len(signals))
        elif sell > buy and sell > hold:
            return Signal(Action.SELL, sell / len(signals))
        return Signal(Action.HOLD)

    def _combine_avg(self, signals: List[Signal]) -> Signal:
        avg_strength = np.mean([s.strength for s in signals])
        buys = [s for s in signals if s.action == Action.BUY]
        sells = [s for s in signals if s.action == Action.SELL]

        if len(buys) > len(sells):
            return Signal(Action.BUY, avg_strength)
        elif len(sells) > len(buys):
            return Signal(Action.SELL, avg_strength)
        return Signal(Action.HOLD)
