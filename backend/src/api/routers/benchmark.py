from fastapi import APIRouter, Depends, HTTPException,status
from src.api.schema import BenchmarkRequest,BenchmarkResultResponse,BenchmarkListResponse,PipelineScores
from sqlalchemy import select
from src.database.models.pipeline import PipelineModel
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.session import get_db
from src.database.models.pipeline import PipelineStatusEnum
from src.api.task import evaluate_single_pipeline,aggregate_benchmark_results
from celery import chord
from src.database.models.benchmark import BenchmarkModel,DatasetModel
from sqlalchemy.orm import joinedload
import uuid

router = APIRouter()


def _to_benchmark_response(row: BenchmarkModel) -> BenchmarkResultResponse:
    results = None
    if row.results is not None:
        results = [PipelineScores.model_validate(r) for r in row.results]
    return BenchmarkResultResponse(
        id=row.id,
        dataset_id=row.dataset_id,
        status=row.status,
        created_at=row.created_at,
        results=results,
        error=row.error_log,
    )

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

    return _to_benchmark_response(benchmark)

@router.get("/benchmarks",tags=["benchmark"],response_model=BenchmarkListResponse)
async def get_benchmarks(db:AsyncSession=Depends(get_db)):

    stmt = select(BenchmarkModel).options(joinedload(BenchmarkModel.dataset)).order_by(BenchmarkModel.created_at.desc())
    result = await db.execute(stmt)

    benchmark_rows = result.scalars().all()
    return BenchmarkListResponse(benchmarks=[_to_benchmark_response(row) for row in benchmark_rows])

@router.get("/benchmarks/{benchmark_id}",tags=["benchmark"],response_model=BenchmarkResultResponse)
async def get_benchmark_by_id(benchmark_id:uuid.UUID,db:AsyncSession=Depends(get_db)):

    stmt = select(BenchmarkModel).where(BenchmarkModel.id == benchmark_id)
    result = await db.execute(stmt)
    benchmark_row = result.scalar_one_or_none()

    if not benchmark_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="benchmark id not found")

    return _to_benchmark_response(benchmark_row)