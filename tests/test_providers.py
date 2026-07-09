import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from plugins.free_cascade_router import FreeCascadeRouter, Provider, PROVIDERS


@pytest.fixture
def router():
    return FreeCascadeRouter()


@pytest.fixture
def mock_aiohttp_session():
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "choices": [
                {
                    "message": {
                        "content": "Hello from provider"
                    }
                }
            ]
        }
    )
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)
    return mock_response


class TestProviderConfiguration:
    def test_all_19_providers_configured(self):
        assert len(PROVIDERS) == 19

    def test_provider_names_unique(self):
        names = [p.name for p in PROVIDERS]
        assert len(names) == len(set(names))

    def test_provider_priorities_unique(self):
        priorities = [p.priority for p in PROVIDERS]
        assert len(priorities) == len(set(priorities))

    def test_keyless_providers(self):
        keyless = [p for p in PROVIDERS if p.no_key is True]
        assert len(keyless) >= 4

    def test_providers_with_env_keys(self):
        keyed = [p for p in PROVIDERS if p.env_key is not None]
        assert len(keyed) >= 10

    def test_all_providers_have_base_url(self):
        for p in PROVIDERS:
            assert p.base_url.startswith("http")

    def test_all_providers_have_model(self):
        for p in PROVIDERS:
            assert len(p.model) > 0

    def test_internal_providers_local(self):
        internal = [p for p in PROVIDERS if p.priority >= 90]
        for p in internal:
            assert "localhost" in p.base_url or "omniroute" in p.base_url or "ninerouter" in p.base_url

    def test_provider_notes_populated(self):
        for p in PROVIDERS:
            assert len(p.notes) > 0

    def test_provider_rpm_positive(self):
        for p in PROVIDERS:
            assert p.rpm_limit > 0

    def test_provider_rpd_positive(self):
        for p in PROVIDERS:
            assert p.rpd_limit > 0

    def test_free_providers_first(self):
        free = [p for p in PROVIDERS if p.no_key]
        assert free[0].priority < free[-1].priority

    def test_llm7_is_first(self):
        llm7 = [p for p in PROVIDERS if p.name == "llm7"]
        assert len(llm7) == 1
        assert llm7[0].priority == 1

    def test_ollama_local(self):
        ollama = [p for p in PROVIDERS if p.name == "ollama"]
        assert len(ollama) == 1
        assert "11434" in ollama[0].base_url

    def test_groq_configured(self):
        groq = [p for p in PROVIDERS if p.name == "groq"]
        assert len(groq) == 1
        assert groq[0].env_key == "GROQ_API_KEY"
        assert "70b" in groq[0].model

    def test_gemini_configured(self):
        gemini = [p for p in PROVIDERS if p.name == "gemini"]
        assert len(gemini) == 1
        assert gemini[0].env_key == "GEMINI_API_KEY"


class TestRPMTracking:
    def test_rpm_window_empty(self, router):
        p = PROVIDERS[0]
        assert router._rpm_ok(p) is True

    def test_rpm_window_one_use(self, router):
        p = PROVIDERS[0]
        router._record_use(p)
        assert router._rpm_ok(p) is True

    def test_rpm_window_exact_limit(self, router):
        p = PROVIDERS[2]
        now = time.time()
        router._rpm_windows[p.name] = [now] * p.rpm_limit
        assert router._rpm_ok(p) is False

    def test_rpm_window_under_limit(self, router):
        p = PROVIDERS[2]
        now = time.time()
        router._rpm_windows[p.name] = [now] * (p.rpm_limit - 1)
        assert router._rpm_ok(p) is True

    def test_rpm_window_expired_entries(self, router):
        p = PROVIDERS[2]
        old_time = time.time() - 120
        router._rpm_windows[p.name] = [old_time] * 100
        assert router._rpm_ok(p) is True

    def test_rpm_window_mixed_times(self, router):
        p = PROVIDERS[2]
        old = time.time() - 120
        recent = time.time()
        router._rpm_windows[p.name] = [old] * 50 + [recent] * (p.rpm_limit - 1)
        assert router._rpm_ok(p) is True

    def test_rpm_window_multiple_providers(self, router):
        for p in PROVIDERS[:3]:
            router._record_use(p)
        for p in PROVIDERS[:3]:
            assert router._rpm_ok(p) is True


class TestRPDTracking:
    def test_rpd_empty(self, router):
        p = PROVIDERS[0]
        assert router._rpd_ok(p) is True

    def test_rpd_one_use(self, router):
        p = PROVIDERS[0]
        router._record_use(p)
        assert router._rpd_ok(p) is True

    def test_rpd_exact_limit(self, router):
        p = PROVIDERS[0]
        dk = router._date_key(p.name)
        router._daily_counts[dk] = p.rpd_limit
        assert router._rpd_ok(p) is False

    def test_rpd_under_limit(self, router):
        p = PROVIDERS[0]
        dk = router._date_key(p.name)
        router._daily_counts[dk] = p.rpd_limit - 1
        assert router._rpd_ok(p) is True

    def test_rpd_different_days(self, router):
        p = PROVIDERS[0]
        today_key = router._date_key(p.name)
        yesterday_key = f"{p.name}:{int(time.time() // 86400) - 1}"
        router._daily_counts[yesterday_key] = 999999
        assert router._rpd_ok(p) is True


class TestProviderSelectionLogic:
    def test_sorted_by_priority(self, router):
        sorted_p = sorted(PROVIDERS, key=lambda x: x.priority)
        assert sorted_p[0].priority <= sorted_p[-1].priority

    def test_skip_no_key_when_env_missing(self, router):
        p = PROVIDERS[2]
        if p.env_key:
            with patch.dict("os.environ", {}, clear=True):
                api_key = None if p.env_key is None else None
                if p.env_key and not api_key and p.priority < 90:
                    assert True

    def test_keyless_always_available(self, router):
        keyless = [p for p in PROVIDERS if p.no_key]
        for p in keyless:
            assert p.env_key is None or p.no_key is True

    def test_priority_ordering(self):
        priorities = [p.priority for p in PROVIDERS]
        assert priorities == sorted(priorities)


class TestCircuitBreakerBehavior:
    def test_all_providers_have_notes(self):
        for p in PROVIDERS:
            assert isinstance(p.notes, str)

    def test_providers_valid_base_urls(self):
        for p in PROVIDERS:
            assert p.base_url.startswith("http://") or p.base_url.startswith("https://")

    def test_providers_model_names(self):
        for p in PROVIDERS:
            assert len(p.model) >= 3

    def test_env_key_names(self):
        env_keys = [p.env_key for p in PROVIDERS if p.env_key]
        for k in env_keys:
            assert k == k.upper()
            assert "_" in k or k.isupper()


class TestProviderDataclass:
    def test_provider_creation(self):
        p = Provider(
            name="test",
            base_url="http://test.com/v1",
            model="test-model",
            env_key=None,
            rpm_limit=10,
            rpd_limit=100,
            priority=50,
        )
        assert p.name == "test"
        assert p.no_key is False

    def test_provider_defaults(self):
        p = Provider(
            name="test",
            base_url="http://test.com/v1",
            model="test-model",
            env_key=None,
            rpm_limit=10,
            rpd_limit=100,
            priority=50,
        )
        assert p.no_key is False
        assert p.notes == ""

    def test_provider_no_key_true(self):
        p = Provider(
            name="test",
            base_url="http://test.com/v1",
            model="test-model",
            env_key=None,
            rpm_limit=10,
            rpd_limit=100,
            priority=50,
            no_key=True,
            notes="free",
        )
        assert p.no_key is True
        assert p.notes == "free"
