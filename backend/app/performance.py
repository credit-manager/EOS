import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger("2to-eos.performance")


@dataclass
class PerformanceMetric:
    name: str
    value: float
    unit: str
    timestamp: float
    tags: dict = field(default_factory=dict)


class PerformanceMonitor:
    def __init__(self):
        self._metrics: list[PerformanceMetric] = []
        self._counters: dict[str, int] = defaultdict(int)
        self._timers: dict[str, list[float]] = defaultdict(list)
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = defaultdict(list)
    
    def record_metric(
        self,
        name: str,
        value: float,
        unit: str = "ms",
        tags: dict | None = None,
    ) -> None:
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=time.time(),
            tags=tags or {},
        )
        self._metrics.append(metric)
        
        if len(self._metrics) > 10000:
            self._metrics = self._metrics[-5000:]
    
    def increment_counter(self, name: str, value: int = 1) -> None:
        self._counters[name] += value
    
    def record_timer(self, name: str, duration_ms: float) -> None:
        self._timers[name].append(duration_ms)
        if len(self._timers[name]) > 1000:
            self._timers[name] = self._timers[name][-500:]
    
    def set_gauge(self, name: str, value: float) -> None:
        self._gauges[name] = value
    
    def record_histogram(self, name: str, value: float) -> None:
        self._histograms[name].append(value)
        if len(self._histograms[name]) > 1000:
            self._histograms[name] = self._histograms[name][-500:]
    
    def get_counter(self, name: str) -> int:
        return self._counters.get(name, 0)
    
    def get_timer_stats(self, name: str) -> dict:
        values = self._timers.get(name, [])
        if not values:
            return {"count": 0, "avg": 0, "min": 0, "max": 0, "p95": 0, "p99": 0}
        
        sorted_values = sorted(values)
        count = len(sorted_values)
        avg = sum(sorted_values) / count
        min_val = sorted_values[0]
        max_val = sorted_values[-1]
        
        p95_idx = int(count * 0.95)
        p99_idx = int(count * 0.99)
        
        return {
            "count": count,
            "avg": round(avg, 2),
            "min": round(min_val, 2),
            "max": round(max_val, 2),
            "p95": round(sorted_values[p95_idx], 2) if p95_idx < count else max_val,
            "p99": round(sorted_values[p99_idx], 2) if p99_idx < count else max_val,
        }
    
    def get_gauge(self, name: str) -> float | None:
        return self._gauges.get(name)
    
    def get_histogram_stats(self, name: str) -> dict:
        values = self._histograms.get(name, [])
        if not values:
            return {"count": 0, "avg": 0, "min": 0, "max": 0, "sum": 0}
        
        return {
            "count": len(values),
            "avg": round(sum(values) / len(values), 2),
            "min": round(min(values), 2),
            "max": round(max(values), 2),
            "sum": round(sum(values), 2),
        }
    
    def get_all_metrics(self) -> dict:
        return {
            "counters": dict(self._counters),
            "timers": {
                name: self.get_timer_stats(name)
                for name in self._timers
            },
            "gauges": dict(self._gauges),
            "histograms": {
                name: self.get_histogram_stats(name)
                for name in self._histograms
            },
        }
    
    def get_metrics_summary(self) -> dict:
        return {
            "total_metrics": len(self._metrics),
            "total_counters": len(self._counters),
            "total_timers": len(self._timers),
            "total_gauges": len(self._gauges),
            "total_histograms": len(self._histograms),
        }
    
    def reset(self) -> None:
        self._metrics.clear()
        self._counters.clear()
        self._timers.clear()
        self._gauges.clear()
        self._histograms.clear()


monitor = PerformanceMonitor()


class Timer:
    def __init__(self, name: str, tags: dict | None = None):
        self.name = name
        self.tags = tags or {}
        self.start_time: float | None = None
    
    def __enter__(self):
        self.start_time = time.monotonic()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration_ms = (time.monotonic() - self.start_time) * 1000
            monitor.record_timer(self.name, duration_ms)
            monitor.record_metric(
                name=self.name,
                value=duration_ms,
                unit="ms",
                tags=self.tags,
            )
            
            if duration_ms > 1000:
                logger.warning("Slow operation '%s': %.2fms", self.name, duration_ms)
        
        return False


def record_request_metric(method: str, path: str, status_code: int, duration_ms: float) -> None:
    monitor.record_timer("http.request.duration", duration_ms)
    monitor.record_histogram("http.request.duration", duration_ms)
    monitor.increment_counter("http.request.count")
    monitor.increment_counter(f"http.request.{status_code}")
    monitor.increment_counter(f"http.request.{method.lower()}")
    monitor.set_gauge("http.request.last_duration", duration_ms)


def record_db_metric(operation: str, duration_ms: float, success: bool = True) -> None:
    monitor.record_timer(f"db.{operation}.duration", duration_ms)
    monitor.record_histogram(f"db.{operation}.duration", duration_ms)
    monitor.increment_counter(f"db.{operation}.count")
    if not success:
        monitor.increment_counter(f"db.{operation}.errors")


def get_performance_stats() -> dict:
    return {
        "metrics": monitor.get_all_metrics(),
        "summary": monitor.get_metrics_summary(),
    }
