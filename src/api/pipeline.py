from fastapi import APIRouter, Depends,status,HTTPException,File,UploadFile
from src.rag.models import PipelineConfig
from src.database.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,delete
from src.database.models.pipeline import PipelineModel,PipelineStatusEnum
from src.database.models.pipeline_result import PipelineResultModel
from src.database.models.chunk_trace import ChunkTraceModel
import uuid
import filetype
from src.storage.minio_client import get_minio_client
from config import settings
from src.api.task import ingest_task
from src.rag.pipeline import run_pipeline
import asyncio

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf"}
ALLOWED_MIME_TYPES = {
    "application/pdf", 
}

@router.get("/pipelines",tags=['pipeline'],status_code=status.HTTP_200_OK)
async def get_all_pipelines(db:AsyncSession = Depends(get_db))->list[PipelineConfig]:
    stmt = select(PipelineModel)
    result = await db.execute(stmt)

    pipeline_rows = result.scalars().all()
    if not pipeline_rows:
        return []
    return [PipelineConfig(
        id=pipeline_row.id,
        name=pipeline_row.name,
        created_at=pipeline_row.created_at,
        status=pipeline_row.status,
        **pipeline_row.config
    ) for pipeline_row in pipeline_rows]

@router.get("/pipelines/{id}",tags=['pipeline'],status_code=status.HTTP_200_OK)
async def get_pipeline_by_id(id:uuid.UUID,db:AsyncSession = Depends(get_db))->PipelineConfig:

    stmt = select(PipelineModel).where(PipelineModel.id == id)

    result = await db.execute(stmt)

    pipeline_row = result.scalar_one_or_none()

    if not pipeline_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"pipeline with {id} not found")
    return PipelineConfig(
        id=pipeline_row.id,
        name=pipeline_row.name,
        created_at=pipeline_row.created_at,
        status=pipeline_row.status,
        **pipeline_row.config
    )

@router.delete("/pipelines/{id}",tags=['pipeline'],status_code=status.HTTP_200_OK)
async def get_pipeline_by_id(id:uuid.UUID,db:AsyncSession = Depends(get_db))->PipelineConfig:
    stmt = delete(PipelineModel).where(PipelineModel.id == id)
    result = await db.execute(stmt)

    pipeline_row = result.scalar_one_or_none()
    if pipeline_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"pipeline with {id} not found")
    
    db.delete(pipeline_row)
    return PipelineConfig(
        id=pipeline_row.id,
        name=pipeline_row.name,
        created_at=pipeline_row.created_at,
        status=pipeline_row.status,
        **pipeline_row.config  
    )



@router.post("/pipelines",tags=['pipeline'],status_code=status.HTTP_201_CREATED)
async def get_pipeline_by_id(body:PipelineConfig,db:AsyncSession = Depends(get_db))->PipelineConfig:
    if not body:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Invalid request: config body is empty")
    new_pipeline = PipelineModel(
        id=body.id,
        name=body.name,
        status=body.status,
        created_at=body.created_at,
        config_payload=body.model_dump(exclude={"id", "name", "status", "created_at"})
    )
    db.add(new_pipeline)
    return body


@router.get("/pipelines/{id}/status",tags=["pipeline"],status_code=status.HTTP_200_OK)
async def get_pipeline_status(id:uuid.UUID,db:AsyncSession=Depends(get_db))->PipelineStatusEnum:
    stmt = select(PipelineModel).where(PipelineModel.id == id)

    result = await db.execute(stmt)

    pipeline_row = result.scalar_one_or_none()

    if not pipeline_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"pipeline with {id} not found")
    
    return pipeline_row.status

@router.post("/pipelines/{id}/upload",tags=["pipelines"],status_code=status.HTTP_200_OK)
async def upload(id:uuid.UUID,file:UploadFile,db:AsyncSession = Depends(get_db)):
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail='Missing file name')
    if not any(file.filename.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail='Bad file extension')
    
    header_bytes = await file.read(2048)
    await file.seek(0)

    kind = filetype.guess(header_bytes)
    detected_mime = kind.mime if kind else file.content_type

    if detected_mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail='Bad file mime type')
    
    stmt = select(PipelineModel).where(PipelineModel.id == id)
    result = await db.execute(stmt)
    pipeline_row = result.scalar_one_or_none()

    if not pipeline_row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f'Pipeline with id {id} not found')
    object_name = f"pipelines/{id}/{file.filename.lower()}"
    minio_client = get_minio_client()
    minio_client.put_object(
                            bucket_name=settings.minio_bucket_name,
                            data=file.file,
                            object_name=object_name,
                            length=file.size
                        )
    pipeline = PipelineConfig(
        id=pipeline_row.id,
        name=pipeline_row.name,
        created_at=pipeline_row.created_at,
        status=pipeline_row.status,
        **pipeline_row.config  
    )
    ingest_task.delay(pipeline.model_dump(mode="json"),object_name)

    return {"status":"ingesting"}

@router.post("/pipelines/{id}/query",tags=["pipeline"])
async def query(query:str,pipeline_id:uuid.UUID,db:AsyncSession = Depends(get_db)):
    if not query:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail='Query must not be empty')
    if not pipeline_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail='Pipeline id must not be empty')

    stmt = select(PipelineModel).where(PipelineModel.id == pipeline_id)
    result = await db.execute(stmt)

    pipeline_row = result.scalar_one_or_none()

    if not pipeline_row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f'Pipeline with id {pipeline_id} not found')
    
    pipeline_config = PipelineConfig(
        id=pipeline_row.id,
        name=pipeline_row.name,
        created_at=pipeline_row.created_at,
        status=pipeline_row.status,
        **pipeline_row.config
    )
    pipeline_result,answer = await run_pipeline(pipeline_config,query)

    result = PipelineResultModel(
        pipeline_id = pipeline_id,
        query = query,
        translated_query = pipeline_result.translated_query,
        query_variants = pipeline_result.query_variants,
        answer = answer,
        latency=pipeline_result.latency
    )
    for chunk in pipeline_result.get("chunks",[]):
        result.chunks.append(
            ChunkTraceModel(
                content = chunk.content,
                source = chunk.source,
                raw_score=chunk.score,
                rerank_score=chunk.rerank_score 
            )
        )
    db.add(result)
    return {
        "answer": result.answer,
        "result_id": result.id,
        "latency_metrics": result.latency
    }



@router.post("/compare")
async def compare(query:str,pipeline_id1:uuid.UUID,pipeline_id2:uuid.UUID,db:AsyncSession=Depends(get_db)):
    if not query:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail='Query must not be empty')
    if not pipeline_id1 or not pipeline_id2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail='Both pipeline ids must not be empty')
    
    stmt = select(PipelineModel).where(PipelineModel.id.in_([pipeline_id1,pipeline_id2]))
    result = await db.execute(stmt)
    pipelines = result.scalars().all()
    if len(pipelines)<2:
        raise HTTPException(status_code=status.HTTP_404_BAD_REQUEST,detail='One or both targeted pipeline configurations were not found')

    pipeline_map = {p.id: p for p in pipelines}
    pipe_row1 = pipeline_map.get(pipeline_id1)
    pipe_row2 = pipeline_map.get(pipeline_id2)

    config1 = PipelineConfig(
        id=pipe_row1.id, name=pipe_row1.name, created_at=pipe_row1.created_at, status=pipe_row1.status, **pipe_row1.config_payload
    )
    config2 = PipelineConfig(
        id=pipe_row2.id, name=pipe_row2.name, created_at=pipe_row2.created_at, status=pipe_row2.status, **pipe_row2.config_payload
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
    return {
        "pipeline1": {
            "result_id": result1.id,
            "answer": result1.answer,
            "latency_metrics": result1.latency
        },
        "pipeline2": {
            "result_id": result2.id,
            "answer": result2.answer,
            "latency_metrics": result2.latency
        }
    }





    





       