"""
finquant - 券商适配器实现

包含:
1. 东方财富行情接口
2. 模拟实盘券商
"""

import asyncio
import json
import logging
import random
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode

import aiohttp
import requests

from finquant.trading.broker.websocket import (
    WsBroker,
    BrokerConfig,
    ConnectionState,
)

logger = logging.getLogger(__name__)


# ========== 东方财富行情 ==========

class EastMoneyQuote:
    """
    东方财富行情接口

    免费实时行情，支持股票、基金、港股等
    """

    # WebSocket 行情地址
    WS_URL = "wss://quote.eastmoney.com/ws"

    # HTTP 行情接口
    QUOTE_URL = "https://push2.eastmoney.com/api/qt/ulist.np/get"

    @classmethod
    def get_quote(cls, codes: List[str]) -> Dict[str, Dict]:
        """
        获取实时行情 (HTTP)

        Args:
            codes: 股票代码列表, 如 ["SH600519", "SZ000001"]

        Returns:
            {code: {price, change, volume, ...}}
        """
        if not codes:
            return {}

        # 转换代码格式
        secids = ",".join(cls._convert_code(c) for c in codes)

        params = {
            "fltt": 2,
            "invt": 2,
            "fields": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18",
            "secids": secids,
            "_": int(time.time() * 1000),
        }

        try:
            resp = requests.get(cls.QUOTE_URL, params=params, timeout=5)
            data = resp.json()

            result = {}
            if data.get("data") and data["data"].get("diff"):
                for item in data["data"]["diff"]:
                    code = cls._format_code(item.get("f12"), item.get("f13"))
                    result[code] = {
                        "name": item.get("f14", ""),
                        "price": item.get("f2"),
                        "change": item.get("f4"),
                        "change_pct": item.get("f3"),
                        "volume": item.get("f5"),
                        "amount": item.get("f6"),
                        "high": item.get("f17"),
                        "low": item.get("f16"),
                        "open": item.get("f1"),
                        "close": item.get("f18"),
                        "bid": item.get("f10"),   # 买一价
                        "ask": item.get("f9"),     # 卖一价
                        "turnover": item.get("f8"),  # 换手率
                    }
            return result
        except Exception as e:
            logger.error(f"获取行情失败: {e}")
            return {}

    @classmethod
    def _convert_code(cls, code: str) -> str:
        """转换代码格式"""
        code = code.strip().upper()
        if code.startswith("SH"):
            return f"1.{code[2:]}"
        elif code.startswith("SZ"):
            return f"0.{code[2:]}"
        elif code.startswith("BJ"):
            return f"0.{code[2:]}"
        return code

    @classmethod
    def _format_code(cls, secid: str, market: int) -> str:
        """格式化代码"""
        if market == 1:
            return f"SH{secid}"
        elif market == 0:
            return f"SZ{secid}"
        elif market == 4:  # 北京交易所
            return f"BJ{secid}"
        return secid


# ========== 模拟实盘券商 ==========

class SimulatedLiveBroker:
    """
    模拟实盘券商

    使用东方财富行情进行模拟交易
    适合实盘测试和策略验证
    """

    def __init__(self, config: BrokerConfig = None, initial_cash: float = 100000):
        if config is None:
            config = BrokerConfig()
        self.config = config
        self._cash = initial_cash
        self._positions: Dict[str, Dict] = {}
        self._quotes: Dict[str, float] = {}

        # 启动行情更新线程
        self._quote_thread = None
        self._quote_running = False
        self._initialized = False

    def initialize(self) -> bool:
        """初始化"""
        self._initialized = True
        self._quote_running = True
        self._quote_thread = threading.Thread(target=self._update_quotes, daemon=True)
        self._quote_thread.start()
        return True

    def _update_quotes(self):
        """更新行情"""
        codes = list(self._positions.keys()) if self._positions else []
        if not codes:
            codes = ["SH600519", "SZ000001", "SH000001"]

        while self._quote_running:
            try:
                quotes = EastMoneyQuote.get_quote(codes)
                for code, data in quotes.items():
                    self._quotes[code] = data.get("price", 0)
            except Exception as e:
                logger.error(f"更新行情失败: {e}")

            time.sleep(3)  # 3秒更新一次

    def buy(
        self,
        code: str,
        quantity: int,
        price: float = 0,
        order_type: str = "MARKET"
    ):
        """买入"""
        from finquant.trading.broker.base import BrokerOrder, BrokerOrderStatus

        # 获取当前价格
        if price <= 0:
            price = self._quotes.get(code, 0)
            if price <= 0:
                price = 10.0  # 默认价格

        order_id = f"LIVE{int(time.time() * 1000)}"

        # 计算成本
        cost = price * quantity * 1.001  # 万三手续费

        if self._cash >= cost:
            self._cash -= cost

            # 更新持仓
            if code not in self._positions:
                self._positions[code] = {
                    "shares": 0,
                    "avg_cost": 0,
                }

            pos = self._positions[code]
            total_cost = pos["shares"] * pos["avg_cost"] + price * quantity
            pos["shares"] += quantity
            pos["avg_cost"] = total_cost / pos["shares"] if pos["shares"] > 0 else 0

            order = BrokerOrder(
                order_id=order_id,
                broker_order_id=order_id,
                code=code,
                action="BUY",
                quantity=quantity,
                price=price,
                filled_quantity=quantity,
                avg_price=price,
                status=BrokerOrderStatus.FILLED,
            )
        else:
            order = BrokerOrder(
                order_id=order_id,
                code=code,
                action="BUY",
                quantity=quantity,
                price=price,
                status=BrokerOrderStatus.REJECTED,
                message="资金不足",
            )

        return order

    def sell(
        self,
        code: str,
        quantity: int,
        price: float = 0,
        order_type: str = "MARKET"
    ):
        """卖出"""
        from finquant.trading.broker.base import BrokerOrder, BrokerOrderStatus

        if price <= 0:
            price = self._quotes.get(code, 0)
            if price <= 0:
                price = 10.0

        order_id = f"LIVE{int(time.time() * 1000)}"

        if code not in self._positions or self._positions[code]["shares"] < quantity:
            order = BrokerOrder(
                order_id=order_id,
                code=code,
                action="SELL",
                quantity=quantity,
                price=price,
                status=BrokerOrderStatus.REJECTED,
                message="持仓不足",
            )
        else:
            # 卖出
            revenue = price * quantity * 0.999  # 卖出收印花税
            self._cash += revenue

            pos = self._positions[code]
            pos["shares"] -= quantity

            order = BrokerOrder(
                order_id=order_id,
                broker_order_id=order_id,
                code=code,
                action="SELL",
                quantity=quantity,
                price=price,
                filled_quantity=quantity,
                avg_price=price,
                status=BrokerOrderStatus.FILLED,
            )

        return order

    def get_account(self):
        """获取账户"""
        from finquant.trading.broker.base import BrokerAccount, BrokerPosition

        market_value = 0
        positions = []

        for code, pos in self._positions.items():
            if pos["shares"] > 0:
                current_price = self._quotes.get(code, pos["avg_cost"])
                mv = pos["shares"] * current_price
                market_value += mv

                positions.append(BrokerPosition(
                    code=code,
                    shares=pos["shares"],
                    avg_cost=pos["avg_cost"],
                    current_price=current_price,
                    market_value=mv,
                    profit=pos["shares"] * (current_price - pos["avg_cost"]),
                    profit_ratio=(current_price - pos["avg_cost"]) / pos["avg_cost"] if pos["avg_cost"] > 0 else 0,
                ))

        return BrokerAccount(
            cash=self._cash,
            market_value=market_value,
            total_assets=self._cash + market_value,
            positions=positions,
        )

    def get_positions(self) -> List:
        """获取持仓"""
        return self.get_account().positions

    def cancel_order(self, order_id: str) -> bool:
        """撤单"""
        return False  # 模拟交易不支持撤单

    def get_order_status(self, order_id: str):
        """订单状态"""
        from finquant.trading.broker.base import BrokerOrderStatus
        return BrokerOrderStatus.FILLED

    def get_quote(self, code: str) -> Optional[float]:
        """获取行情"""
        return self._quotes.get(code)

    def close(self):
        """关闭"""
        self._quote_running = False
        if self._quote_thread:
            self._quote_thread.join(timeout=1)


# ========== 便捷函数 ==========

def create_simulated_broker(
    initial_cash: float = 100000,
    watch_codes: List[str] = None
) -> SimulatedLiveBroker:
    """
    创建模拟实盘券商

    Args:
        initial_cash: 初始资金
        watch_codes: 关注的股票代码

    Returns:
        SimulatedLiveBroker 实例
    """
    broker = SimulatedLiveBroker.__new__(SimulatedLiveBroker)
    broker._cash = initial_cash
    broker._positions = {}
    broker._quotes = {}
    broker._initialized = True
    broker._quote_running = False
    broker._quote_thread = None

    if watch_codes:
        for code in watch_codes:
            broker._positions.setdefault(code, {"shares": 0, "avg_cost": 0})

    return broker


def get_realtime_quote(codes: List[str]) -> Dict[str, Dict]:
    """
    获取实时行情

    Args:
        codes: 股票代码列表

    Returns:
        行情数据
    """
    return EastMoneyQuote.get_quote(codes)


__all__ = [
    "EastMoneyQuote",
    "SimulatedLiveBroker",
    "create_simulated_broker",
    "get_realtime_quote",
]
