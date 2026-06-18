from fastapi import APIRouter, Depends,status,HTTPException,File,UploadFile
from rag.models import PipelineConfig
from database.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,delete,insert
from database.models.pipeline import PipelineModel,PipelineStatusEnum
import uuid
import filetype
from storage.minio_client import get_minio_client
from config import settings
from api.task import ingest_task

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
        **pipeline_row.pipeline_config
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
        **pipeline_row.pipeline_config
    )

@router.delete("/pipelines/{id}",tags=['pipeline'],status_code=status.HTTP_200_OK)
async def get_pipeline_by_id(id:uuid.UUID,db:AsyncSession = Depends(get_db))->PipelineConfig:
    stmt = delete(PipelineModel).where(PipelineModel.id == id)
    result = await db.execute(stmt)

    pipeline_row = result.scalar_one_or_none()
    if pipeline_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"pipeline with {id} not found")
    return PipelineConfig(
        id=pipeline_row.id,
        name=pipeline_row.name,
        created_at=pipeline_row.created_at,
        status=pipeline_row.status,
        **pipeline_row.pipeline_config  
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
        **pipeline_row.pipeline_config  
    )
    ingest_task.delay(pipeline.model_dump(mode="json"),object_name)
    
    





       