"""
D-10: Security Tests — Rate Limiting, IP Filter, Login Throttle, Security Headers
"""
import pytest
import time
from api.security import RateLimiter, LoginThrottle, IPFilter


# ============================================================
# Rate Limiter Tests
# ============================================================
class TestRateLimiter:
    def test_allow_within_limit(self):
        rl = RateLimiter()
        for _ in range(5):
            assert rl.allow("test-key", max_tokens=5, refill_rate=0.0) is True
        # 6th request should be denied
        assert rl.allow("test-key", max_tokens=5, refill_rate=0.0) is False

    def test_different_keys_independent(self):
        rl = RateLimiter()
        for _ in range(5):
            rl.allow("key-a", max_tokens=5, refill_rate=0.0)
        assert rl.allow("key-a", max_tokens=5, refill_rate=0.0) is False
        # key-b should still have tokens
        assert rl.allow("key-b", max_tokens=5, refill_rate=0.0) is True

    def test_remaining_count(self):
        rl = RateLimiter()
        rl.allow("test", max_tokens=10, refill_rate=0.0)
        assert rl.remaining("test") == 9

    def test_remaining_unknown_key(self):
        rl = RateLimiter()
        assert rl.remaining("nonexistent") == 0

    def test_cleanup(self):
        rl = RateLimiter()
        rl.allow("old-key", max_tokens=5, refill_rate=0.0)
        # Simulate old timestamp
        rl._buckets["old-key"]["last_refill"] = time.monotonic() - 7200
        rl.cleanup(max_age_seconds=3600)
        assert "old-key" not in rl._buckets

    def test_refill_restores_tokens(self):
        rl = RateLimiter()
        # Exhaust all tokens
        for _ in range(3):
            rl.allow("refill-test", max_tokens=3, refill_rate=100.0)
        assert rl.allow("refill-test", max_tokens=3, refill_rate=100.0) is False
        # With high refill rate, next call should refill
        time.sleep(0.05)
        assert rl.allow("refill-test", max_tokens=3, refill_rate=100.0) is True


# ============================================================
# Login Throttle Tests
# ============================================================
class TestLoginThrottle:
    def test_not_locked_initially(self):
        lt = LoginThrottle(max_failures=3, lockout_seconds=60)
        assert lt.is_locked("1.2.3.4") is False

    def test_lock_after_max_failures(self):
        lt = LoginThrottle(max_failures=3, lockout_seconds=60)
        for _ in range(3):
            lt.record_failure("1.2.3.4")
        assert lt.is_locked("1.2.3.4") is True

    def test_success_resets_failures(self):
        lt = LoginThrottle(max_failures=3, lockout_seconds=60)
        lt.record_failure("1.2.3.4")
        lt.record_failure("1.2.3.4")
        lt.record_success("1.2.3.4")
        assert lt.is_locked("1.2.3.4") is False

    def test_lockout_expires(self):
        lt = LoginThrottle(max_failures=2, lockout_seconds=0)  # Immediate expiry
        lt.record_failure("1.2.3.4")
        lt.record_failure("1.2.3.4")
        # Lockout should expire immediately
        time.sleep(0.01)
        assert lt.is_locked("1.2.3.4") is False

    def test_different_ips_independent(self):
        lt = LoginThrottle(max_failures=2, lockout_seconds=60)
        lt.record_failure("1.1.1.1")
        lt.record_failure("1.1.1.1")
        assert lt.is_locked("1.1.1.1") is True
        assert lt.is_locked("2.2.2.2") is False

    def test_get_stats(self):
        lt = LoginThrottle(max_failures=2, lockout_seconds=60)
        lt.record_failure("1.1.1.1")
        stats = lt.get_stats()
        assert stats["tracked_ips"] >= 1
        assert "locked_ips" in stats


# ============================================================
# IP Filter Tests
# ============================================================
class TestIPFilter:
    def test_default_allows_all(self):
        f = IPFilter()
        assert f.is_allowed("1.2.3.4") is True
        assert f.is_allowed("10.0.0.1") is True

    def test_whitelist_blocks_unknown(self):
        f = IPFilter()
        f.configure(whitelist_csv="10.0.0.1,10.0.0.2")
        assert f.is_allowed("10.0.0.1") is True
        assert f.is_allowed("10.0.0.2") is True
        assert f.is_allowed("192.168.1.1") is False

    def test_blacklist_blocks_specific(self):
        f = IPFilter()
        f.configure(blacklist_csv="10.0.0.99")
        assert f.is_allowed("10.0.0.1") is True
        assert f.is_allowed("10.0.0.99") is False

    def test_blacklist_overrides_whitelist(self):
        f = IPFilter()
        f.configure(whitelist_csv="10.0.0.1,10.0.0.2", blacklist_csv="10.0.0.1")
        assert f.is_allowed("10.0.0.1") is False
        assert f.is_allowed("10.0.0.2") is True

    def test_empty_strings_ignored(self):
        f = IPFilter()
        f.configure(whitelist_csv="", blacklist_csv="")
        assert f.is_allowed("1.2.3.4") is True

    def test_get_config(self):
        f = IPFilter()
        f.configure(whitelist_csv="10.0.0.1")
        config = f.get_config()
        assert config["mode"] == "whitelist"
        assert "10.0.0.1" in config["whitelist"]

    def test_open_mode_config(self):
        f = IPFilter()
        config = f.get_config()
        assert config["mode"] == "open"
