
from fastapi import APIRouter, Depends,status,HTTPException
from src.rag.models import PipelineConfig,PipelineResult,ChunkTrace
from src.database.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database.models.pipeline import PipelineModel,PipelineStatusEnum
from src.database.models.pipeline_result import PipelineResultModel
from src.database.models.chunk_trace import ChunkTraceModel
import uuid
from src.rag.pipeline import run_pipeline

router = APIRouter()

@router.post("/pipelines/{id}/query",tags=["query"],response_model=PipelineResult)
async def query_pipeline(id:uuid.UUID,query:str,db:AsyncSession = Depends(get_db)):
    if not query:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail='Query must not be empty')
    if not id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail='Pipeline id must not be empty')

    stmt = select(PipelineModel).where(PipelineModel.id == id)
    result = await db.execute(stmt)

    pipeline_row = result.scalar_one_or_none()

    if not pipeline_row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f'Pipeline with id {id} not found')
    
    if pipeline_row.status != PipelineStatusEnum.READY:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f"Pipeline is not ready — current status: {pipeline_row.status.value}")

    
    pipeline_config = PipelineConfig(
        id=pipeline_row.id,
        name=pipeline_row.name,
        created_at=pipeline_row.created_at,
        status=pipeline_row.status,
        **pipeline_row.config
    )
    pipeline_result,answer = await run_pipeline(pipeline_config,query)

    result = PipelineResultModel(
        pipeline_id = id,
        query = query,
        translated_query = pipeline_result.translated_query,
        query_variants = pipeline_result.query_variants,
        answer = answer,
        latency=pipeline_result.latency,
        chunks= [ChunkTraceModel(
            content = chunk.content,
            source = chunk.source,
            raw_score=chunk.raw_score,
            rerank_score=chunk.rerank_score 
        ) for chunk in pipeline_result.chunks]
    )

    db.add(result)
    return  PipelineResult(
        pipeline_id = id,
        query = query,
        translated_query = pipeline_result.translated_query,
        query_variants = pipeline_result.query_variants,
        answer = answer,
        latency=pipeline_result.latency,
        chunks= [ChunkTrace(
                content = chunk.content,
                source = chunk.source,
                raw_score=chunk.raw_score,
                rerank_score=chunk.rerank_score 
            ) for chunk in pipeline_result.chunks]
    )

@router.get("/pipelines/{id}/results",status_code=status.HTTP_200_OK,response_model=list[PipelineResult])
async def get_pipeline_history(id:uuid.UUID,db:AsyncSession = Depends(get_db)):
    if not id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail='Pipeline id must not be empty')
    
    stmt = select(PipelineResultModel).where(PipelineResultModel.pipeline_id == id)
    result = await db.execute(stmt)

    pipeline_rows = result.scalars().all()

    if not pipeline_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f'No Pipeline results with id {id} were found')

    return [PipelineResult(
        id=pipeline_row.id,
        pipeline_id=pipeline_row.pipeline_id,
        query=pipeline_row.query,
        query_variants=pipeline_row.query_variants,
        translated_query=pipeline_row.translated_query,
        chunks=[ChunkTrace(
            content=chunk.content,
            source= chunk.source,
            raw_score=chunk.raw_score,
            rerank_score=chunk.rerank_score,
        ) for chunk in pipeline_row.chunks],
        answer=pipeline_row.answer,
        latency=pipeline_row.latency
    ) for pipeline_row in pipeline_rows]

@router.get("/pipelines/{id}/results/{result_id}",status_code=status.HTTP_200_OK,response_model=PipelineResult)
async def get_pipeline_result(id:uuid.UUID,result_id:uuid.UUID,db:AsyncSession=Depends(get_db)):
    if not id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail='Pipeline id must not be empty')
    
    if not result_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail='result id must not be empty')
    
    stmt = select(PipelineResultModel).where(PipelineResultModel.pipeline_id == id and PipelineResultModel.id == result_id)

    result = await db.execute(stmt)

    pipeline_row = result.scalar_one_or_none()

    if not pipeline_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail='result id was not found')
    
    return PipelineResult(
        id=pipeline_row.id,
        pipeline_id=pipeline_row.pipeline_id,
        query=pipeline_row.query,
        query_variants=pipeline_row.query_variants,
        translated_query=pipeline_row.translated_query,
        chunks=[ChunkTrace(
            content=chunk.content,
            source= chunk.source,
            raw_score=chunk.raw_score,
            rerank_score=chunk.rerank_score,   
        ) for chunk in pipeline_row.chunks],
        answer=pipeline_row.answer,
        latency=pipeline_row.latency
    )
