import pytest
from src.rag.steps.retrieval import retrieve
from langchain_core.documents import Document


pytestmark = pytest.mark.asyncio

class TestRetrieve:
    async def test_returns_docs_and_trace(self,base_config):
        docs , trace = await retrieve(query="what is attention",config=base_config)
        assert isinstance(docs,list)
        assert isinstance(trace,dict)

    async def test_all_returned_items_are_documents(self,base_config):
        docs,_ = await retrieve(query="what is attention",config=base_config)
        assert all(isinstance(doc,Document) for doc in docs)

    async def test_trace_has_retrieved_chunks(self,base_config):
        _, trace = await retrieve(query="what is attention",config=base_config)
        assert "retrieved_chunks" in trace

    async def test_retrieved_chunks_have_required_fields(self,base_config):
        _,trace = await retrieve(query="what is attention",config=base_config)
        for chunk in trace["retrieved_chunks"]:
            assert "content" in chunk
            assert "score" in chunk
            assert "source" in chunk
            assert "page" in chunk

    async def test_scores_stored_in_doc_metadata(self,base_config):
        docs,_ = await retrieve(query="what is attention",config=base_config)
        assert all("score" in doc.metadata for doc in docs)

    async def test_multiquery_returns_flat_list(self,multi_query_config):
        docs,trace = await retrieve(query=["query 1","query 2","query 3"],config=multi_query_config)
        assert isinstance(docs,list)
        assert all(isinstance(doc,Document) for doc in docs)
        assert "raw_results" in trace

    async def test_multiquery_tags_retrieved_by(self,multi_query_config):
        docs,trace = await retrieve(["query 1","query 2"],config=multi_query_config)
        assert all("retrieved_by" in doc.metadata for doc in docs)
    
    async def test_parent_doc_retrieve_called(self,parent_rerank_config):
        docs,trace = await retrieve("what is attention",config=parent_rerank_config)
        assert isinstance(docs,list)

