from src.rag.models import PipelineConfig,ChunkTrace,PipelineResult
import time
from src.rag.steps.query_translation import translate_query
from src.rag.steps.retrieval import retrieve
from src.rag.steps.post_retrieval import post_retrieval
from src.rag.steps.generation import generate
async def run_pipeline(config:PipelineConfig,query:str)->tuple[PipelineResult,str]:
    full_trace = {}
    latency = {}

    # step 1 — query translation
    t0 = time.time()
    search_query,translation_trace = await translate_query(query=query,config=config)
    latency["query_translation_ms"] = int((time.time() - t0)*1000)
    full_trace.update(translation_trace)
    print("translation_trace:", translation_trace)
    print("search_query:", search_query[:100])

    # step 2 — retrieval
    t0 = time.time()
    docs, retrieval_trace = await retrieve(query=search_query,config=config)
    latency["retrieval_ms"] = int((time.time() - t0)*1000)
    full_trace.update(retrieval_trace)

    # step 3 — post_retrieval
    t0 = time.time()
    docs, post_retrieval_trace = await post_retrieval(trace=full_trace,query=query,docs=docs,config=config)
    latency["post_retrieval_ms"] = int((time.time() - t0)*1000)
    full_trace.update(post_retrieval_trace)

    # step 4 — generation
    t0 = time.time()
    answer,generation_trace = await generate(query=query,docs=docs,config=config)
    latency["generation_ms"] = int((time.time() - t0)*1000)
    full_trace.update(generation_trace)
    
    pipeline_result = PipelineResult(
        pipeline_id=config.id,
        query=query,
        translated_query=full_trace.get("hypothetical_doc") or full_trace.get("step_back_query"),
        query_variants= full_trace.get("query_variants") or None,
        chunks=[ChunkTrace(
            content=c.get("content"),
            source=c.get("source"),
            raw_score=c.get("score"),
            rerank_score= next((r["rerank_score"] for r in full_trace.get("reranked_chunks",[]) if r.get("content") and r.get("content") == c.get("content")),None)
        ) 
    for c in full_trace.get("retrieved_chunks",[])],
    answer=answer,
    latency=latency
    )
    return pipeline_result,answer


 





