"""
finquant - 信号发布器

将信号发送到各种目标
"""

from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from datetime import datetime
import json
import threading
from queue import Queue, Empty


class SignalHandler(ABC):
    """信号处理器基类"""

    @abstractmethod
    def send(self, signal, context: Dict[str, Any]) -> bool:
        """
        发送信号

        Returns:
            bool: 是否发送成功
        """
        pass

    def on_success(self, signal, result: Any):
        """发送成功回调"""
        pass

    def on_error(self, signal, error: Exception):
        """发送失败回调"""
        print(f"SignalHandler error: {error}")


class SignalPublisher:
    """
    信号发布器

    管理多个信号处理器，支持同步/异步发送
    """

    def __init__(self, async_mode: bool = False):
        self.handlers: List[SignalHandler] = []
        self.async_mode = async_mode
        self.queue: Optional[Queue] = None

        if async_mode:
            self.queue = Queue()
            self._worker_thread = threading.Thread(target=self._worker, daemon=True)
            self._worker_thread.start()

    def add_handler(self, handler: SignalHandler):
        """添加处理器"""
        self.handlers.append(handler)

    def remove_handler(self, handler: SignalHandler):
        """移除处理器"""
        if handler in self.handlers:
            self.handlers.remove(handler)

    def publish(self, signal, context: Dict[str, Any] = None) -> bool:
        """
        发布信号

        Args:
            signal: Signal 对象
            context: 附加上下文

        Returns:
            bool: 是否至少一个处理器成功
        """
        if not signal:
            return False

        if self.async_mode:
            return self._publish_async(signal, context)
        else:
            return self._publish_sync(signal, context)

    def _publish_sync(self, signal, context: Dict[str, Any]) -> bool:
        """同步发送"""
        success = False

        for handler in self.handlers:
            try:
                if handler.send(signal, context):
                    success = True
            except Exception as e:
                handler.on_error(signal, e)

        return success

    def _publish_async(self, signal, context: Dict[str, Any]) -> bool:
        """异步发送"""
        if self.queue:
            self.queue.put((signal, context))
        return True

    def _worker(self):
        """异步工作线程"""
        while True:
            try:
                signal, context = self.queue.get(timeout=1)
                self._publish_sync(signal, context)
            except Empty:
                continue
            except Exception as e:
                print(f"Async worker error: {e}")

    def stop(self):
        """停止异步模式"""
        if self.async_mode and self.queue:
            self.queue.put((None, None))  # 发送停止信号


# ========== 内置处理器 ==========

class WebhookHandler(SignalHandler):
    """
    Webhook 推送处理器

    支持钉钉、企业微信等 Webhook
    """

    def __init__(
        self,
        url: str,
        headers: Dict[str, str] = None,
        secret: str = None,  # 钉钉签名密钥
    ):
        self.url = url
        self.headers = headers or {"Content-Type": "application/json"}
        self.secret = secret

    def send(self, signal, context: Dict[str, Any]) -> bool:
        """发送 Webhook 请求"""
        try:
            import requests

            payload = self._build_payload(signal, context)

            # 钉钉签名
            if self.secret:
                import hmac
                import base64
                import hashlib

                timestamp = str(round(datetime.now().timestamp() * 1000))
                sign = self._generate_sign(timestamp)
                url = f"{self.url}&timestamp={timestamp}&sign={sign}"
            else:
                url = self.url

            response = requests.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=10,
            )

            return response.status_code == 200

        except ImportError:
            print("WebhookHandler: requests not installed")
            return False
        except Exception as e:
            self.on_error(signal, e)
            return False

    def _build_payload(self, signal, context: Dict) -> Dict:
        """构建请求载荷"""
        return {
            "msgtype": "text",
            "text": {
                "content": self._format_message(signal, context)
            }
        }

    def _format_message(self, signal, context: Dict) -> str:
        """格式化消息"""
        action_emoji = "🟢" if signal.action.value == "BUY" else "🔴"
        return f"""{action_emoji} {signal.action.value} 信号

代码: {signal.code}
价格: {signal.price or '市价'}
数量: {signal.quantity or '自动'}
原因: {signal.reason}
强度: {signal.strength:.0%}
时间: {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
"""

    def _generate_sign(self, timestamp: str) -> str:
        """生成钉钉签名"""
        import hmac
        import base64
        import hashlib

        string_to_sign = f"{timestamp}\n{self.secret}"
        sign = hmac.new(
            self.secret.encode(),
            string_to_sign.encode(),
            digestmod=hashlib.sha256
        ).digest()
        return base64.b64encode(sign).decode()


class ConsoleHandler(SignalHandler):
    """控制台输出处理器"""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose

    def send(self, signal, context: Dict[str, Any]) -> bool:
        """输出到控制台"""
        print(f"\n{'='*50}")
        print(f"📢 交易信号")
        print(f"{'='*50}")
        print(f"动作: {signal.action.value}")
        print(f"代码: {signal.code}")
        print(f"价格: {signal.price or '市价'}")
        print(f"数量: {signal.quantity or '自动计算'}")
        print(f"原因: {signal.reason}")
        print(f"强度: {signal.strength:.0%}")

        if self.verbose and context:
            print(f"\n上下文:")
            for k, v in context.items():
                print(f"  {k}: {v}")

        return True


class FileHandler(SignalHandler):
    """文件输出处理器"""

    def __init__(self, filepath: str):
        self.filepath = filepath

    def send(self, signal, context: Dict[str, Any]) -> bool:
        """写入文件"""
        try:
            with open(self.filepath, "a") as f:
                record = {
                    "timestamp": signal.timestamp.isoformat(),
                    "code": signal.code,
                    "action": signal.action.value,
                    "price": signal.price,
                    "quantity": signal.quantity,
                    "reason": signal.reason,
                    "context": context,
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            return True
        except Exception as e:
            self.on_error(signal, e)
            return False


class RedisHandler(SignalHandler):
    """Redis 缓存处理器"""

    def __init__(self, host: str = "localhost", port: int = 6379, key: str = "finquant:signals"):
        self.host = host
        self.port = port
        self.key = key
        self._client = None

    def _get_client(self):
        """获取 Redis 客户端"""
        if self._client is None:
            try:
                import redis
                self._client = redis.Redis(host=self.host, port=self.port, decode_responses=True)
            except ImportError:
                print("RedisHandler: redis not installed")
        return self._client

    def send(self, signal, context: Dict[str, Any]) -> bool:
        """写入 Redis"""
        client = self._get_client()
        if not client:
            return False

        try:
            record = json.dumps(signal.to_dict())
            client.lpush(self.key, record)
            # 只保留最近 100 条
            client.ltrim(self.key, 0, 99)
            return True
        except Exception as e:
            self.on_error(signal, e)
            return False


__all__ = [
    "SignalHandler",
    "SignalPublisher",
    "WebhookHandler",
    "ConsoleHandler",
    "FileHandler",
    "RedisHandler",
]
