
from src.rag.models import PipelineConfig
from langchain_classic.docstore.document import Document
from src.rag.models import RerankerConfig
from src.rag.core import get_cross_encoder,get_cohere_rerank


async def post_retrieval(config:PipelineConfig,trace:dict,query:str,docs:list[Document])->tuple[list[Document],dict]:
    post_trace = {}
    docs = _deduplicate(docs)
    post_trace["doc_count_after_dedup"] = len(docs)

    if config.post_retrieval.reranker == RerankerConfig.RECIPROCAL_RANK_FUSION:
        raw_results = trace["raw_results"]
        if raw_results:
            docs = _rrf_score(all_results=raw_results,top_n=config.post_retrieval.top_n)
            post_trace["rrf_applied"] = True

    elif config.post_retrieval.reranker == RerankerConfig.COHERE:
        docs,scores = _cohere_rerank()
        post_trace["reranked_chunks"] = scores
    
    elif config.post_retrieval.reranker == RerankerConfig.CROSS_ENCODER:
        docs,scores = _cross_encoder_rerank(config,query,docs)
        post_trace["reranked_chunks"] = scores
            
    elif config.post_retrieval.reorder:
        docs = _reorder(docs=docs)
        post_trace["reorder_applied"] = True
    
    return docs,post_trace


    

def _cohere_rerank(config:PipelineConfig,docs:list[Document],query:str)->tuple[list[Document],list[dict]]:
    model = get_cohere_rerank(config)
    reranked = model.rerank(documents=[doc.page_content for doc in docs],query=query,top_n=config.post_retrieval.top_n)
    result_docs = []
    result_scores = []
    for r in reranked:
        doc = docs[r.index]
        score = r.relevance_score
        doc.metadata["rerank_score"] = float(score)
        result_docs.append(doc)
        result_scores.append({
            "content": doc.page_content,
            "rerank_score":float(score),
            "source": doc.metadata.get("source"),
            "page": doc.metadata.get("page"),
            "retrieved_by": doc.metadata.get("retrieved_by"),
        })

    return result_docs,result_scores


def _cross_encoder_rerank(config:PipelineConfig,query:str,docs:list[Document])->tuple[list[Document],list[dict]]:
    model = get_cross_encoder(config)
    pairs = [(query,doc.page_content) for doc in docs]
    scores = model.score(pairs)
    scored = sorted(zip(scores,docs),key=lambda x:x[0],reverse=True)

    result_docs = []
    result_scores = []
    for score,doc in scored[:config.post_retrieval.top_n]:
        doc.metadata["rerank_score"] = float(score)
        result_docs.append(doc)
        result_scores.append({
            "content": doc.page_content,
            "rerank_score":float(score),
            "source": doc.metadata.get("source"),
            "page": doc.metadata.get("page"),
            "retrieved_by": doc.metadata.get("retrieved_by"),
        })
    return result_docs,result_scores

def _reorder(docs:list)->list:
    reordered = []
    for i,doc in enumerate(docs):
        if i % 2 == 0:
            reordered.append(doc)
        else:
            reordered.insert(0,doc)
    return reordered

def _deduplicate(all_result:list[Document])->list[Document]:
    seen = set()
    unique = []
    for doc in all_result:
        if doc.page_content not in seen:
            seen.add(doc.page_content)
            unique.append(doc)
    return unique




def _rrf_score(all_results:list[list],top_n:int=5,k:int=60)->list:
    scores: dict[str, float] = {}
    doc_map: dict[str, Document] = {}
    for docs in all_results:
        for rank, doc in enumerate(docs):
            key = doc.page_content
            scores[key] = scores.get(key, 0) + 1 / (rank + k)
            doc_map[key] = doc
    # return top_n sorted by score
    sorted_keys = sorted(scores, key=lambda x: scores[x], reverse=True)
    return [doc_map[k] for k in sorted_keys[:top_n]]
    