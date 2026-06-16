from src.rag.models import PipelinePresets
from src.rag.pipeline import run_pipeline

async def test_baseline():
    config = PipelinePresets.baseline(name="test")
    result,answer = await run_pipeline(config=config,query="what is attention")
    assert answer
    assert len(result.chunks)>0
    print(answer[:100])


async def test_rag_fusion():
    config = PipelinePresets.rag_fusion(name="test")
    result,answer = await run_pipeline(config=config,query="what is attention")
    assert answer
    assert len(result.chunks)>0
    print(answer[:100])


async def test_hyde_hybrid():
    config = PipelinePresets.hyde_hybrid(name="test")
    result,answer = await run_pipeline(config=config,query="what is attention")
    assert answer
    assert len(result.chunks)>0
    print(answer[:100])

async def test_rag_hyde():
    config = PipelinePresets.rag_hyde(name="test")
    result,answer = await run_pipeline(config=config,query="what is attention")
    assert answer
    assert len(result.chunks)>0
    print(answer[:100])


async def test_parent_rerank():
    config = PipelinePresets.parent_rerank(name="test")
    result,answer = await run_pipeline(config=config,query="what is attention")
    assert answer
    assert len(result.chunks)>0
    print(answer[:100])

async def test_rag_multiquery():
    config = PipelinePresets.rag_hyde(name="test")
    result,answer = await run_pipeline(config=config,query="what is attention")
    assert answer
    assert len(result.chunks)>0
    print(answer[:100])

async def test_rag_step_back():
    config = PipelinePresets.rag_step_back(name="test")
    result,answer = await run_pipeline(config=config,query="what is attention")
    assert answer
    assert len(result.chunks)>0
    print(answer[:100])