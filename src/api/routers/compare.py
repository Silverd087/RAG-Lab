from fastapi import APIRouter, Depends,status,HTTPException
from src.rag.models import PipelineConfig,CompareResponse,PipelineResult,ChunkTrace
from src.database.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database.models.pipeline import PipelineModel,PipelineStatusEnum
from src.database.models.pipeline_result import PipelineResultModel
from src.database.models.chunk_trace import ChunkTraceModel
import uuid
from src.rag.pipeline import run_pipeline
import asyncio

router = APIRouter()

@router.post("/compare",tags=["compare"],response_model=CompareResponse)
async def compare(query:str,pipeline_id1:uuid.UUID,pipeline_id2:uuid.UUID,db:AsyncSession=Depends(get_db)):
    if not query:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail='Query must not be empty')
    if not pipeline_id1 or not pipeline_id2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail='Both pipeline ids must not be empty')
    
    stmt = select(PipelineModel).where(PipelineModel.id.in_([pipeline_id1,pipeline_id2]))
    result = await db.execute(stmt)
    pipelines = result.scalars().all()
    if len(pipelines)<2:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail='One or both targeted pipeline configurations were not found')

    pipeline_map = {p.id: p for p in pipelines}
    pipe_row1 = pipeline_map.get(pipeline_id1)
    pipe_row2 = pipeline_map.get(pipeline_id2)

    if pipe_row1.status != PipelineStatusEnum.READY:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f"Pipeline with id {pipe_row1.id} is not ready — current status: {pipe_row1.status.value}")

    if pipe_row2.status != PipelineStatusEnum.READY:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f"Pipeline with id {pipe_row2.id} is not ready — current status: {pipe_row2.status.value}")

    config1 = PipelineConfig(
        id=pipe_row1.id, name=pipe_row1.name, created_at=pipe_row1.created_at, status=pipe_row1.status, **pipe_row1.config
    )
    config2 = PipelineConfig(
        id=pipe_row2.id, name=pipe_row2.name, created_at=pipe_row2.created_at, status=pipe_row2.status, **pipe_row2.config
    )

    task_1 = run_pipeline(config1,query)
    task_2 = run_pipeline(config2,query)

    results = await asyncio.gather(task_1,task_2)
    
    (pipeline_result1,answer1),(pipeline_result2,answer2) = results

    result1 = PipelineResultModel(
        pipeline_id = pipeline_id1,
        query = query,
        translated_query = pipeline_result1.translated_query,
        query_variants = pipeline_result1.query_variants,
        answer = answer1,
        latency=pipeline_result1.latency
    )
    for chunk in pipeline_result1.chunks:
        result1.chunks.append(
            ChunkTraceModel(
                content = chunk.content,
                source = chunk.source,
                raw_score=chunk.score,
                rerank_score=chunk.rerank_score 
            )
        )
    
    result2 = PipelineResultModel(
        pipeline_id = pipeline_id2,
        query = query,
        translated_query = pipeline_result2.translated_query,
        query_variants = pipeline_result2.query_variants,
        answer = answer2,
        latency=pipeline_result2.latency
    )
    for chunk in pipeline_result2.chunks:
        result2.chunks.append(
            ChunkTraceModel(
                content = chunk.content,
                source = chunk.source,
                raw_score=chunk.score,
                rerank_score=chunk.rerank_score 
            )
        )
    db.add_all([result1,result2])
    result1 = PipelineResult(
        pipeline_id = pipeline_id1,
        query = query,
        translated_query = pipeline_result1.translated_query,
        query_variants = pipeline_result1.query_variants,
        answer = answer1,
        latency=pipeline_result1.latency
    )
    for chunk in pipeline_result1.chunks:
        result1.chunks.append(
            ChunkTrace(
                content = chunk.content,
                source = chunk.source,
                raw_score=chunk.score,
                rerank_score=chunk.rerank_score 
            )
        )
    result2 = PipelineResult(
        pipeline_id = pipeline_id2,
        query = query,
        translated_query = pipeline_result2.translated_query,
        query_variants = pipeline_result2.query_variants,
        answer = answer2,
        latency=pipeline_result2.latency
    )
    for chunk in pipeline_result2.chunks:
        result2.chunks.append(
            ChunkTrace(
                content = chunk.content,
                source = chunk.source,
                raw_score=chunk.score,
                rerank_score=chunk.rerank_score 
            )
        )
    return  CompareResponse(result1,result2)