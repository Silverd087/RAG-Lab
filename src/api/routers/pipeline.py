from fastapi import APIRouter, Depends,status,HTTPException
from src.rag.models import PipelineConfig,PipelineUpdate
from src.database.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,update
from src.database.models.pipeline import PipelineModel,PipelineStatusEnum
import uuid

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
    
    await db.delete(pipeline_row)



@router.post("/pipelines",tags=['pipeline'],status_code=status.HTTP_201_CREATED,response_model=PipelineConfig)
async def get_pipeline_by_id(body:PipelineConfig,db:AsyncSession = Depends(get_db)):
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
    return PipelineConfig(
        id=body.id,
        name=body.name,
        status=body.status,
        created_at=body.created_at,
        **body.model_dump(exclude={"id", "name", "status", "created_at","error"})
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

    update_data = payload.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        if key in ["name", "status"]:
            setattr(pipeline_row, key, value)
        else:
            current_config = dict(pipeline_row.config) if pipeline_row.config else {}
            current_config[key] = value
            
            pipeline_row.config = current_config


    return PipelineConfig(
        id=pipeline_row.id,
        name=pipeline_row.name,
        status=pipeline_row.status,
        created_at=pipeline_row.created_at,
        **pipeline_row.config
    )


    





       