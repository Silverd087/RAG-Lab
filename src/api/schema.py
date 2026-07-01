from pydantic import BaseModel, ConfigDict,Field,UUID4,field_validator
from src.rag.models import (PipelineResult,PipelineStatus,QueryTranslationConfig,
                            ChunkingConfig,RetrievalConfig,PostRetrievalConfig,PipelineConfig)
from typing import Optional

class CompareResponse(BaseModel):
    job_id:str
    result1:PipelineResult
    result2:PipelineResult

class UploadResponse(BaseModel):
    status:PipelineStatus = PipelineStatus.INGESTING
    job_id:str

class PipelineUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1)
    status: Optional[str] = None
    chunking: Optional[ChunkingConfig] = None
    retrieval: Optional[RetrievalConfig] = None
    query_translation:Optional[QueryTranslationConfig] = None
    post_retrieval:Optional[PostRetrievalConfig] = None

class QueryRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    query:str = Field(...,min_length=1)

class CompareRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    pipeline_id1:UUID4
    pipeline_id2:UUID4
    query:str = Field(...,min_length=1)

class DeepEvalScores(BaseModel):
    faithulness: float
    context_recall:float
    context_precision:float
    answer_relevance: float

class JobStatusResponse(BaseModel):
    job_id:str
    status:str
    scores_1: Optional[DeepEvalScores] = None
    scores_2: Optional[DeepEvalScores] = None
    error: Optional[str] = None

class DeepEvalResponse(BaseModel):
    scores_1:DeepEvalScores
    scores_2:DeepEvalScores

class GoldenSetItem(BaseModel):
    question:str
    answer:str

class BenchmarkRequest(BaseModel):
    pipeline_ids:list[PipelineConfig]
    golden_set:list[GoldenSetItem]

    @field_validator("pipeline_ids")
    @classmethod
    def must_have_at_least_one(cls, v):
        if not v:
            raise ValueError("At least one pipeline_id required")
        return v

    @field_validator("golden_set")
    @classmethod
    def must_have_at_least_one_item(cls, v):
        if not v:
            raise ValueError("Golden set cannot be empty")
        return v
    
class BenchmarkResponse(BaseModel):
    task_id:str
    status:str = "Pending"
    pipeline_count:int
