from langchain_google_genai import GoogleGenerativeAIEmbeddings
from qdrant_client import QdrantClient
from config import settings
from langchain_qdrant import QdrantVectorStore,RetrievalMode,FastEmbedSparse
from langchain_text_splitters import RecursiveCharacterTextSplitter, CharacterTextSplitter
from .models import PipelineConfig
from .models import ModeConfig
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_cohere import CohereRerank
from .models import ChunkingStrategy
from langchain_experimental.text_splitter import SemanticChunker
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_classic.retrievers import ParentDocumentRetriever
from langchain_community.storage import RedisStore
from langchain_classic.storage._lc_store import create_kv_docstore
from langchain_core.prompts import ChatPromptTemplate

_client: QdrantClient | None = None
_embeddings:  dict[str, GoogleGenerativeAIEmbeddings] = {}
_cross_encoder: dict[str,HuggingFaceCrossEncoder] = {}
_cohere_rerank: dict[str,CohereRerank] = {}
_llm: dict[str,ChatGoogleGenerativeAI] = {}
_prompt:dict[str,any] = {}
_sparse_embeddings = None

def get_sparse_embeddings():
    global _sparse_embeddings
    if _sparse_embeddings is None:
        _sparse_embeddings = FastEmbedSparse(model_name="Qdrant/bm25")
    return _sparse_embeddings

def get_cross_encoder(config:PipelineConfig)->HuggingFaceCrossEncoder:
    model = config.post_retrieval.cross_encoder_model
    if model not in _cross_encoder:
        _cross_encoder[model] = HuggingFaceCrossEncoder(model_name=model)
    return _cross_encoder[model]

def get_cohere_rerank(config:PipelineConfig)->CohereRerank:
    model = config.post_retrieval.cohere_model
    if model not in _cohere_rerank:
        _cohere_rerank[model] = CohereRerank(model=model)
    return _cohere_rerank[model]

def get_client()->QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=settings.qdrant_url)
    return _client

def get_embeddings(config:PipelineConfig)->GoogleGenerativeAIEmbeddings:
    model =  config.indexing.embedding_model
    if model not in _embeddings:
        _embeddings[model] = GoogleGenerativeAIEmbeddings(model=model,google_api_key=settings.google_api_key)
    return _embeddings[model]

def get_llm(config:PipelineConfig)->ChatGoogleGenerativeAI:
    model = config.generation.llm
    if model not in _llm:
        _llm[model] = ChatGoogleGenerativeAI(model=config.generation.llm, temperature=0,google_api_key=settings.google_api_key)
    return _llm[model]


mode_map = {
    ModeConfig.DENSE : RetrievalMode.DENSE,
    ModeConfig.SPARSE : RetrievalMode.SPARSE,
}

def get_vectorstore(config:PipelineConfig)-> QdrantVectorStore:
    _embeddings = get_embeddings(config)

    # Retrieval mode selection
    # vector store for mmr search
    if config.retrieval.mode == ModeConfig.MMR:
        vectorstore = QdrantVectorStore(
            client=get_client(),
            embedding=_embeddings,
            collection_name=f"collection_{config.id}",
        )
    if config.retrieval.mode == RetrievalMode.HYBRID:
        vectorstore = QdrantVectorStore(
        client=get_client(),
        embedding=_embeddings,
        collection_name=f"collection_{config.id}",
        retrieval_mode=RetrievalMode.HYBRID,
        sparse_embedding=get_sparse_embeddings(),
        )
    # vector store with selected retrieval mode
    else:
        vectorstore = QdrantVectorStore(
        client=get_client(),
        embedding=_embeddings,
        collection_name=f"collection_{config.id}",
        retrieval_mode=mode_map[config.retrieval.mode],
        )
    return vectorstore

def get_splitter(config:PipelineConfig, use_parent:bool = False):
    chunk_size = config.chunking.parent_chunk_size if use_parent else config.chunking.chunk_size
    overlap = config.chunking.parent_overlap if use_parent else config.chunking.overlap
    strategy = config.chunking.strategy
    if strategy == ChunkingStrategy.RECURSIVE:
        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap
            )
    elif strategy == ChunkingStrategy.FIXED:
        return CharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap
            )
    elif strategy == ChunkingStrategy.SENTENCE:
        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            separators=["\n",".","?","!"]
            )
    elif strategy == ChunkingStrategy.SEMANTIC:
        # SemanticChunker splits by embedding similarity,
        # chunk_size and overlap are not applicable
        return SemanticChunker(
            embeddings=get_embeddings(config),
            breakpoint_threshold_type='percentile'
            )
    raise ValueError(f"Unkown chunking strategy {strategy}")



def get_parent_doc_retriever(config):
    vectorstore = get_vectorstore(config)
    chil_splitter = get_splitter(config,use_parent=False)
    parent_splitter = get_splitter(config,use_parent=True)
    store = RedisStore(redis_url=settings.redis_url,namespace=f'docstore_{config.id}')
    docstore = create_kv_docstore(store)
    base_retriever = ParentDocumentRetriever(
        vectorstore=vectorstore,
        child_splitter=chil_splitter,
        parent_splitter=parent_splitter,
        docstore=docstore
        )
    return base_retriever

DEFAULT_RAG_TEMPLATE = """You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question. If you don't know the answer, just say that you don't know. Use three sentences maximum and keep the answer concise.
    Question: {question} 
    Context: {context} 
    Answer:
"""

def get_prompt(config:PipelineConfig)->ChatPromptTemplate:
    key = config.generation.prompt.prompt_id or "default"
    if key not in _prompt:
        template = config.generation.prompt.prompt or DEFAULT_RAG_TEMPLATE
        _prompt[key] = ChatPromptTemplate.from_template(template)
    return _prompt[key]