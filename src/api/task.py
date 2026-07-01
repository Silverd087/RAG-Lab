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
from src.database.models.pipeline_result import PipelineResultModel
from fastapi import Depends
from sqlalchemy import select
from deepeval.metrics import FaithfulnessMetric, AnswerRelevancyMetric, ContextualPrecisionMetric, ContextualRecallMetric
from deepeval.test_case import LLMTestCase
from deepeval.dataset import EvaluationDataset
from deepeval import evaluate
from src.rag.core import get_llm
from sqlalchemy.orm import joinedload
from src.api.schema import DeepEvalScores,DeepEvalResponse

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


@shared_task
def run_deep_eval(result_id1:str,result_id2:str,config_1_dict:dict,config_2_dict:dict,db:Session=get_sync_db()):

    stmt = (
        select(PipelineResultModel)
        .options(joinedload(PipelineResultModel.chunks))
        .where(PipelineResultModel.id == result_id1)
    )    
    result = db.execute(stmt)
    pipeline_result1 = result.scalar_one_or_none()


    stmt = (
        select(PipelineResultModel)
        .options(joinedload(PipelineResultModel.chunks))
        .where(PipelineResultModel.id == result_id2)
    )  
    result = db.execute(stmt)
    pipeline_result2 = result.scalar_one_or_none()

    pipeline_results = [pipeline_result1,pipeline_result2]

    test_cases = []

    for p in pipeline_results:
        test_case = LLMTestCase(input=p.query,
                                actual_output=p.answer,
                                context=[chunk.content for chunk in p.chunks])
        test_cases.append(test_case)

    dataset = EvaluationDataset(test_cases)

    config1 = PipelineConfig.model_validate(config_1_dict)
    config2 = PipelineConfig.model_validate(config_2_dict)
    eval_model = get_llm(config1)

    metrics = [
        FaithfulnessMetric(threshold=0.7, model=eval_model),
        AnswerRelevancyMetric(threshold=0.7, model=eval_model),
        ContextualPrecisionMetric(threshold=0.7, model=eval_model),
        ContextualRecallMetric(threshold=0.7, model=eval_model)
    ]

    results = evaluate(test_cases=dataset,metrics=metrics)

    return (
        DeepEvalResponse(
            scores_1=DeepEvalScores(faithulness=result.test_result[0].metrics_data[0].score,
                       answer_relevance=results.test_results[0].metrics_data[1].score,
                       context_precision=results.test_results[0].metrics_data[2].score,
                       context_recall=results.test_results[0].metrics_data[3].score
                       ),
            scores_2=DeepEvalScores(faithulness=result.test_result[1].metrics_data[0].score,
                        answer_relevance=results.test_results[1].metrics_data[1].score,
                        context_precision=results.test_results[1].metrics_data[2].score,
                        context_recall=results.test_results[1].metrics_data[3].score
                       )
        )

    )

