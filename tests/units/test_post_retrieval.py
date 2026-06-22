import pytest
from src.rag.steps.post_retrieval import _deduplicate,post_retrieval,_rrf_score,_reorder
from langchain_core.documents import Document


pytestmark = pytest.mark.asyncio

class TestDeduplicate:
    def test_removes_duplicates(self,duplicate_docs):
        result = _deduplicate(duplicate_docs)
        assert len(result) == len(duplicate_docs)//2

    def test_preserves_first_occurrence_order(self,duplicate_docs,fake_docs):
        result = _deduplicate(duplicate_docs)
        assert result[0].page_content == fake_docs[0].page_content

    def test_empty_list_returns_empty(self):
        result = _deduplicate([])
        assert result == []

    def test_no_duplicates_unchanged(self,fake_docs):
        result = _deduplicate(fake_docs)
        assert result == fake_docs


class TestPostRetrieval:

    async def test_no_reranker_returns_docs_unchanged(self,base_config,fake_docs):
        docs,trace = await post_retrieval(
            config=base_config,
            trace={"retrieval": {}, "translation": {}},
            query= "what is attention",
            docs=fake_docs
            )
        assert len(docs) == len(fake_docs)
        assert trace["doc_count_after_dedup"] == len(fake_docs)
    
    async def test_dedup_count_in_trace(self,base_config,duplicate_docs):
        _,trace = await post_retrieval(
            config=base_config,
            trace={"retrieval": {}, "translation": {}},
            query= "what is attention",
            docs=duplicate_docs
            )
        assert trace["doc_count_after_dedup"] == len(duplicate_docs)//2

    async def test_cross_encoder_adds_reranked_chunks_to_trace(self,cross_encoder_config,fake_docs):
        
        docs, trace = await post_retrieval(
            config=cross_encoder_config,
            trace={"retrieval": {}, "translation": {}},
            query= "what is attention",
            docs=fake_docs
        )
        assert "reranked_chunks" in trace
        assert len(docs) <= cross_encoder_config.post_retrieval.top_n

    async def test_cross_encoder_scores_stored_in_metadata(self,cross_encoder_config,fake_docs):
        docs, _ = await post_retrieval(
            config=cross_encoder_config,
            trace={"retrieval": {}, "translation": {}},
            query= "what is attention",
            docs=fake_docs
        )
        assert all("rerank_score" in doc.metadata for doc in docs)
    
    async def test_rrf_applied_when_raw_results_present(slef,fusion_config,fake_docs):
        raw_results = [fake_docs[:2], fake_docs[1:]]
        docs, trace = await post_retrieval(
            config=fusion_config,
            trace={"retrieval": {}, "translation": {},"raw_results": raw_results},
            query= "what is attention",
            docs=fake_docs
        )

        assert trace.get("rrf_applied") is True
        assert isinstance(docs,list)

    async def test_rrf_skipped_without_raw_results(self,fusion_config,fake_docs):
        _, trace = await post_retrieval(
            config=fusion_config,
            trace={"retrieval": {}, "translation": {}, "raw_results": {}},
            query= "what is attention",
            docs=fake_docs
        )

        assert trace.get("rrf_applied") is  not True
    
    async def test_reorder_applied_when_configured(self,reorder_config,fake_docs):
        _, trace = await post_retrieval(
            config=reorder_config,
            trace={"retrieval": {}, "translation": {},"raw_results": {}},
            query= "what is attention",
            docs=fake_docs
        )

        assert trace["reorder_applied"] is True

    async def test_reorder_not_applied_when_not_configured(self,base_config,fake_docs):
        _, trace = await post_retrieval(
            config=base_config,
            trace={"retrieval": {"raw_results": {}}, "translation": {}},
            query= "what is attention",
            docs=fake_docs
        )
        assert "reorder_applied" not in trace

class TestRRFScore:

    def test_returns_list_of_documents(self,fake_docs):

        docs = _rrf_score([fake_docs + list(reversed(fake_docs))],top_n=3)
        
        assert isinstance(docs,list)
        assert all(isinstance(doc,Document) for doc in docs)

    def test_top_n_limits_results(self,fake_docs):
        docs = _rrf_score([fake_docs],top_n=1)
        assert len(docs) <= 1

    def test_deduplicates_across_lists(self,fake_docs):
        docs = _rrf_score([fake_docs,fake_docs],top_n=10)
        contents = [d.page_content for d in docs]
        assert len(contents) == len(set(contents))

    def test_empty_input_returns_empty(self):
        docs = _rrf_score([],top_n=3)
        assert docs == []

    def test_single_list_returns_top_n_by_rank(self,fake_docs):
        docs = _rrf_score([fake_docs],top_n=2)
        assert docs[0].page_content == fake_docs[0].page_content


class TestReorder:
    def test_preserves_all_docs(self,fake_docs):
        docs = _reorder(fake_docs)
        assert set(d.page_content for d in docs) == set(d.page_content for d in fake_docs)

    def test_same_length_as_input(self,fake_docs):
        docs = _reorder(fake_docs)
        assert len(docs) == len(fake_docs)

    def test_single_doc_unchanged(self,fake_docs):
        docs = _reorder([fake_docs[0]])
        assert docs[0].page_content == fake_docs[0].page_content

    def test_empty_list_returns_empty(self):
        docs = _reorder([])
        assert len(docs) == 0