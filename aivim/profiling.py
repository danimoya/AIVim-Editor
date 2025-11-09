"""
Performance profiling utilities for AIVim
"""
import cProfile
import pstats
import functools
import time
import logging
from contextlib import contextmanager
from typing import Callable, Optional
from io import StringIO

logger = logging.getLogger(__name__)


class Profiler:
    """Performance profiling utilities"""

    _enabled = False  # Global profiling flag

    @classmethod
    def enable(cls):
        """Enable profiling globally"""
        cls._enabled = True
        logger.info("Profiling enabled")

    @classmethod
    def disable(cls):
        """Disable profiling globally"""
        cls._enabled = False
        logger.info("Profiling disabled")

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if profiling is enabled"""
        return cls._enabled

    @staticmethod
    def profile_function(sort_by: str = "cumulative", limit: int = 20):
        """
        Decorator to profile a function

        Args:
            sort_by: Sort statistic (cumulative, time, calls, etc.)
            limit: Number of lines to display

        Example:
            @Profiler.profile_function(sort_by="time", limit=10)
            def slow_function():
                # Implementation
                pass
        """

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if not Profiler._enabled:
                    return func(*args, **kwargs)

                profiler = cProfile.Profile()
                profiler.enable()

                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    profiler.disable()

                    # Print stats
                    stream = StringIO()
                    stats = pstats.Stats(profiler, stream=stream)
                    stats.sort_stats(sort_by)
                    stats.print_stats(limit)

                    logger.info(
                        f"\n{'=' * 60}\nProfile for {func.__name__}\n{'=' * 60}\n{stream.getvalue()}"
                    )

            return wrapper

        return decorator

    @staticmethod
    @contextmanager
    def profile_block(name: str, sort_by: str = "cumulative", limit: int = 10):
        """
        Context manager to profile a code block

        Args:
            name: Name for the profiled block
            sort_by: Sort statistic
            limit: Number of lines to display

        Example:
            with Profiler.profile_block("loading_file"):
                # Code to profile
                load_large_file()
        """
        if not Profiler._enabled:
            yield
            return

        profiler = cProfile.Profile()
        profiler.enable()

        try:
            yield
        finally:
            profiler.disable()

            stream = StringIO()
            stats = pstats.Stats(profiler, stream=stream)
            stats.sort_stats(sort_by)
            stats.print_stats(limit)

            logger.info(
                f"\n{'=' * 60}\nProfile for {name}\n{'=' * 60}\n{stream.getvalue()}"
            )

    @staticmethod
    def time_function(func: Callable) -> Callable:
        """
        Decorator to time function execution

        Example:
            @Profiler.time_function
            def slow_function():
                # Implementation
                pass
        """

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not Profiler._enabled:
                return func(*args, **kwargs)

            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            end_time = time.perf_counter()

            elapsed = end_time - start_time
            logger.info(f"{func.__name__} took {elapsed:.4f} seconds")

            return result

        return wrapper

    @staticmethod
    @contextmanager
    def time_block(name: str):
        """
        Context manager to time a code block

        Args:
            name: Name for the timed block

        Example:
            with Profiler.time_block("file_loading"):
                load_large_file()
        """
        if not Profiler._enabled:
            yield
            return

        start_time = time.perf_counter()
        try:
            yield
        finally:
            end_time = time.perf_counter()
            elapsed = end_time - start_time
            logger.info(f"{name} took {elapsed:.4f} seconds")


class PerformanceMonitor:
    """Monitor performance metrics over time"""

    def __init__(self):
        """Initialize performance monitor"""
        self.metrics = {}

    def record_metric(self, name: str, value: float):
        """
        Record a performance metric

        Args:
            name: Metric name
            value: Metric value (e.g., execution time in seconds)
        """
        if name not in self.metrics:
            self.metrics[name] = []

        self.metrics[name].append({"timestamp": time.time(), "value": value})

        # Keep only last 1000 measurements
        if len(self.metrics[name]) > 1000:
            self.metrics[name] = self.metrics[name][-1000:]

    def get_stats(self, name: str) -> dict:
        """
        Get statistics for a metric

        Args:
            name: Metric name

        Returns:
            Dictionary with min, max, avg, count
        """
        if name not in self.metrics or not self.metrics[name]:
            return {"count": 0}

        values = [m["value"] for m in self.metrics[name]]

        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "recent": values[-10:] if len(values) >= 10 else values,
        }

    def clear_metric(self, name: str):
        """Clear all measurements for a metric"""
        if name in self.metrics:
            self.metrics[name] = []

    def clear_all(self):
        """Clear all metrics"""
        self.metrics = {}

    @contextmanager
    def measure(self, name: str):
        """
        Context manager to measure and record execution time

        Args:
            name: Metric name

        Example:
            monitor = PerformanceMonitor()
            with monitor.measure("file_load"):
                load_file()
        """
        start_time = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start_time
            self.record_metric(name, elapsed)
