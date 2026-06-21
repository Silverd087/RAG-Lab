from celery import shared_task,Task
from src.rag.models import PipelineConfig
from src.storage.minio_client import get_minio_client
from config import settings
from src.rag.ingest import run_ingest
import tempfile
import os
from sqlalchemy.orm import Session
from src.database.sync_session import get_sync_db
from src.database.models.pipeline import PipelineModel


def update_pipeline_status(db:Session,pipeline_id:str,status:str,error:str=None):
    pipeline = db.query(PipelineModel).filter(PipelineModel.id == pipeline_id).first()
    if not pipeline:
        raise ValueError(f"Pipeline {pipeline_id} not found")
    pipeline.status = status
    if error:
        pipeline.error = error


@shared_task
def ingest_task(config_dict:dict,object_name:str,)->None:
    pipeline_config = PipelineConfig.model_validate(config_dict)
    minio_client = get_minio_client()
    response = None
    tmp_path = None
    try:
        with get_sync_db() as db:
            update_pipeline_status(db,pipeline_config.id,status="ingesting")

        response = minio_client.get_object(
            bucket_name=settings.minio_bucket_name,
            object_name=object_name
            )
        with tempfile.NamedTemporaryFile(suffix=".pdf",delete=False) as tmp:
            tmp.write(response.read())
            tmp_path = tmp.name
        
        run_ingest(tmp_path,pipeline_config)

        with get_sync_db() as db:
            update_pipeline_status(db,pipeline_config.id,status="ready")
    except Exception as e:
            with get_sync_db() as db:
                update_pipeline_status(db=db,pipeline_id=pipeline_config.id,status="error",error=str(e))

    finally:
        if response:
            response.close()
            response.release_conn()
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)