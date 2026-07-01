from fastapi import APIRouter, Depends, HTTPException,status
from src.api.schema import BenchmarkRequest
from sqlalchemy import select
from src.database.models.pipeline import PipelineModel
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.session import get_db
from src.database.models.pipeline import PipelineStatusEnum

router = APIRouter()

@router.post("/benchmarks",tags=["benchmark"])
async def run_benchmark(payload:BenchmarkRequest,db:AsyncSession = Depends(get_db)):
    pipeline_ids = payload.pipeline_ids

    stmt = select(PipelineModel).where(PipelineModel.id.in_(pipeline_ids))
    result = await db.execute(stmt)
    pipeline_rows = result.scalars().all()

    if not pipeline_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="pipeline ids not foud")
    
    for pipeline in pipeline_rows:
        if pipeline.status != PipelineStatusEnum.READY:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="pipeline ids not foud")

    