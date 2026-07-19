from fastapi import APIRouter, Depends,status,HTTPException
from src.rag.models import PipelineConfig
from src.database.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,update
from src.database.models.pipeline import PipelineModel,PipelineStatusEnum
import uuid
import logging
from pydantic import ValidationError
from src.api.schema import PipelineUpdate
from src.rag.core import get_client
from src.storage.minio_client import get_minio_client
from minio.deleteobjects import DeleteObject
from redis import Redis
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/pipelines",tags=['pipeline'],status_code=status.HTTP_200_OK,response_model=list[PipelineConfig])
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

@router.get("/pipelines/{id}",tags=['pipeline'],status_code=status.HTTP_200_OK,response_model=PipelineConfig)
async def get_pipeline_by_id(id:uuid.UUID,db:AsyncSession = Depends(get_db)):
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

@router.delete("/pipelines/{id}",tags=['pipeline'],status_code=status.HTTP_204_NO_CONTENT)
async def delete_pipeline_by_id(id:uuid.UUID,db:AsyncSession = Depends(get_db)):
    stmt = select(PipelineModel).where(PipelineModel.id == id)
    result = await db.execute(stmt)

    pipeline_row = result.scalar_one_or_none()
    if not pipeline_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"pipeline with {id} not found")

    # Best-effort cleanup of per-pipeline storage: a draft pipeline may have
    # none of these yet, and a failure here shouldn't keep the DB row alive.
    try:
        qdrant_client = get_client()
        qdrant_client.delete_collection(collection_name=f"collection_{id}")
    except Exception:
        logger.warning("Failed to delete qdrant collection for pipeline %s", id, exc_info=True)

    try:
        minio_client = get_minio_client()
        objects = minio_client.list_objects(bucket_name=settings.minio_bucket_name,prefix=f"pipelines/{id}/",recursive=True)
        delete_list = [DeleteObject(obj.object_name) for obj in objects]
        # remove_objects is lazy — deletion only happens while the error
        # iterator is consumed.
        for error in minio_client.remove_objects(settings.minio_bucket_name, delete_list):
            logger.warning("Failed to delete object %s for pipeline %s: %s", error.name, id, error.message)
    except Exception:
        logger.warning("Failed to delete minio documents for pipeline %s", id, exc_info=True)

    try:
        redis_client = Redis.from_url(settings.redis_url)
        docstore_keys = list(redis_client.scan_iter(match=f"docstore_{id}/*"))
        if docstore_keys:
            redis_client.delete(*docstore_keys)
        redis_client.close()
    except Exception:
        logger.warning("Failed to delete redis docstore for pipeline %s", id, exc_info=True)

    await db.delete(pipeline_row)



@router.post("/pipelines",tags=['pipeline'],status_code=status.HTTP_201_CREATED,response_model=PipelineConfig)
async def create_pipeline(body:PipelineConfig,db:AsyncSession = Depends(get_db)):
    new_pipeline = PipelineModel(
        name=body.name,
        status=body.status,
        created_at=body.created_at,
        config=body.model_dump(mode="json",exclude={"id", "name", "status", "created_at","error"})
    )
    db.add(new_pipeline)
    await db.flush()
    return PipelineConfig(
        id=new_pipeline.id,
        name=new_pipeline.name,
        status=new_pipeline.status,
        created_at=new_pipeline.created_at,
        **new_pipeline.config
    )


@router.get("/pipelines/{id}/status",tags=["pipeline"],status_code=status.HTTP_200_OK,response_model=PipelineStatusEnum)
async def get_pipeline_status(id:uuid.UUID,db:AsyncSession=Depends(get_db))->PipelineStatusEnum:
    stmt = select(PipelineModel).where(PipelineModel.id == id)

    result = await db.execute(stmt)

    pipeline_row = result.scalar_one_or_none()

    if not pipeline_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"pipeline with {id} not found")
    
    return pipeline_row.status


@router.patch("/pipelines/{id}",tags=["pipeline"],status_code=status.HTTP_200_OK)
async def update_pipeline(id:uuid.UUID,payload:PipelineUpdate,db:AsyncSession=Depends(get_db)):
    stmt = select(PipelineModel).where(PipelineModel.id == id)

    result = await db.execute(stmt)

    pipeline_row = result.scalar_one_or_none()

    if not pipeline_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"pipeline with {id} not found")
    
    if pipeline_row.status == "ingesting":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail=f"Pipeline configuration cannot be modified while in 'ingesting' status.")

    update_data = payload.model_dump(exclude_unset=True, mode="json")

    for key, value in update_data.items():
        if key in ["name", "status"]:
            setattr(pipeline_row, key, value)
        else:
            current_config = dict(pipeline_row.config) if pipeline_row.config else {}
            current_config[key] = value
            
            pipeline_row.config = current_config


    try:
        return PipelineConfig(
            id=pipeline_row.id,
            name=pipeline_row.name,
            status=pipeline_row.status,
            created_at=pipeline_row.created_at,
            **pipeline_row.config
        )
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,detail=e.errors())








       