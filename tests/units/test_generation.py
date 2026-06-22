import pytest
from src.rag.steps.generation import generate,format_docs

pytestmark = pytest.mark.asyncio


class TestGenerate:

    async def test_returns_answer_string(self,base_config,fake_docs):
        answer,_ = await generate(query="what is attention",docs=fake_docs,config=base_config)

        assert isinstance(answer,str)
        assert len(answer)>0

    async def test_returns_trace_dict(self,base_config,fake_docs):
        _,trace = await generate(query="what is attention",docs=fake_docs,config=base_config)

        assert isinstance(trace,dict)

    async def test_trace_has_context(self,base_config,fake_docs):
        _,trace = await generate(query="what is attention",docs=fake_docs,config=base_config)

        assert "context_sent_to_llm" in trace
        assert isinstance(trace["context_sent_to_llm"],str)

    async def test_context_contains_doc_content(self,base_config,fake_docs):
        _,trace = await generate(query="what is attention",docs=fake_docs,config=base_config)
        assert fake_docs[0].page_content in trace["context_sent_to_llm"]

    async def test_empty_docs_handled_gracefully(self,base_config):
        asnswer,trace = await generate(query="what is attention",docs=[],config=base_config)
        assert isinstance(asnswer,str)
        assert trace["context_sent_to_llm"] == ""

class TestFormatDocs:
    def test_joins_with_double_newline(self,fake_docs):
        result = format_docs(fake_docs)
        assert "\n\n" in result

    def test_all_content_included(self,fake_docs):
        result = format_docs(fake_docs)
        for doc in fake_docs:
            assert doc.page_content in result
        
    def test_empty_returns_empty_string(self):
        assert format_docs([]) == ""
    
    def test_single_doc_no_separator(self,fake_docs):
        assert format_docs([fake_docs[0]]) == fake_docs[0].page_content

    
