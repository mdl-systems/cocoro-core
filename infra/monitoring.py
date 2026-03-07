"""cocoro-core — Monitoring & Alerting (D-7)
システム監視・メトリクス収集・アラート管理。
Prometheus 互換 + 内部ヘルスダッシュボード。
"""
import time
import os
import asyncio
import logging

logger = logging.getLogger("cocoro.monitor")


class MetricsCollector:
    """内部メトリクス収集"""

    def __init__(self):
        self._counters: dict[str, int] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = {}
        self._start_time = time.time()

    def inc(self, name: str, value: int = 1):
        self._counters[name] = self._counters.get(name, 0) + value

    def set_gauge(self, name: str, value: float):
        self._gauges[name] = value

    def observe(self, name: str, value: float):
        if name not in self._histograms:
            self._histograms[name] = []
        self._histograms[name].append(value)
        # Keep last 1000 observations
        if len(self._histograms[name]) > 1000:
            self._histograms[name] = self._histograms[name][-1000:]

    def get_counter(self, name: str) -> int:
        return self._counters.get(name, 0)

    def get_gauge(self, name: str) -> float:
        return self._gauges.get(name, 0.0)

    def get_histogram_stats(self, name: str) -> dict:
        values = self._histograms.get(name, [])
        if not values:
            return {"count": 0}
        return {
            "count": len(values),
            "avg": round(sum(values) / len(values), 4),
            "min": round(min(values), 4),
            "max": round(max(values), 4),
            "p50": round(sorted(values)[len(values) // 2], 4),
            "p99": round(sorted(values)[int(len(values) * 0.99)], 4),
        }

    def to_prometheus(self) -> str:
        """Prometheus テキスト形式でメトリクスをエクスポート"""
        lines = []
        for name, val in self._counters.items():
            safe = name.replace(".", "_").replace("-", "_")
            lines.append(f"# TYPE cocoro_{safe} counter")
            lines.append(f"cocoro_{safe} {val}")
        for name, val in self._gauges.items():
            safe = name.replace(".", "_").replace("-", "_")
            lines.append(f"# TYPE cocoro_{safe} gauge")
            lines.append(f"cocoro_{safe} {val}")
        for name, values in self._histograms.items():
            safe = name.replace(".", "_").replace("-", "_")
            if values:
                lines.append(f"# TYPE cocoro_{safe} summary")
                lines.append(f'cocoro_{safe}_count {len(values)}')
                lines.append(f'cocoro_{safe}_sum {sum(values):.4f}')
        # Uptime
        lines.append("# TYPE cocoro_uptime_seconds gauge")
        lines.append(f"cocoro_uptime_seconds {time.time() - self._start_time:.0f}")
        return "\n".join(lines) + "\n"

    def get_all(self) -> dict:
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {k: self.get_histogram_stats(k) for k in self._histograms},
            "uptime_seconds": round(time.time() - self._start_time, 1),
        }


class AlertRule:
    """アラートルール定義"""
    def __init__(self, name: str, metric: str, condition: str,
                 threshold: float, severity: str = "warning"):
        self.name = name
        self.metric = metric
        self.condition = condition  # "gt", "lt", "eq"
        self.threshold = threshold
        self.severity = severity
        self.fired = False
        self.last_checked = 0.0

    def check(self, value: float) -> bool:
        self.last_checked = time.time()
        if self.condition == "gt":
            self.fired = value > self.threshold
        elif self.condition == "lt":
            self.fired = value < self.threshold
        elif self.condition == "eq":
            self.fired = value == self.threshold
        return self.fired

    def to_dict(self) -> dict:
        return {
            "name": self.name, "metric": self.metric,
            "condition": self.condition, "threshold": self.threshold,
            "severity": self.severity, "fired": self.fired,
            "last_checked": self.last_checked,
        }


class MonitoringManager:
    """監視・アラート統合管理"""

    def __init__(self):
        self.metrics = MetricsCollector()
        self._alerts: list[AlertRule] = []
        self._alert_history: list[dict] = []
        self._setup_default_alerts()

    def _setup_default_alerts(self):
        """デフォルトアラートルール"""
        self._alerts = [
            AlertRule("high_error_rate", "api.errors", "gt", 100, "critical"),
            AlertRule("slow_response", "api.response_time_avg", "gt", 5.0, "warning"),
            AlertRule("memory_high", "system.memory_pct", "gt", 90, "warning"),
            AlertRule("llm_failures", "llm.errors", "gt", 10, "critical"),
        ]

    def record_request(self, path: str, status: int, duration: float):
        """APIリクエストをメトリクスに記録"""
        self.metrics.inc("api.requests_total")
        self.metrics.observe("api.response_time", duration)
        if status >= 400:
            self.metrics.inc("api.errors")
        self.metrics.inc(f"api.status.{status}")

    def record_llm_call(self, model: str, duration: float, success: bool):
        """LLM呼び出しメトリクス記録"""
        self.metrics.inc("llm.calls_total")
        self.metrics.observe("llm.response_time", duration)
        if not success:
            self.metrics.inc("llm.errors")

    def check_alerts(self) -> list[dict]:
        """全アラートルールをチェック"""
        fired = []
        for rule in self._alerts:
            value = self.metrics.get_counter(rule.metric)
            if value == 0:
                value = self.metrics.get_gauge(rule.metric)
            if rule.check(value):
                alert = {**rule.to_dict(), "current_value": value,
                         "fired_at": time.time()}
                fired.append(alert)
                self._alert_history.append(alert)
        # Keep last 100 alerts
        self._alert_history = self._alert_history[-100:]
        return fired

    def add_alert(self, name: str, metric: str, condition: str,
                  threshold: float, severity: str = "warning") -> dict:
        """カスタムアラートルール追加"""
        rule = AlertRule(name, metric, condition, threshold, severity)
        self._alerts.append(rule)
        return rule.to_dict()

    def get_health_dashboard(self) -> dict:
        """ヘルスダッシュボード情報"""
        import psutil  # type: ignore
        try:
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            system = {
                "cpu_percent": cpu,
                "memory_percent": mem.percent,
                "memory_used_mb": round(mem.used / 1024 / 1024),
                "disk_percent": disk.percent,
            }
            self.metrics.set_gauge("system.cpu_pct", cpu)
            self.metrics.set_gauge("system.memory_pct", mem.percent)
        except ImportError:
            system = {"note": "psutil not installed"}

        return {
            "status": "healthy",
            "metrics": self.metrics.get_all(),
            "alerts": [r.to_dict() for r in self._alerts],
            "fired_alerts": [r.to_dict() for r in self._alerts if r.fired],
            "system": system,
        }

    def get_alert_history(self, limit: int = 50) -> list[dict]:
        return self._alert_history[-limit:]

    def get_prometheus_metrics(self) -> str:
        return self.metrics.to_prometheus()
