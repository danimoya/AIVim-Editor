"""
Unit tests for rate limiter
"""
import pytest
import time
from aivim.rate_limiter import RateLimiter, MultiProviderRateLimiter


class TestRateLimiter:
    """Test basic rate limiter functionality"""

    def test_create_rate_limiter(self):
        """Test rate limiter creation"""
        limiter = RateLimiter(calls_per_minute=60)
        assert limiter.capacity == 60
        assert limiter.burst_size == 60
        assert limiter.tokens == 60.0

    def test_acquire_immediate(self):
        """Test immediate token acquisition"""
        limiter = RateLimiter(calls_per_minute=60)
        assert limiter.acquire() is True

    def test_acquire_multiple(self):
        """Test multiple token acquisitions"""
        limiter = RateLimiter(calls_per_minute=60, burst_size=10)

        # Should succeed for burst size
        for _ in range(10):
            assert limiter.acquire(block=False) is True

        # Should fail when exhausted
        assert limiter.acquire(block=False) is False

    def test_acquire_non_blocking(self):
        """Test non-blocking acquisition"""
        limiter = RateLimiter(calls_per_minute=60, burst_size=1)

        # First acquire succeeds
        assert limiter.acquire(block=False) is True

        # Second acquire fails (no blocking)
        assert limiter.acquire(block=False) is False

    def test_token_refill(self):
        """Test token refill over time"""
        # High rate for faster testing
        limiter = RateLimiter(calls_per_minute=600, burst_size=1)  # 10 tokens/sec

        # Exhaust token
        assert limiter.acquire(block=False) is True
        assert limiter.acquire(block=False) is False

        # Wait for refill (0.1 second = 1 token at 10/sec)
        time.sleep(0.15)

        # Should have refilled
        assert limiter.acquire(block=False) is True

    def test_reset(self):
        """Test rate limiter reset"""
        limiter = RateLimiter(calls_per_minute=60, burst_size=5)

        # Exhaust tokens
        for _ in range(5):
            limiter.acquire(block=False)

        assert limiter.acquire(block=False) is False

        # Reset
        limiter.reset()

        # Should have tokens again
        assert limiter.acquire(block=False) is True

    def test_get_stats(self):
        """Test statistics tracking"""
        limiter = RateLimiter(calls_per_minute=60, burst_size=2)

        # Make some requests
        limiter.acquire()  # Success
        limiter.acquire()  # Success
        limiter.acquire(block=False)  # Blocked

        stats = limiter.get_stats()
        assert stats['total_requests'] == 3
        assert stats['blocked_requests'] == 1
        assert stats['block_rate'] > 0

    def test_get_wait_time(self):
        """Test wait time calculation"""
        limiter = RateLimiter(calls_per_minute=60, burst_size=1)

        # Exhaust token
        limiter.acquire()

        # Get wait time
        wait_time = limiter.get_wait_time()
        assert wait_time > 0  # Should need to wait

        # After waiting, should be 0
        time.sleep(wait_time + 0.1)
        wait_time = limiter.get_wait_time()
        assert wait_time == 0

    def test_context_manager(self):
        """Test context manager usage"""
        limiter = RateLimiter(calls_per_minute=60, burst_size=1)

        # Should work
        with limiter:
            pass

        # Should raise timeout when exhausted
        with pytest.raises(TimeoutError):
            with limiter:
                pass

    def test_custom_burst_size(self):
        """Test custom burst size"""
        limiter = RateLimiter(calls_per_minute=60, burst_size=5)

        # Should allow burst of 5
        for _ in range(5):
            assert limiter.acquire(block=False) is True

        # Should fail on 6th
        assert limiter.acquire(block=False) is False


class TestMultiProviderRateLimiter:
    """Test multi-provider rate limiter"""

    def test_create_multi_provider_limiter(self):
        """Test multi-provider limiter creation"""
        limiter = MultiProviderRateLimiter()
        assert limiter.default_calls_per_minute == 60

    def test_set_provider_limit(self):
        """Test setting provider-specific limits"""
        limiter = MultiProviderRateLimiter()

        limiter.set_provider_limit("openai", calls_per_minute=60)
        limiter.set_provider_limit("claude", calls_per_minute=100)

        assert "openai" in limiter.limiters
        assert "claude" in limiter.limiters

    def test_get_limiter_creates_default(self):
        """Test automatic default limiter creation"""
        limiter = MultiProviderRateLimiter()

        # Should create default limiter
        provider_limiter = limiter.get_limiter("new_provider")
        assert provider_limiter is not None
        assert provider_limiter.capacity == 60

    def test_acquire_per_provider(self):
        """Test per-provider token acquisition"""
        limiter = MultiProviderRateLimiter()

        limiter.set_provider_limit("openai", calls_per_minute=60, burst_size=1)
        limiter.set_provider_limit("claude", calls_per_minute=60, burst_size=1)

        # Each provider has independent limits
        assert limiter.acquire("openai", block=False) is True
        assert limiter.acquire("claude", block=False) is True

        # Each provider can be exhausted independently
        assert limiter.acquire("openai", block=False) is False
        assert limiter.acquire("claude", block=False) is False

    def test_get_stats_single_provider(self):
        """Test getting stats for single provider"""
        limiter = MultiProviderRateLimiter()
        limiter.set_provider_limit("openai", calls_per_minute=60)

        limiter.acquire("openai")

        stats = limiter.get_stats("openai")
        assert "openai" in stats
        assert stats["openai"]["total_requests"] == 1

    def test_get_stats_all_providers(self):
        """Test getting stats for all providers"""
        limiter = MultiProviderRateLimiter()

        limiter.set_provider_limit("openai", calls_per_minute=60)
        limiter.set_provider_limit("claude", calls_per_minute=60)

        limiter.acquire("openai")
        limiter.acquire("claude")

        stats = limiter.get_stats()
        assert "openai" in stats
        assert "claude" in stats

    def test_reset_single_provider(self):
        """Test resetting single provider"""
        limiter = MultiProviderRateLimiter()
        limiter.set_provider_limit("openai", calls_per_minute=60, burst_size=1)

        # Exhaust
        limiter.acquire("openai")
        assert limiter.acquire("openai", block=False) is False

        # Reset
        limiter.reset("openai")

        # Should work again
        assert limiter.acquire("openai", block=False) is True

    def test_reset_all_providers(self):
        """Test resetting all providers"""
        limiter = MultiProviderRateLimiter()

        limiter.set_provider_limit("openai", calls_per_minute=60, burst_size=1)
        limiter.set_provider_limit("claude", calls_per_minute=60, burst_size=1)

        # Exhaust both
        limiter.acquire("openai")
        limiter.acquire("claude")

        # Reset all
        limiter.reset()

        # Both should work again
        assert limiter.acquire("openai", block=False) is True
        assert limiter.acquire("claude", block=False) is True
