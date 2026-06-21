from rag.models import (
    ChunkingConfig,ChunkingStrategy,IndexingConfig,VectorDb,
    PostRetrievalConfig,RerankerConfig,PipelineConfig,
    PipelineStatus,PipelinePresets,ModeConfig)
import pytest
import uuid
from datetime import datetime
import json
class TestChunkingConfig:
    def test_default_values(self):
        config = ChunkingConfig()
        assert config.strategy == ChunkingStrategy.RECURSIVE
        assert config.chunk_size == 500
        assert config.overlap == 50
        assert config.parent_chunk_size is None
        assert config.parent_overlap is None
        assert config.parent_doc == False

    def test_parent_sets_defaults(self):
        config = ChunkingConfig(parent_doc=True)
        assert config.parent_chunk_size == 2000
        assert config.parent_overlap == 200

    def test_parent_doc_false_clears_parent_fields(self):
        config = ChunkingConfig(parent_doc=False,parent_chunk_size=3000,parent_overlap=300)
        assert config.parent_chunk_size is None
        assert config.parent_overlap is None
    
    def test_parent_doc_respects_custom_values(self):
        config = ChunkingConfig(parent_doc=True,parent_chunk_size=3000,parent_overlap=300)
        assert config.parent_chunk_size == 3000
        assert config.parent_overlap == 300

class TestIndexingConfig:
    def test_default_values(self):
        config = IndexingConfig()
        assert config.vector_db == VectorDb.QDRANT
        assert config.embedding_model == "gemini-embedding-001"

class TestPostRetrievalConfig:
    def test_cross_encoder_requires_top_n(self):
        with pytest.raises(ValueError,match="top_n"):
            PostRetrievalConfig(reranker=RerankerConfig.CROSS_ENCODER,top_n=None)

    def test_cross_encoder_top_n_must_be_positive(self):
        with pytest.raises(ValueError,match="top_n"):
            PostRetrievalConfig(reranker=RerankerConfig.CROSS_ENCODER,top_n=-1)
    
    def test_cohere_requires_model(self):
        with pytest.raises(ValueError,match="cohere_model"):
            PostRetrievalConfig(reranker=RerankerConfig.COHERE,cohere_model=None)

    def test_none_reranker_no_validation_errors(self):
        config = PostRetrievalConfig(reranker=RerankerConfig.NONE)
        assert config.reranker == RerankerConfig.NONE
    
class TestPipelineConfig:
    def test_auto_generates_uuid(self):
        config = PipelineConfig(name="test")
        assert isinstance(config.id,uuid.UUID)

    def test_two_configs_have_different_ids(self):
        a = PipelineConfig(name="a")
        b = PipelineConfig(name="b")
        assert a.id != b-id

    def test_default_status_is_draft(self):
        conifg = PipelineConfig(name="test")
        assert conifg.status == PipelineStatus.DRAFT
    
    def test_created_at_is_set(self):
        conifg = PipelineConfig(name="test")
        assert isinstance(conifg.created_at,datetime)

    def test_nested_configs_have_defaults(self):
        config = PipelineConfig(name="test")
        assert config.chunking is not None
        assert config.indexing is not None
        assert config.retrieval is not None
        assert config.post_retrieval is not None
        assert config.generation is not None
        assert config.query_translation is not None
    
    def test_model_dump_is_json_serialisable(self):
        config = PipelineConfig(name="test")
        dumped = config.model_dump(mode="json")
        json.dumps(dumped)


class TestPipelinePresets:
    def test_baseline_uses_dense_retrieval(self):
        config = PipelinePresets.baseline(name="test")
        assert config.retrieval.mode == ModeConfig.DENSE
        assert config.query_translation.hyde is False
        assert config.query_translation.step_back is False
        assert config.query_translation.multi_query is False

    def test_rag_fusion_enables_multiquery_and_rrf(self):
        config = PipelinePresets.rag_fusion(name="test")
        assert config.query_translation.multi_query is True
        assert config.post_retrieval.reranker == RerankerConfig.RECIPROCAL_RANK_FUSION

    def test_hyde_hybrid_enables_hyde_and_hybrid(self):
        config = PipelinePresets.hyde_hybrid(name="test")
        assert config.query_translation.hyde is True
        assert config.retrieval.mode == ModeConfig.HYBRID

    def test_parent_rerank_enables_parent_doc_and_cross_encoder(self):
        config = PipelinePresets.parent_rerank(name="test")
        assert config.chunking.parent_doc is True
        assert config.post_retrieval.reranker == RerankerConfig.CROSS_ENCODER
    
    def test_each_preset_creates_unique_id(self):
        a = PipelinePresets.baseline(name="a")
        b = PipelinePresets.baseline(name="b")

        assert a.id != b.id