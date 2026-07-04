from fastapi import APIRouter, Depends, HTTPException,status
from src.api.schema import BenchmarkRequest,BenchmarkResultResponse
from sqlalchemy import select
from src.database.models.pipeline import PipelineModel
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.session import get_db
from src.database.models.pipeline import PipelineStatusEnum
from src.api.task import evaluate_single_pipeline,aggregate_benchmark_results
from celery import chord
from src.database.models.benchmark import BenchmarkModel,DatasetModel
from sqlalchemy.orm import joinedload

router = APIRouter()

@router.post("/benchmarks",tags=["benchmark"],status_code=status.HTTP_202_ACCEPTED,response_model=BenchmarkResultResponse)
async def run_benchmark(payload:BenchmarkRequest,db:AsyncSession = Depends(get_db)):
    pipeline_ids = payload.pipeline_ids

    stmt = select(PipelineModel).where(PipelineModel.id.in_(pipeline_ids))
    result = await db.execute(stmt)
    pipeline_rows = result.scalars().all()

    if not pipeline_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="pipeline ids not foud")

    if len(pipeline_rows) != len(pipeline_ids):
        found_ids = {str(p.id) for p in pipeline_rows}
        missing = [pid for pid in pipeline_ids if str(pid) not in found_ids]
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipelines not found: {missing}"
        )
    
    for pipeline in pipeline_rows:
        if pipeline.status != PipelineStatusEnum.READY:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f"Pipeline {pipeline.id} is not ready — status: {pipeline.status.value}")

    stmt = select(DatasetModel).where(DatasetModel.id == payload.dataset_id)
    result = await db.execute(stmt)
    dataset_row = result.scalar_one_or_none()

    if not dataset_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="dataset id not foud")


    benchmark = BenchmarkModel(
        dataset_id=dataset_row.id,
        status= "pending"
    )

    db.add(benchmark)
    await db.flush()


    header = [
        evaluate_single_pipeline.s(pipeline.id,dataset_row.id) for pipeline in pipeline_rows
    ]


    callback = aggregate_benchmark_results.s(benchmark.id)

    chord(header=header)(callback)

    return BenchmarkResultResponse(
        benchmark_id = benchmark.id,
        status= benchmark.status
    )
    