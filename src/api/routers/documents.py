import filetype
from src.storage.minio_client import get_minio_client
from config import settings
from src.api.task import ingest_task
from src.database.session import get_db
from fastapi import APIRouter, Depends,status,HTTPException,UploadFile
from src.database.models.pipeline import PipelineModel,PipelineStatusEnum
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from src.rag.models import PipelineConfig
from src.rag.models import UploadResponse
from sqlalchemy import select

ALLOWED_EXTENSIONS = {".pdf"}
ALLOWED_MIME_TYPES = {
    "application/pdf", 
}

router = APIRouter()

@router.post("/pipelines/{id}/upload",tags=["documents"],status_code=status.HTTP_202_ACCEPTED,response_model=PipelineStatusEnum)
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
    result = ingest_task.delay(pipeline.model_dump(mode="json"),object_name)


    return UploadResponse(job_id=result.id)