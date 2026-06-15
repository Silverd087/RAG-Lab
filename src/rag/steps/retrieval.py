from rag.core import get_vectorstore
from rag.models import PipelineConfig
from rag.models import ModeConfig
from config import settings
from rag.core import get_parent_doc_retriever, get_embeddings
from langchain_classic.docstore.document import Document
import asyncio

async def retrieve(query:str|list,config:PipelineConfig)-> tuple[list,dict]:
    trace = {}

    if isinstance(query,list):
        vectorstore = get_vectorstore(config)

        all_docs = await asyncio.gather(
        *[_standard_retrieve(q, config) for q in query]
        )
        for query_variant, docs in zip(query, all_docs):
            for doc in docs:
                doc.metadata["retrieved_by"] = query_variant
        trace["raw_results"] = list(all_docs)
        docs = [doc for results in all_docs for doc in results]
        return docs,trace
    
    elif config.chunking.parent_doc:
        docs = await _parent_doc_retrieve(query, config)
    elif config.retrieval.mode == ModeConfig.MMR:
        docs = await _mmr_doc_retrieve(query,config)
    else:
        docs = await _standard_retrieve(query,config)

    trace["retrieved_chunks"] = [
        {
            "content": doc.page_content,
            "score": doc.metadata.get("score", 0.0),
            "source": doc.metadata.get("source"),
            "page": doc.metadata.get("page"),
        }
        for doc in docs
    ]
    return docs, trace

async def _parent_doc_retrieve(query:str,config:PipelineConfig)->list[Document]:
        base_retriever = get_parent_doc_retriever(config)
        return await base_retriever.ainvoke(query)

async def _mmr_doc_retrieve(query:str,config:PipelineConfig)->list[Document]:
        vectorstore = get_vectorstore(config)
        embeddings = get_embeddings(config)
        embedded_query = asyncio.to_thread(embeddings.embed_query,query)

        results = asyncio.to_thread(
             vectorstore.max_marginal_relevance_search_with_score_by_vector,
             embedding=embedded_query,
             k=config.retrieval.top_k,
             fetch_k=config.retrieval.top_k*4)
        for doc,score in results:
            doc.metadata["score"] = score
        return [doc for doc, _ in results]

async def _standard_retrieve(query:str,config:PipelineConfig):
    vectorstore = get_vectorstore(config)
    results = await asyncio.to_thread(
        vectorstore.similarity_search_with_score,
        query=query,
        k=config.retrieval.top_k)
    for doc,score in results:
        doc.metadata["score"] = float(score)
    return [doc for doc, _ in results]