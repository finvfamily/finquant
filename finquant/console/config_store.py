"""
finquant - 配置持久化

管理券商配置、设置、策略配置的持久化存储
"""

import json
import os
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# 默认配置目录
DEFAULT_CONFIG_DIR = Path.home() / ".finquant"


@dataclass
class BrokerConfigData:
    """券商配置数据"""
    id: str
    name: str
    broker_type: str  # huatai, eastmoney, simulated
    config: Dict[str, Any]
    is_active: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    updated_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


@dataclass
class StrategyConfigData:
    """策略配置数据"""
    id: str
    name: str
    strategy_type: str
    params: Dict[str, Any]
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


@dataclass
class SettingsData:
    """设置数据"""
    # 自动执行
    auto_execute_signals: bool = False
    auto_buy_ratio: float = 0.2      # 每次买入金额占可用资金比例
    auto_sell_all: bool = True        # 卖出时是否全卖

    # 仓位控制
    max_position_pct: float = 0.3     # 单票最大仓位
    max_total_position: float = 0.9    # 总仓位上限
    min_cash_ratio: float = 0.1       # 最低现金比例

    # 交易设置
    default_order_type: str = "MARKET"  # 默认委托类型
    quote_refresh_interval: int = 3     # 行情刷新间隔

    # 风控
    enable_stop_loss: bool = False       # 启用止损
    stop_loss_pct: float = 0.05         # 止损比例
    enable_take_profit: bool = False    # 启用止盈
    take_profit_pct: float = 0.15       # 止盈比例

    # 其他
    log_level: str = "INFO"
    theme: str = "default"


@dataclass
class ConfigData:
    """配置数据"""
    version: str = "1.0"
    brokers: List[BrokerConfigData] = field(default_factory=list)
    active_broker_id: Optional[str] = None
    settings: SettingsData = field(default_factory=SettingsData)


class ConfigStore:
    """
    配置持久化存储

    配置文件存储在 ~/.finquant/config.json
    """

    def __init__(self, config_dir: str = None):
        if config_dir is None:
            self._config_dir = DEFAULT_CONFIG_DIR
        else:
            self._config_dir = Path(config_dir)

        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._config_file = self._config_dir / "config.json"

        # 加载配置
        self._data = self._load()

    def _load(self) -> ConfigData:
        """加载配置"""
        if self._config_file.exists():
            try:
                with open(self._config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # 转换 BrokerConfigData
                    brokers = []
                    for b in data.get("brokers", []):
                        brokers.append(BrokerConfigData(**b))
                    data["brokers"] = brokers

                    # 转换 SettingsData
                    if "settings" in data:
                        data["settings"] = SettingsData(**data["settings"])
                    else:
                        data["settings"] = SettingsData()

                    return ConfigData(**data)
            except Exception as e:
                logger.error(f"加载配置失败: {e}")

        return ConfigData()

    def _save(self):
        """保存配置"""
        try:
            # 手动转换为 dict
            data = {
                "version": self._data.version,
                "brokers": [],
                "active_broker_id": self._data.active_broker_id,
                "settings": {},
            }

            # 转换 BrokerConfigData
            for b in self._data.brokers:
                data["brokers"].append({
                    "id": b.id,
                    "name": b.name,
                    "broker_type": b.broker_type,
                    "config": b.config,
                    "is_active": b.is_active,
                    "created_at": b.created_at,
                    "updated_at": b.updated_at,
                })

            # 转换 SettingsData
            s = self._data.settings
            data["settings"] = {
                # 自动执行
                "auto_execute_signals": s.auto_execute_signals,
                "auto_buy_ratio": s.auto_buy_ratio,
                "auto_sell_all": s.auto_sell_all,
                # 仓位控制
                "max_position_pct": s.max_position_pct,
                "max_total_position": s.max_total_position,
                "min_cash_ratio": s.min_cash_ratio,
                # 交易设置
                "default_order_type": s.default_order_type,
                "quote_refresh_interval": s.quote_refresh_interval,
                # 风控
                "enable_stop_loss": s.enable_stop_loss,
                "stop_loss_pct": s.stop_loss_pct,
                "enable_take_profit": s.enable_take_profit,
                "take_profit_pct": s.take_profit_pct,
                # 其他
                "log_level": s.log_level,
                "theme": s.theme,
            }

            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.debug(f"配置已保存到 {self._config_file}")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")

    # ========== 券商管理 ==========

    def add_broker(self, name: str, broker_type: str, config: Dict[str, Any]) -> str:
        """添加券商"""
        import uuid
        broker_id = f"{broker_type}_{uuid.uuid4().hex[:8]}"

        broker = BrokerConfigData(
            id=broker_id,
            name=name,
            broker_type=broker_type,
            config=config,
        )

        # 如果是第一个券商，设为激活
        if not self._data.brokers:
            broker.is_active = True
            self._data.active_broker_id = broker_id

        self._data.brokers.append(broker)
        self._save()

        return broker_id

    def remove_broker(self, broker_id: str) -> bool:
        """删除券商"""
        for i, broker in enumerate(self._data.brokers):
            if broker.id == broker_id:
                self._data.brokers.pop(i)

                # 如果删除的是激活的券商，切换到第一个
                if self._data.active_broker_id == broker_id:
                    if self._data.brokers:
                        self._data.brokers[0].is_active = True
                        self._data.active_broker_id = self._data.brokers[0].id
                    else:
                        self._data.active_broker_id = None

                self._save()
                return True

        return False

    def update_broker(self, broker_id: str, **kwargs) -> bool:
        """更新券商"""
        for broker in self._data.brokers:
            if broker.id == broker_id:
                for key, value in kwargs.items():
                    if hasattr(broker, key):
                        setattr(broker, key, value)
                broker.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._save()
                return True
        return False

    def set_active_broker(self, broker_id: str) -> bool:
        """设置激活券商"""
        for broker in self._data.brokers:
            broker.is_active = (broker.id == broker_id)

        self._data.active_broker_id = broker_id
        self._save()
        return True

    def get_broker(self, broker_id: str) -> Optional[BrokerConfigData]:
        """获取券商"""
        for broker in self._data.brokers:
            if broker.id == broker_id:
                return broker
        return None

    def get_active_broker(self) -> Optional[BrokerConfigData]:
        """获取激活券商"""
        if self._data.active_broker_id:
            return self.get_broker(self._data.active_broker_id)
        return self._data.brokers[0] if self._data.brokers else None

    def list_brokers(self) -> List[BrokerConfigData]:
        """列出所有券商"""
        return self._data.brokers

    # ========== 设置管理 ==========

    def get_settings(self) -> SettingsData:
        """获取设置"""
        return self._data.settings

    def update_settings(self, **kwargs) -> bool:
        """更新设置"""
        for key, value in kwargs.items():
            if hasattr(self._data.settings, key):
                setattr(self._data.settings, key, value)
        self._save()
        return True

    # ========== 策略配置管理 ==========

    def add_strategy_config(
        self,
        name: str,
        strategy_type: str,
        params: Dict[str, Any],
    ) -> str:
        """添加策略配置"""
        import uuid
        strategy_id = f"strat_{uuid.uuid4().hex[:8]}"

        config = StrategyConfigData(
            id=strategy_id,
            name=name,
            strategy_type=strategy_type,
            params=params,
        )

        # 保存到单独文件
        self._save_strategy_config(config)
        return strategy_id

    def get_strategy_config(self, strategy_id: str) -> Optional[StrategyConfigData]:
        """获取策略配置"""
        strategy_file = self._config_dir / "strategies.json"
        if strategy_file.exists():
            try:
                with open(strategy_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for s in data.get("strategies", []):
                        if s.get("id") == strategy_id:
                            return StrategyConfigData(**s)
            except Exception:
                pass
        return None

    def list_strategy_configs(self) -> List[StrategyConfigData]:
        """列出策略配置"""
        strategy_file = self._config_dir / "strategies.json"
        if strategy_file.exists():
            try:
                with open(strategy_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return [StrategyConfigData(**s) for s in data.get("strategies", [])]
            except Exception:
                pass
        return []

    def remove_strategy_config(self, strategy_id: str) -> bool:
        """删除策略配置"""
        strategy_file = self._config_dir / "strategies.json"
        if strategy_file.exists():
            try:
                with open(strategy_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                strategies = [s for s in data.get("strategies", []) if s.get("id") != strategy_id]

                with open(strategy_file, "w", encoding="utf-8") as f:
                    json.dump({"strategies": strategies}, f, ensure_ascii=False, indent=2)
                return True
            except Exception:
                pass
        return False

    def _save_strategy_config(self, config: StrategyConfigData):
        """保存策略配置"""
        strategy_file = self._config_dir / "strategies.json"

        # 加载现有
        strategies = []
        if strategy_file.exists():
            try:
                with open(strategy_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    strategies = data.get("strategies", [])
            except Exception:
                pass

        # 添加新配置
        strategies.append({
            "id": config.id,
            "name": config.name,
            "strategy_type": config.strategy_type,
            "params": config.params,
            "created_at": config.created_at,
        })

        # 保存
        with open(strategy_file, "w", encoding="utf-8") as f:
            json.dump({"strategies": strategies}, f, ensure_ascii=False, indent=2)

    # ========== 工具方法 ==========

    def get_config_dir(self) -> Path:
        """获取配置目录"""
        return self._config_dir

    def reset(self):
        """重置配置"""
        self._data = ConfigData()
        self._save()

    def export_config(self) -> str:
        """导出配置（不包含敏感信息）"""
        data = asdict(self._data)

        # 移除敏感信息
        for broker in data.get("brokers", []):
            if "password" in broker.get("config", {}):
                broker["config"]["password"] = "***"
            if "app_secret" in broker.get("config", {}):
                broker["config"]["app_secret"] = "***"

        return json.dumps(data, ensure_ascii=False, indent=2)


# ========== 便捷函数 ==========

def get_config_store() -> ConfigStore:
    """获取配置存储"""
    return ConfigStore()


__all__ = [
    "ConfigStore",
    "BrokerConfigData",
    "SettingsData",
    "ConfigData",
    "get_config_store",
]
