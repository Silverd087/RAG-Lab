from pydantic import BaseModel,UUID4, model_validator,Field,ConfigDict
from enum import Enum
from datetime import datetime,timezone
from typing import Optional
from uuid import uuid4


class PipelineStatus(str,Enum):
    DRAFT = "draft"
    INGESTING = "ingesting"
    READY = "ready"
    ERROR = "error"

class ChunkingStrategy(str,Enum):
    RECURSIVE = "recursive"
    FIXED = "fixed"
    SEMANTIC = "semantic"
    SENTENCE = "sentence"

class ChunkingConfig(BaseModel):
    strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE
    chunk_size: int = 500
    parent_chunk_size: Optional[int] = None
    overlap: int = 50
    parent_overlap: Optional[int] = None
    parent_doc: bool = False

    @model_validator(mode="after")
    def enforce_default_parent(self)-> "ChunkingConfig":
        if not self.parent_doc:
            self.parent_overlap = None
            self.parent_chunk_size = None
        else:
            if self.parent_overlap is None:
                self.parent_overlap = 200
            if self.parent_chunk_size is None:
                self.parent_chunk_size = 2000
        return self           

class VectorDb(str,Enum):
    QDRANT = "qdrant"
    CHROMA = "chroma"

class Provider(str,Enum):
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    HUGGINGFACE = "huggingface"

class IndexingConfig(BaseModel):
    vector_db: VectorDb = VectorDb.QDRANT
    provider:Provider = Provider.GOOGLE
    embedding_model: str = "gemini-embedding-001"

class QueryTranslationConfig(BaseModel):
    multi_query: bool = False
    hyde: bool = False
    step_back: bool = False


class ModeConfig(str,Enum):
    DENSE = "dense"
    SPARSE = "sparse"
    HYBRID = "hybrid"
    MMR = "mmr"

class RetrievalConfig(BaseModel):
    mode: ModeConfig = ModeConfig.DENSE
    top_k: int = 5

class RerankerConfig(str,Enum):
    NONE = "none"
    CROSS_ENCODER = "cross-encoder"
    COHERE = "cohere"
    RECIPROCAL_RANK_FUSION = "reciprocal_rank_fusion"


class PostRetrievalConfig(BaseModel):
    reranker: RerankerConfig = RerankerConfig.NONE
    top_n: Optional[int] = None
    cross_encoder_model: Optional[str] = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    cohere_model: Optional[str] = "rerank-english-v3.0"
    compression: bool = False
    reorder: bool = False

    @model_validator(mode='after')
    def enforce_reranker_config(self)->"PostRetrievalConfig":
        if self.reranker == RerankerConfig.CROSS_ENCODER and (self.top_n is None or self.top_n <0):
            raise ValueError("top_n field is required to be an integer greater than 0")
        if self.reranker == RerankerConfig.CROSS_ENCODER and self.cross_encoder_model is None:
            raise ValueError("cross encoder model field is required")
        if self.reranker == RerankerConfig.COHERE and (self.top_n is None or self.top_n<0):
            raise ValueError("cohere model field is required")
        return self

class Prompt(BaseModel):
    prompt_id:UUID4 = Field(default_factory=uuid4)
    prompt:Optional[str] = None

class GenerationConfig(BaseModel):
    llm: str = "gemini-2.5-flash"
    provider:Provider = Provider.GOOGLE
    streaming: bool = False
    prompt: Optional[Prompt] = None

class PipelineConfig(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    id: Optional[UUID4] = None
    name: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: PipelineStatus = PipelineStatus.DRAFT
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    indexing: IndexingConfig = Field(default_factory=IndexingConfig)
    query_translation: QueryTranslationConfig = Field(default_factory=QueryTranslationConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    post_retrieval: PostRetrievalConfig = Field(default_factory=PostRetrievalConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)

    @model_validator(mode='after')
    def enforce_rrf_requires_multi_query(self)->"PipelineConfig":
        if self.post_retrieval.reranker == RerankerConfig.RECIPROCAL_RANK_FUSION and not self.query_translation.multi_query:
            raise ValueError("reciprocal_rank_fusion reranker requires multi_query to be enabled")
        return self



class PipelinePresets:

    @staticmethod
    def baseline(name:str):
        """Dense retrieval, recursive chunking, no reranking"""
        return PipelineConfig(name=name)

    @staticmethod
    def rag_fusion(name:str):
        """Multi-query + Reciprocal Rank Fusion"""
        return PipelineConfig(name=name,
                              query_translation=QueryTranslationConfig(multi_query=True),
                              post_retrieval=PostRetrievalConfig(
                                  reranker=RerankerConfig.RECIPROCAL_RANK_FUSION,
                                  top_n=5))
    @staticmethod
    def hyde_hybrid(name:str):
        """hyde + hybrid BM25/dense retrieval"""
        return PipelineConfig(name=name,
                              retrieval=RetrievalConfig(mode=ModeConfig.HYBRID),query_translation=QueryTranslationConfig(hyde=True))
    
    @staticmethod
    def parent_rerank(name: str) -> PipelineConfig:
        """Parent-document retriever + cross-encoder reranking"""
        return PipelineConfig(
            name=name,
            chunking=ChunkingConfig(parent_doc=True),
            post_retrieval=PostRetrievalConfig(
                reranker=RerankerConfig.CROSS_ENCODER,
                top_n=5,
            ),
        )
    @staticmethod
    def rag_multiquery(name:str):
        """Multi-query"""
        return PipelineConfig(name=name,
                              query_translation=QueryTranslationConfig(multi_query=True))

    @staticmethod
    def rag_hyde(name:str):
        """Hyde"""
        return PipelineConfig(name=name,
                              query_translation=QueryTranslationConfig(hyde=True))

    @staticmethod
    def rag_step_back(name:str):
        """Step back prompting"""
        return PipelineConfig(name=name,
                              query_translation=QueryTranslationConfig(step_back=True))
    
    @staticmethod
    def rag_cross_encoder(name:str):
        "Cross Encoder reranker"
        return PipelineConfig(name=name,post_retrieval=PostRetrievalConfig(reranker=RerankerConfig.CROSS_ENCODER,top_n=2))
    
    @staticmethod
    def rag_reorder(name:str):
        return PipelineConfig(name=name,post_retrieval=PostRetrievalConfig(reorder=True))
    
    @staticmethod
    def rag_mmr(name:str):
        return PipelineConfig(name=name,retrieval=RetrievalConfig(mode=ModeConfig.MMR))

    @staticmethod
    def rag_cohere(name:str):
        return PipelineConfig(name=name,post_retrieval=PostRetrievalConfig(reranker=RerankerConfig.COHERE,top_n=2))

class ChunkTrace(BaseModel):
    content:str
    source:str
    raw_score:float
    rerank_score:float|None
    by:str|None = None

class PipelineResult(BaseModel):
    id:UUID4|None = Field(default_factory=uuid4)
    pipeline_id:UUID4
    session_id:UUID4|None = None
    created_at:datetime|None = None
    query:str
    query_variants:list[str] | None
    translated_query:str|None
    chunks:list[ChunkTrace]
    answer:str
    latency: dict[str,int]


 