from fastapi import APIRouter, Depends
from rag.models import PipelineConfig
from database.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import pipeline_config
router = APIRouter()

@router.get("/pipelines",tags=['pipeline'])
def get_all_pipelines(db:AsyncSession = Depends(get_db))->list[PipelineConfig]:
    stmt = select(pipeline_config)
    pipelines = db.execute(stmt).all()