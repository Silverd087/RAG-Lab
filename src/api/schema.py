from pydantic import BaseModel, ConfigDict,Field,UUID4,field_validator
from src.rag.models import (PipelineResult,PipelineStatus,QueryTranslationConfig,
                            ChunkingConfig,RetrievalConfig,PostRetrievalConfig,PipelineConfig)
from typing import Optional
from datetime import datetime
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
    faithfulness: float
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

class DatasetItemCreate(BaseModel):
    question:str
    ground_truth:str

class DatasetItemCreateQuery(BaseModel):
    items: list[DatasetItemCreate]

    @field_validator("items")
    def must_not_be_empty(cls, value):
        if not value or len(value) == 0:
            raise ValueError("Items list cannot be empty")
        return value

class DatasetCreateQuery(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name:str = Field(...,min_length=1)
    description:str
    items: list[DatasetItemCreate]

    @field_validator("items")
    def must_not_be_empty(cls, value):
        if not value or len(value) == 0:
            raise ValueError("Items list cannot be empty")
        return value

class DatasetItemResponse(BaseModel):
    id:UUID4
    question:str
    ground_truth:str

class DatasetResponse(BaseModel):
    id:UUID4
    name:str
    description:Optional[str] = None
    created_at:datetime
    items: Optional[list[DatasetItemResponse]] = None

class DatasetListResponse(BaseModel):
    id:UUID4
    name:str
    description:Optional[str] = None
    created_at:datetime

class BenchmarkRequest(BaseModel):
    pipeline_ids:list[PipelineConfig]
    dataset_id:str

    @field_validator("pipeline_ids")
    @classmethod
    def must_have_at_least_one(cls, v):
        if not v:
            raise ValueError("At least one pipeline_id required")
        return v

    @field_validator("dataset_id")
    @classmethod
    def must_not_be_empty(cls, v):
        if not v:
            raise ValueError("dataset_id cannot be empty")
        return v
    

class PipelineScores(BaseModel):
    pipeline_id: UUID4
    pipeline_name:str
    scores:DeepEvalScores

class BenchmarkResultResponse(BaseModel):
    benchmark_id: UUID4
    status:str
    results:list[PipelineScores] | None = None
    error:str|None = None

class CompareStatusResponse(BaseModel):
    comparison_id:UUID4
    status:str = "pending"
    query:str
    result_1:str
    result_2:str
    evaluation_scores:dict