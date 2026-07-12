
from fastapi import APIRouter, Depends,status,HTTPException
from src.rag.models import PipelineConfig,PipelineResult,ChunkTrace
from src.database.session import get_db,async_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from src.database.models.pipeline import PipelineModel,PipelineStatusEnum
from src.database.models.pipeline_result import PipelineResultModel
from src.database.models.chunk_trace import ChunkTraceModel
import uuid
from src.rag.pipeline import run_pipeline,run_pipeline_stream
from src.api.schema import QueryRequest
from fastapi.responses import StreamingResponse
import json

router = APIRouter()


def _build_result_row(id:uuid.UUID,pipeline_result:PipelineResult, answer:str):

    result = PipelineResultModel(
        pipeline_id = id,
        session_id = pipeline_result.session_id,
        query = pipeline_result.query,
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
    return result

@router.post("/pipelines/{id}/query",tags=["query"],response_model=PipelineResult)
async def query_pipeline(id:uuid.UUID,payload:QueryRequest,db:AsyncSession = Depends(get_db)):
    query = payload.query

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

    result = _build_result_row(id,pipeline_result.model_copy(update={"session_id": payload.session_id}),answer)

    db.add(result)
    await db.flush()
    updated_result = pipeline_result.model_copy(update={
        "id": result.id,
        "session_id": result.session_id,
        "created_at": result.created_at,
    })
    return updated_result

@router.post("/stream/pipelines/{id}/query",tags=["query"])
async def query_pipeline_stream(id:uuid.UUID,payload:QueryRequest,db:AsyncSession = Depends(get_db)):
    query = payload.query

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
    async def event_stream():
        answer_parts = []
        pipeline_result = None
        final_latency = {}
        try:
            async for event in run_pipeline_stream(config=pipeline_config,query=query):
                if event["type"] == "token":
                    answer_parts.append(event["text"])
                if event["type"] == "metadata":
                    pipeline_result = {k: v for k, v in event.items() if k != "type"}
                elif event["type"] == "done":
                    final_latency = event["latency"]
                    continue 
                yield f"data: {json.dumps(event)}\n\n"
            if pipeline_result is None:
                return
            result_obj = PipelineResult(
                    pipeline_id=id,
                    session_id=payload.session_id,
                    query=query,
                    translated_query=pipeline_result["query_translation"],
                    query_variants=pipeline_result["query_variants"],
                    chunks=[ChunkTrace(**c) for c in pipeline_result["chunks"]],
                    answer="".join(answer_parts),
                    latency=final_latency,
                )
            async with async_session() as session:
                result = _build_result_row(id,result_obj,"".join(answer_parts))
                session.add(result)
                await session.commit()
                yield f'data: {json.dumps({"type":"done","result_id":str(result.id),"latency":final_latency})}\n\n'
        except Exception as e:
            yield f'data: {json.dumps({"type":"error","detail":str(e)})}\n\n' 

    return StreamingResponse(event_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
 

@router.get("/pipelines/{id}/results",status_code=status.HTTP_200_OK,response_model=list[PipelineResult])
async def get_pipeline_history(id:uuid.UUID,db:AsyncSession = Depends(get_db)):
    
    stmt = (
        select(PipelineResultModel)
        .where(PipelineResultModel.pipeline_id == id)
        .options(selectinload(PipelineResultModel.chunks))
        .order_by(PipelineResultModel.created_at)
    )
    result = await db.execute(stmt)

    pipeline_rows = result.scalars().all()

    return [PipelineResult(
        id=pipeline_row.id,
        pipeline_id=pipeline_row.pipeline_id,
        session_id=pipeline_row.session_id,
        created_at=pipeline_row.created_at,
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
    
    stmt = select(PipelineResultModel).where(PipelineResultModel.pipeline_id == id, PipelineResultModel.id == result_id).options(selectinload(PipelineResultModel.chunks))

    result = await db.execute(stmt)

    pipeline_row = result.scalar_one_or_none()

    if not pipeline_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail='result id was not found')
    
    return PipelineResult(
        id=pipeline_row.id,
        pipeline_id=pipeline_row.pipeline_id,
        session_id=pipeline_row.session_id,
        created_at=pipeline_row.created_at,
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
