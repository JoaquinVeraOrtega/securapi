from ..security.rateLimiting import RateLimiterMiddleware
import time



class TestRateLimiterUnit:
    def test_rate_limiter_allows_requests_within_limit(self):
        rate_limiter = RateLimiterMiddleware(max_requests=5, time_window=10)
        ip_address = "127.0.0.1"
        for _ in range(5):
            assert rate_limiter.new_request_allowed(ip_address) is True
        assert rate_limiter.is_ip_suspected(ip_address) is False

    def test_rate_limiter_blocks_requests_exceeding_limit(self):
        rate_limiter = RateLimiterMiddleware(max_requests=3, time_window=10)
        ip_address = "127.0.0.1"
        for _ in range(3):
            assert rate_limiter.new_request_allowed(ip_address) is True
        assert rate_limiter.new_request_allowed(ip_address) is False
        assert rate_limiter.is_ip_suspected(ip_address) is True

    def test_rate_limiter_resets_after_time_window(self):
        rate_limiter = RateLimiterMiddleware(max_requests=2, time_window=2)
        ip_address = "127.0.0.1"
        for _ in range(2):
            assert rate_limiter.new_request_allowed(ip_address) is True
        assert rate_limiter.new_request_allowed(ip_address) is False
        time.sleep(3)  # Wait for time window to expire

        assert rate_limiter.new_request_allowed(ip_address) is True
        assert rate_limiter.is_ip_suspected(ip_address) is False
