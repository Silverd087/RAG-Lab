from celery.result import AsyncResult
from fastapi import APIRouter
from src.api.schema import JobStatusResponse

router = APIRouter()

@router.get("/jobs/{job_id}",tags=["jobs"],response_model=JobStatusResponse)
def get_job_status(job_id:str):
    result = AsyncResult(job_id)
    if result.state == "PENDING":
        return JobStatusResponse(job_id=job_id,status="pending")
    elif result.state == "FAILURE":
        return JobStatusResponse(job_id=job_id,status="failed",error=str(result.info))
    elif result.state == "SUCCESS":
        data = result.result
        return JobStatusResponse(job_id=job_id,status="complete",scores_1=data["scores_1"],scores_2=data["scores_2"])
    


