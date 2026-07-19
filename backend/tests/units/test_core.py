import asyncio
import gc
import uuid
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from src.rag import core
from src.rag.models import PipelineConfig


def make_config(provider: str, llm: str = "claude-opus-4-8") -> PipelineConfig:
    return PipelineConfig(
        id=uuid.uuid4(),
        name="test-get-llm",
        created_at=datetime.now(),
        status="ready",
        generation={"llm": llm, "provider": provider},
    )


@pytest.fixture
def anthropic_config():
    return make_config("anthropic")


@pytest.fixture(autouse=True)
def fresh_chat_anthropic(mocker):
    # conftest's mock_get_llm patches ChatGoogleGenerativeAI to one shared
    # instance; the identity checks here need a distinct instance per
    # construction, so patch the Anthropic path with a factory instead.
    return mocker.patch("src.rag.core.ChatAnthropic", side_effect=lambda **kwargs: MagicMock())


@pytest.fixture(autouse=True)
def clean_llm_cache():
    yield
    # The session-scoped pytest event loop outlives each test, so entries made
    # under it (with this file's mocked clients) must not leak to other tests.
    core._llm_per_loop.clear()


class TestGetLlmPerLoopCache:
    async def test_reuses_client_within_one_loop(self, anthropic_config):
        assert core.get_llm(anthropic_config) is core.get_llm(anthropic_config)

    def test_new_loop_gets_fresh_client(self, anthropic_config):
        # Regression: a client cached across asyncio.run() calls carries httpx
        # connections bound to a closed loop and fails with "Connection error."
        async def grab():
            return core.get_llm(anthropic_config)

        assert asyncio.run(grab()) is not asyncio.run(grab())

    def test_no_running_loop_never_caches(self, anthropic_config):
        assert core.get_llm(anthropic_config) is not core.get_llm(anthropic_config)

    def test_cache_entry_dies_with_its_loop(self, anthropic_config):
        entries_before = len(core._llm_per_loop)

        async def grab():
            core.get_llm(anthropic_config)

        asyncio.run(grab())
        gc.collect()
        assert len(core._llm_per_loop) == entries_before

    def test_unknown_provider_raises(self):
        config = make_config("huggingface", llm="some-hf-model")
        with pytest.raises(ValueError, match="Unknown generation provider"):
            core.get_llm(config)
