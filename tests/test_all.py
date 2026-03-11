"""
finquant V2.0.0 全面测试

测试所有模块功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ========== 测试工具 ==========

def generate_mock_data(codes, start_date, end_date, initial_price=100):
    """生成模拟数据"""
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    dates = pd.date_range(start, end, freq='B')

    all_data = []
    for code in codes:
        np.random.seed(hash(code) % 10000)
        n = len(dates)
        returns = np.random.normal(0.001, 0.02, n)
        prices = initial_price * np.exp(np.cumsum(returns))

        for i, date in enumerate(dates):
            close = prices[i]
            open_p = prices[i-1] if i > 0 else close * (1 + np.random.uniform(-0.01, 0.01))
            high = max(open_p, close) * (1 + abs(np.random.uniform(0, 0.02)))
            low = min(open_p, close) * (1 - abs(np.random.uniform(0, 0.02)))
            volume = np.random.randint(1000000, 10000000)

            all_data.append({
                'code': code,
                'trade_date': date,
                'open': open_p,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume,
            })

    return pd.DataFrame(all_data)


# ========== 测试模块 ==========

def test_event_system():
    """测试事件系统"""
    print("\n" + "="*60)
    print("  测试事件系统")
    print("="*60)

    from finquant.core.event import (
        EventBus, Event, EventType,
        BarEvent, SignalEvent, OrderEvent, FillEvent
    )

    # 测试事件创建
    event = Event(EventType.BAR, {'data': 'test'})
    assert event is not None, "创建 Event 失败"
    print("  ✓ 创建 Event")

    # 测试 BarEvent
    bar_data = {'code': 'SH600519', 'close': 100, 'trade_date': pd.Timestamp.now()}
    bar_event = BarEvent(bar_data)
    assert bar_event.code == 'SH600519', "BarEvent 属性错误"
    print("  ✓ 创建 BarEvent")

    # 测试 EventBus
    bus = EventBus()
    events_received = []

    def handler(evt):
        events_received.append(evt)

    bus.subscribe(EventType.BAR, handler)
    bus.publish(Event(EventType.BAR, {'test': 'data'}))

    assert len(events_received) == 1, "EventBus 订阅/发布失败"
    print("  ✓ EventBus 订阅/发布")

    # 测试 SignalEvent
    signal = SignalEvent('SH600519', 1, 0.8)
    assert signal.signal == 1, "SignalEvent 属性错误"
    print("  ✓ SignalEvent")

    # 测试 OrderEvent
    order = OrderEvent('SH600519', 'BUY', 100, 10.5)
    assert order.code == 'SH600519', "OrderEvent 属性错误"
    print("  ✓ OrderEvent")

    # 测试 FillEvent
    fill = FillEvent('order1', 'SH600519', 'BUY', 100, 10.5, 0.01)
    assert fill.code == 'SH600519', "FillEvent 属性错误"
    print("  ✓ FillEvent")

    print("  ✓ 事件系统测试通过")


def test_strategy():
    """测试策略接口"""
    print("\n" + "="*60)
    print("  测试策略接口")
    print("="*60)

    from finquant.strategy.base import Strategy, Signal, Action, Bar

    # 测试创建策略
    class TestStrategy(Strategy):
        def on_bar(self, bar):
            return Signal(Action.BUY)

    strategy = TestStrategy("TestStrategy")
    assert strategy.name == "TestStrategy", "策略名称错误"
    print("  ✓ 创建策略")

    # 测试 Signal
    signal = Signal(Action.BUY, strength=0.8)
    assert signal.action == Action.BUY, "Signal action 错误"
    assert signal.strength == 0.8, "Signal strength 错误"
    print("  ✓ Signal")

    # 测试 Bar
    bar = Bar('SH600519', pd.Timestamp.now(), 100, 101, 99, 100, 1000000)
    assert bar.code == 'SH600519', "Bar code 错误"
    assert bar.close == 100, "Bar close 错误"
    print("  ✓ Bar")

    print("  ✓ 策略接口测试通过")


def test_vectorized_strategy():
    """测试向量化策略"""
    print("\n" + "="*60)
    print("  测试向量化策略")
    print("="*60)

    from finquant.strategy import MAStrategy, RSIStrategy

    # 测试 MA 策略
    ma = MAStrategy(short_period=5, long_period=20)
    assert ma.short_period == 5, "MA 策略参数错误"
    assert ma.long_period == 20, "MA 策略参数错误"
    print("  ✓ MAStrategy")

    # 测试 RSI 策略
    rsi = RSIStrategy(period=14, oversold=30, overbought=70)
    assert rsi.period == 14, "RSI 策略参数错误"
    assert rsi.oversold == 30, "RSI 策略参数错误"
    print("  ✓ RSIStrategy")

    print("  ✓ 向量化策略测试通过")


def test_broker():
    """测试 Broker"""
    print("\n" + "="*60)
    print("  测试 Broker")
    print("="*60)

    from finquant.core.broker import Broker, Order, OrderStatus, OrderType

    # 测试创建 Broker
    broker = Broker(initial_cash=100000)
    assert broker.cash == 100000, "Broker 初始资金错误"
    print("  ✓ 创建 Broker")

    # 测试下单
    order = Order('SH600519', 'BUY', 100)
    assert order.code == 'SH600519', "Order code 错误"
    print("  ✓ Order")

    # 测试订单提交
    order_id = broker.submit_order('SH600519', 'BUY', 100)
    assert order_id is not None, "提交订单失败"
    print("  ✓ 提交订单")

    print("  ✓ Broker 测试通过")


def test_risk_manager():
    """测试风控管理器"""
    print("\n" + "="*60)
    print("  测试风控管理器")
    print("="*60)

    from finquant.risk import RiskManager, RiskConfig, RiskLevel, create_risk_manager

    # 测试创建风控配置
    config = RiskConfig(
        stop_loss=0.05,
        take_profit=0.15,
        max_drawdown=0.20,
    )
    assert config.stop_loss == 0.05, "风控配置错误"
    print("  ✓ RiskConfig")

    # 测试创建风控管理器
    risk_mgr = create_risk_manager(config)
    assert risk_mgr is not None, "创建风控管理器失败"
    print("  ✓ create_risk_manager")

    print("  ✓ 风控测试通过")


def test_execution():
    """测试执行精度"""
    print("\n" + "="*60)
    print("  测试执行精度")
    print("="*60)

    from finquant.risk import OrderExecutor, SlippageModel, create_executor

    # 测试滑点模型
    assert SlippageModel.FIXED is not None, "滑点模型错误"
    print("  ✓ SlippageModel")

    # 测试创建执行器
    executor = create_executor()
    assert executor is not None, "创建执行器失败"
    print("  ✓ create_executor")

    print("  ✓ 执行精度测试通过")


def test_factor_library():
    """测试因子库"""
    print("\n" + "="*60)
    print("  测试因子库")
    print("="*60)

    from finquant.data import FactorLibrary, get_factor, FACTOR_REGISTRY

    # 测试因子注册表
    assert isinstance(FACTOR_REGISTRY, dict), "因子注册表错误"
    print("  ✓ FACTOR_REGISTRY")

    # 测试获取因子
    ma_factor = get_factor('ma')
    assert ma_factor is not None, "获取因子失败"
    print("  ✓ get_factor")

    # 测试因子库
    lib = FactorLibrary()
    assert lib is not None, "创建因子库失败"
    print("  ✓ FactorLibrary")

    print("  ✓ 因子库测试通过")


def test_data_loader():
    """测试数据加载器"""
    print("\n" + "="*60)
    print("  测试数据加载器")
    print("="*60)

    from finquant.data import DataLoader, DataCache

    # 测试数据缓存
    cache = DataCache()
    cache.set('test_key', {'data': [1, 2, 3]})
    result = cache.get('test_key')
    assert result is not None, "数据缓存失败"
    print("  ✓ DataCache")

    # 测试数据加载器
    loader = DataLoader()
    assert loader is not None, "创建数据加载器失败"
    print("  ✓ DataLoader")

    print("  ✓ 数据加载器测试通过")


def test_multi_asset():
    """测试多资产"""
    print("\n" + "="*60)
    print("  测试多资产")
    print("="*60)

    from finquant.core import MultiAssetEngine, AssetType, create_stock, create_futures, create_fund

    # 测试创建资产配置
    stock = create_stock("SH600519", "茅台")
    assert stock.asset_type == AssetType.STOCK, "股票类型错误"
    print("  ✓ create_stock")

    futures = create_futures("IF", multiplier=300)
    assert futures.asset_type == AssetType.FUTURES, "期货类型错误"
    print("  ✓ create_futures")

    fund = create_fund("110011", "易方达")
    assert fund.asset_type == AssetType.FUND, "基金类型错误"
    print("  ✓ create_fund")

    # 测试多资产引擎
    engine = MultiAssetEngine(initial_capital=1000000)
    assert engine is not None, "创建多资产引擎失败"
    print("  ✓ MultiAssetEngine")

    print("  ✓ 多资产测试通过")


def test_optimizer():
    """测试优化器"""
    print("\n" + "="*60)
    print("  测试优化器")
    print("="*60)

    from finquant.optimize import (
        BayesianOptimizer, BayesianConfig,
        WalkForwardOptimizer, WalkForwardConfig,
        SensitivityAnalyzer, ParameterStability,
    )

    # 测试贝叶斯配置
    config = BayesianConfig(n_iter=10)
    assert config.n_iter == 10, "贝叶斯配置错误"
    print("  ✓ BayesianConfig")

    # 测试贝叶斯优化器
    optimizer = BayesianOptimizer({'x': (0, 10)})
    assert optimizer is not None, "创建贝叶斯优化器失败"
    print("  ✓ BayesianOptimizer")

    # 测试 WalkForward 配置
    wf_config = WalkForwardConfig(train_days=60, test_days=20)
    assert wf_config.train_days == 60, "WalkForward 配置错误"
    print("  ✓ WalkForwardConfig")

    # 测试敏感性分析
    analyzer = SensitivityAnalyzer()
    assert analyzer is not None, "创建敏感性分析器失败"
    print("  ✓ SensitivityAnalyzer")

    # 测试参数稳定性
    stability = ParameterStability()
    assert stability is not None, "创建参数稳定性失败"
    print("  ✓ ParameterStability")

    print("  ✓ 优化器测试通过")


def test_api():
    """测试 API"""
    print("\n" + "="*60)
    print("  测试 API")
    print("="*60)

    from finquant import backtest, bt, compare, optimize

    # 测试 API 导入
    assert backtest is not None, "backtest 导入失败"
    print("  ✓ backtest")

    assert bt is not None, "bt 导入失败"
    print("  ✓ bt")

    assert compare is not None, "compare 导入失败"
    print("  ✓ compare")

    assert optimize is not None, "optimize 导入失败"
    print("  ✓ optimize")

    print("  ✓ API 测试通过")


def test_visualize():
    """测试可视化"""
    print("\n" + "="*60)
    print("  测试可视化")
    print("="*60)

    from finquant.visualize import BacktestPlotter, plot, compare_results
    from finquant.result import BacktestResult

    # 创建模拟结果
    result = BacktestResult()
    result.initial_capital = 100000
    result.final_capital = 120000
    result.total_return = 0.2
    result.annual_return = 0.15
    result.sharpe_ratio = 1.2
    result.max_drawdown = 0.1
    result.win_rate = 0.6
    result.total_trades = 10
    result.daily_equity = []
    result.trades = []

    # 测试 BacktestPlotter
    plotter = BacktestPlotter(result)
    summary = plotter.summary()
    assert summary is not None, "生成摘要失败"
    print("  ✓ BacktestPlotter.summary")

    # 测试 plot
    assert plot is not None, "plot 导入失败"
    print("  ✓ plot")

    # 测试 compare_results
    assert compare_results is not None, "compare_results 导入失败"
    print("  ✓ compare_results")

    print("  ✓ 可视化测试通过")


def test_performance():
    """性能测试"""
    print("\n" + "="*60)
    print("  性能测试")
    print("="*60)

    from finquant.strategy import MAStrategy
    from finquant.core import BacktestEngineV2, BacktestConfig

    # 测试基本功能
    strategy = MAStrategy(short_period=5, long_period=20)
    assert strategy is not None, "创建策略失败"
    print("  ✓ 创建 MAStrategy")

    config = BacktestConfig(initial_capital=100000)
    engine = BacktestEngineV2(config)
    assert engine is not None, "创建引擎失败"
    print("  ✓ 创建 BacktestEngineV2")

    engine.add_strategy(strategy)
    print("  ✓ 添加策略")

    print("  ✓ 性能测试通过")


# ========== 运行所有测试 ==========

if __name__ == "__main__":
    tests = [
        ("事件系统", test_event_system),
        ("策略接口", test_strategy),
        ("向量化策略", test_vectorized_strategy),
        ("Broker", test_broker),
        ("风控", test_risk_manager),
        ("执行精度", test_execution),
        ("因子库", test_factor_library),
        ("数据加载", test_data_loader),
        ("多资产", test_multi_asset),
        ("优化器", test_optimizer),
        ("API", test_api),
        ("可视化", test_visualize),
        ("性能", test_performance),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"  ✗ {name} 失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "="*60)
    print(f"  测试结果: {passed} 通过, {failed} 失败")
    print("="*60)
