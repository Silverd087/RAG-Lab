from fastapi import APIRouter, Depends,status,HTTPException
from src.rag.models import PipelineConfig
from src.database.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,delete
from src.database.models.pipeline import PipelineModel,PipelineStatusEnum
import uuid
from src.rag.pipeline import run_pipeline

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

@router.delete("/pipelines/{id}",tags=['pipeline'],status_code=status.HTTP_204_NO_CONTENT,response_model=PipelineConfig)
async def delete_pipeline_by_id(id:uuid.UUID,db:AsyncSession = Depends(get_db))->PipelineConfig:
    stmt = select(PipelineModel).where(PipelineModel.id == id)
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



@router.post("/pipelines",tags=['pipeline'],status_code=status.HTTP_201_CREATED,response_model=PipelineConfig)
async def get_pipeline_by_id(body:PipelineConfig,db:AsyncSession = Depends(get_db))->PipelineConfig:
    if not body:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Invalid request: config body is empty")
    new_pipeline = PipelineModel(
        id=body.id,
        name=body.name,
        status=body.status,
        created_at=body.created_at,
        config=body.model_dump(exclude={"id", "name", "status", "created_at","error"})
    )
    db.add(new_pipeline)
    return body


@router.get("/pipelines/{id}/status",tags=["pipeline"],status_code=status.HTTP_200_OK,response_model=PipelineStatusEnum)
async def get_pipeline_status(id:uuid.UUID,db:AsyncSession=Depends(get_db))->PipelineStatusEnum:
    stmt = select(PipelineModel).where(PipelineModel.id == id)

    result = await db.execute(stmt)

    pipeline_row = result.scalar_one_or_none()

    if not pipeline_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"pipeline with {id} not found")
    
    return pipeline_row.status









    





       