import pytest
from src.rag.pipeline import run_pipeline
from unittest.mock import AsyncMock, patch
from src.rag.models import PipelineResult

pytestmark = pytest.mark.asyncio


class TestRunPipeline:

    async def test_returns_pipeline_result_and_answer(self,base_config):
        result,answer = await run_pipeline(config=base_config,query="what is attention")

        assert isinstance(result,PipelineResult)
        assert answer == "This is a mock response."
        assert result.answer == "This is a mock response."

    async def test_latency_has_all_stages(self,base_config):
        result,_ = await run_pipeline(config=base_config,query="what is attention")
        assert "query_translation_ms" in result.latency
        assert "retrieval_ms" in result.latency
        assert "post_retrieval_ms" in result.latency
        assert "generation_ms" in result.latency

    
    async def test_all_latencies_are_non_negative(self,base_config):
        result,_ = await run_pipeline(config=base_config,query="what is attention")
        assert all(v>=0 for v in result.latency.values())

    async def test_chunks_populated_from_trace(self,base_config):
        result,_ = await run_pipeline(config=base_config,query="what is attention")
        assert len(result.chunks) == 3
        assert result.chunks[0].content == "Chunk 1"
        assert result.chunks[1].content == "Chunk 2"
        assert result.chunks[2].content == "Chunk 3"

    async def test_chunk_scores_populated(self,base_config):
        result,_ = await run_pipeline(config=base_config,query="what is attention")
        assert result.chunks[0].raw_score == 0.95
        assert result.chunks[1].raw_score == 0.88
        assert result.chunks[2].raw_score == 0.81

    async def test_translated_query_none_for_baseline(self,base_config):
        result,_ = await run_pipeline(config=base_config,query="what is attention")
        assert result.translated_query is None

    async def test_translated_query_populated_for_hyde(self,hyde_config):
        result,_ = await run_pipeline(config=hyde_config,query="what is attention")
        assert result.translated_query == "This is a mock response."

    async def test_pipeline_id_matches_config(self,base_config):
        result,_ = await run_pipeline(config=base_config,query="what is attention")
        assert result.pipeline_id == base_config.id



    



