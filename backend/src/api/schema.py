from pydantic import BaseModel, ConfigDict,Field,UUID4,field_validator
from src.rag.models import (PipelineResult,PipelineStatus,QueryTranslationConfig,
                            ChunkingConfig,RetrievalConfig,PostRetrievalConfig,PipelineConfig)
from typing import Optional
from datetime import datetime
class CompareResponse(BaseModel):
    id:UUID4
    result1:PipelineResult
    result2:PipelineResult

class UploadResponse(BaseModel):
    status:PipelineStatus = PipelineStatus.INGESTING
    job_id:str

class DocumentResponse(BaseModel):
    name:str
    size:Optional[int] = None
    last_modified:Optional[datetime] = None

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
    session_id:Optional[UUID4] = None

class CompareRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    pipeline_id1:UUID4
    pipeline_id2:UUID4
    query:str = Field(...,min_length=1)

class DeepEvalScores(BaseModel):
    faithfulness: float
    # Contextual precision/recall need a ground-truth expected_output, which
    # ad-hoc comparisons don't have — only benchmarks against a dataset do.
    context_recall:Optional[float] = None
    context_precision:Optional[float] = None
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
    pipeline_ids:list[UUID4]
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
    scores:Optional[DeepEvalScores] = None
    status:str
    error:Optional[str] = None

class BenchmarkResultResponse(BaseModel):
    id: UUID4
    dataset_id: UUID4
    status:str
    created_at: datetime
    results:list[PipelineScores] | None = None
    error:str|None = None

class BenchmarkListResponse(BaseModel):
    benchmarks:list[BenchmarkResultResponse]

class CompareStatusResponse(BaseModel):
    id:UUID4
    status:str = "pending"
    query:str
    result_1:UUID4
    result_2:UUID4
    evaluation_scores:Optional[dict]
    result1:Optional[PipelineResult] = None
    result2:Optional[PipelineResult] = None

class ComparisonListItem(BaseModel):
    id:UUID4
    query:str
    status:str
    created_at:datetime

class DatasetUpdateQuery(BaseModel):
    name:Optional[str] = None
    description:Optional[str] = None

    model_config=ConfigDict(str_strip_whitespace=True,str_min_length=1)

class DatasetItemUpdateQuery(BaseModel):
    question:Optional[str] = None
    ground_truth:Optional[str] = None

    model_config=ConfigDict(str_strip_whitespace=True,str_min_length=1)