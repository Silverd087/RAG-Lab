from fastapi import APIRouter, Depends,status,HTTPException
from src.rag.models import PipelineConfig
from src.database.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database.models.pipeline import PipelineModel,PipelineStatusEnum
from src.database.models.pipeline_result import PipelineResultModel
from src.database.models.chunk_trace import ChunkTraceModel
from src.rag.pipeline import run_pipeline
import asyncio
from src.api.task import run_deep_eval
from src.api.schema import CompareRequest,CompareResponse,CompareStatusResponse,ComparisonListItem
from src.database.models.compare import ComparisonModel
from src.rag.models import PipelineResult,ChunkTrace
import uuid
from sqlalchemy.orm import selectinload

router = APIRouter()

@router.post("/compare",tags=["compare"],response_model=CompareResponse)
async def compare(payload:CompareRequest,db:AsyncSession=Depends(get_db)):
    query = payload.query
    pipeline_id1 = payload.pipeline_id1
    pipeline_id2 = payload.pipeline_id2
    
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
        latency=pipeline_result1.latency,
        chunks=[
            ChunkTraceModel(
                content = chunk.content,
                source = chunk.source,
                raw_score=chunk.raw_score,
                rerank_score=chunk.rerank_score 
            )
        for chunk in pipeline_result1.chunks]
    )
    
    result2 = PipelineResultModel(
        pipeline_id = pipeline_id2,
        query = query,
        translated_query = pipeline_result2.translated_query,
        query_variants = pipeline_result2.query_variants,
        answer = answer2,
        latency=pipeline_result2.latency,
        chunks=[
            ChunkTraceModel(
                content = chunk.content,
                source = chunk.source,
                raw_score=chunk.raw_score,
                rerank_score=chunk.rerank_score 
            )         
        for chunk in pipeline_result2.chunks]
    )
    db.add_all([result1,result2])
    await db.flush()

    comparison = ComparisonModel(
        query=query,
        status="pending",
        result_1_id=result1.id,
        result_2_id=result2.id,
    )
    db.add(comparison)
    await db.flush()

    run_deep_eval.delay(comparison_id=comparison.id ,result_id1=result1.id,result_id2=result2.id,config_1_dict=config1.model_dump(mode='json'),config_2_dict=config2.model_dump(mode='json'))

    pipeline_result1.id = result1.id
    pipeline_result2.id = result2.id

    return  CompareResponse(id=comparison.id,result1=pipeline_result1,result2=pipeline_result2)

def _to_pipeline_result(row:PipelineResultModel)->PipelineResult:
    return PipelineResult(
        id=row.id,
        pipeline_id=row.pipeline_id,
        session_id=row.session_id,
        created_at=row.created_at,
        query=row.query,
        query_variants=row.query_variants,
        translated_query=row.translated_query,
        chunks=[ChunkTrace(
            content=chunk.content,
            source=chunk.source,
            raw_score=chunk.raw_score,
            rerank_score=chunk.rerank_score,
        ) for chunk in row.chunks],
        answer=row.answer,
        latency=row.latency,
    )


@router.get("/compare",tags=["compare"],response_model=list[ComparisonListItem])
async def list_comparisons(db:AsyncSession=Depends(get_db)):
    stmt = select(ComparisonModel).order_by(ComparisonModel.created_at.desc())
    result = await db.execute(stmt)
    comparison_rows = result.scalars().all()

    return [ComparisonListItem(
        id=row.id,
        query=row.query,
        status=row.status,
        created_at=row.created_at,
    ) for row in comparison_rows]


@router.get("/compare/{comparison_id}",tags=["compare"])
async def get_comparison_id_status(comparison_id:uuid.UUID,db:AsyncSession=Depends(get_db)):
    stmt = (
        select(ComparisonModel)
        .options(
            selectinload(ComparisonModel.result_1).selectinload(PipelineResultModel.chunks),
            selectinload(ComparisonModel.result_2).selectinload(PipelineResultModel.chunks),
        )
        .where(ComparisonModel.id == comparison_id)
    )
    result = await db.execute(stmt)
    comparison_row = result.scalar_one_or_none()

    if not comparison_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Comparison trace not found")

    response =  CompareStatusResponse(
        id=comparison_row.id,
        status=comparison_row.status,
        query=comparison_row.query,
        result_1=comparison_row.result_1_id,
        result_2=comparison_row.result_2_id,
        evaluation_scores=comparison_row.evaluation_scores,
        result1=_to_pipeline_result(comparison_row.result_1) if comparison_row.result_1 else None,
        result2=_to_pipeline_result(comparison_row.result_2) if comparison_row.result_2 else None,
    )
    return response