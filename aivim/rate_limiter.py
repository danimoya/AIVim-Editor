"""
Rate limiting for AI API calls
"""
import time
import threading
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter for API calls

    Implements the token bucket algorithm for rate limiting API calls.
    Tokens are added to the bucket at a constant rate, and each API call
    consumes one token. If no tokens are available, the call must wait.
    """

    def __init__(
        self,
        calls_per_minute: int = 60,
        burst_size: Optional[int] = None,
        wait_timeout: float = 30.0,
    ):
        """
        Initialize rate limiter

        Args:
            calls_per_minute: Maximum number of calls allowed per minute
            burst_size: Maximum burst size (defaults to calls_per_minute)
            wait_timeout: Maximum time to wait for a token (seconds)
        """
        self.capacity = calls_per_minute
        self.burst_size = burst_size or calls_per_minute
        self.tokens = float(self.burst_size)
        self.last_update = time.time()
        self.wait_timeout = wait_timeout
        self.lock = threading.Lock()

        # Statistics
        self.total_requests = 0
        self.blocked_requests = 0
        self.timeout_requests = 0

        logger.info(
            f"Rate limiter initialized: {calls_per_minute} calls/min, "
            f"burst: {self.burst_size}, timeout: {wait_timeout}s"
        )

    def acquire(self, tokens: int = 1, block: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Acquire permission to make API call(s)

        Args:
            tokens: Number of tokens to acquire (default: 1)
            block: Whether to block if tokens not available
            timeout: Override default wait timeout (seconds)

        Returns:
            True if tokens acquired, False if timeout or non-blocking and unavailable

        Example:
            if rate_limiter.acquire():
                # Make API call
                make_api_call()
            else:
                # Handle rate limit
                logger.warning("Rate limit exceeded")
        """
        timeout = timeout if timeout is not None else self.wait_timeout
        start_time = time.time()

        self.total_requests += 1

        while True:
            with self.lock:
                self._refill()

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    logger.debug(
                        f"Token acquired. Remaining: {self.tokens:.2f}/{self.burst_size}"
                    )
                    return True

            if not block:
                self.blocked_requests += 1
                logger.debug("Token acquisition failed (non-blocking)")
                return False

            elapsed = time.time() - start_time
            if elapsed >= timeout:
                self.timeout_requests += 1
                logger.warning(
                    f"Token acquisition timeout after {elapsed:.2f}s"
                )
                return False

            # Wait a bit before retrying
            time.sleep(0.1)

    def _refill(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_update

        # Add tokens based on time elapsed
        tokens_to_add = elapsed * (self.capacity / 60.0)  # Convert per-minute to per-second
        self.tokens = min(self.burst_size, self.tokens + tokens_to_add)
        self.last_update = now

    def get_wait_time(self) -> float:
        """
        Get estimated wait time for next token

        Returns:
            Estimated wait time in seconds
        """
        with self.lock:
            self._refill()

            if self.tokens >= 1:
                return 0.0

            # Calculate time needed to accumulate 1 token
            tokens_needed = 1.0 - self.tokens
            seconds_per_token = 60.0 / self.capacity
            return tokens_needed * seconds_per_token

    def reset(self):
        """Reset the rate limiter to initial state"""
        with self.lock:
            self.tokens = float(self.burst_size)
            self.last_update = time.time()
            logger.info("Rate limiter reset")

    def get_stats(self) -> dict:
        """
        Get rate limiter statistics

        Returns:
            Dictionary with statistics
        """
        with self.lock:
            self._refill()
            return {
                "total_requests": self.total_requests,
                "blocked_requests": self.blocked_requests,
                "timeout_requests": self.timeout_requests,
                "current_tokens": self.tokens,
                "capacity": self.capacity,
                "burst_size": self.burst_size,
                "block_rate": (
                    self.blocked_requests / self.total_requests
                    if self.total_requests > 0
                    else 0.0
                ),
            }

    def __enter__(self):
        """Context manager entry - acquire token"""
        if not self.acquire():
            raise TimeoutError("Rate limit timeout")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        pass


class MultiProviderRateLimiter:
    """
    Rate limiter that manages limits for multiple providers

    Each AI provider can have different rate limits.
    """

    def __init__(self):
        """Initialize multi-provider rate limiter"""
        self.limiters: dict[str, RateLimiter] = {}
        self.default_calls_per_minute = 60

    def set_provider_limit(
        self, provider: str, calls_per_minute: int, burst_size: Optional[int] = None
    ):
        """
        Set rate limit for a specific provider

        Args:
            provider: Provider name
            calls_per_minute: Maximum calls per minute
            burst_size: Optional burst size
        """
        self.limiters[provider] = RateLimiter(
            calls_per_minute=calls_per_minute, burst_size=burst_size
        )
        logger.info(
            f"Set rate limit for {provider}: {calls_per_minute} calls/min"
        )

    def get_limiter(self, provider: str) -> RateLimiter:
        """
        Get rate limiter for a provider

        Args:
            provider: Provider name

        Returns:
            RateLimiter instance for the provider
        """
        if provider not in self.limiters:
            self.limiters[provider] = RateLimiter(
                calls_per_minute=self.default_calls_per_minute
            )
            logger.info(
                f"Created default rate limiter for {provider}: "
                f"{self.default_calls_per_minute} calls/min"
            )

        return self.limiters[provider]

    def acquire(self, provider: str, block: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Acquire token for a specific provider

        Args:
            provider: Provider name
            block: Whether to block if no tokens available
            timeout: Optional timeout override

        Returns:
            True if token acquired, False otherwise
        """
        limiter = self.get_limiter(provider)
        return limiter.acquire(block=block, timeout=timeout)

    def get_stats(self, provider: Optional[str] = None) -> dict:
        """
        Get statistics for provider(s)

        Args:
            provider: Optional provider name (if None, returns all)

        Returns:
            Dictionary with statistics
        """
        if provider:
            if provider in self.limiters:
                return {provider: self.limiters[provider].get_stats()}
            return {}

        return {name: limiter.get_stats() for name, limiter in self.limiters.items()}

    def reset(self, provider: Optional[str] = None):
        """
        Reset rate limiter(s)

        Args:
            provider: Optional provider name (if None, resets all)
        """
        if provider:
            if provider in self.limiters:
                self.limiters[provider].reset()
        else:
            for limiter in self.limiters.values():
                limiter.reset()
