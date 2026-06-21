from src.rag.steps.query_translation import translate_query,_generate_variants,_hyde,_step_back
from src.rag.models import PipelineConfig,QueryTranslationConfig
class TestTranslateQuery:
    async def test_no_translation_returns_original(self,base_config):
        query,trace = await translate_query(query="what is attention",config=base_config)
        assert query == "what is attention"
        assert trace["original_query"] == "what is attention"
        assert "hypothetical_doc" not in trace
        assert "query_variants" not in trace
        assert "step_back_query" not in trace

    async def test_hyde_returns_string(self,hyde_config):
        query,trace = await translate_query(query="what is attention",config=hyde_config)
        assert isinstance(query,str)
        assert "hypothetical_doc" in trace
        assert trace["hypothetical_doc"] == "This is a mock response."

    async def test_multiquery_returns_list_with_original(self,multi_query_config):
        query,trace = await translate_query(query="what is attention",config=multi_query_config)
        assert isinstance(query,list)
        assert "query_variants" in trace
        assert "what is attention" in query

    async def test_stepback_returns_string(self,step_back_config):
        query,trace = await translate_query(query="what is attention",config=step_back_config)
        assert isinstance(query,str)
        assert "step_back_query" in trace
    
    async def test_trace_always_has_original_query(self,hyde_config):
        _,trace = await translate_query(query="what is attention",config=hyde_config)
        assert "original_query" in trace

    async def test_hyde_takes_priority_over_multiquery(self):
        config = PipelineConfig(
            name="test",
            query_translation=QueryTranslationConfig(multi_query=True,hyde=True)
        )
        query,trace = await translate_query(query="what is attention",config=config)
        assert isinstance(query,str)
        assert "hypothetical_doc" in trace
        assert "query_variants" not in trace

    async def test_empty_query_still_translates(self,hyde_config):
        query,trace = await translate_query(query="",config=hyde_config)
        assert isinstance(query,str)

class TestGenerateVariants:

    async def test_returns_list(self,base_config):
        variants = await _generate_variants(query="what is attention",config=base_config)
        assert isinstance(variants,list)

    async def test_all_items_are_strings(self,base_config):
        variants = await _generate_variants(query="what is attention",config=base_config)
        assert all(isinstance(v,str) for v in variants)

    async def test_no_empty_strings(self,base_config):
        variants = await _generate_variants(query="what is attenion",config=base_config)
        assert "" not in variants
        assert all(v.strip() for v in variants)

class TestHyde:
    async def test_returns_string(self,base_config):
        result = await _hyde(query="what is attention",config=base_config)
        assert isinstance(result,str)
        assert len(result) > 0

class TestStepBack:
    async def test_returns_string(self,base_config):
        result = await _step_back(query="what is attention",config=base_config)
        assert isinstance(result,str)
        assert len(result) > 0
    