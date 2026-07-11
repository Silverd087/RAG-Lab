from celery import shared_task,Task
from src.celery_app import celery_app
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
from src.api.schema import PipelineScores,DeepEvalResponse,BenchmarkResultResponse,DeepEvalScores
from src.rag.pipeline import run_pipeline
import asyncio
from src.database.models.benchmark import DatasetModel,BenchmarkModel
from sqlalchemy.orm import joinedload
from src.database.models.compare import ComparisonModel

def update_pipeline_status(db:Session,pipeline_id:str,status:str,error:str=None):
    pipeline = db.query(PipelineModel).filter(PipelineModel.id == pipeline_id).first()
    if not pipeline:
        raise ValueError(f"Pipeline {pipeline_id} not found")
    pipeline.status = status
    if error:
        pipeline.error = error


async def build_benchmark_dataset(golden_set:list,config:PipelineConfig):

    test_cases = []
    for item in golden_set:
        result,answer = await run_pipeline(config=config,query=item["question"])

        test_case = LLMTestCase(input=item["question"],
                        expected_output=item["ground_truth"],
                        actual_output=answer,
                        context=[c.content for c in result.chunks])
        
        test_cases.append(test_case)
    dataset = EvaluationDataset()
    dataset.test_cases = test_cases
    return dataset

@shared_task(queue="ingestion")
def ingest_task(config_dict:dict,object_name:str)->None:
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


@shared_task(queue="evaluation")
def run_deep_eval(comparison_id:str,result_id1:str,result_id2:str,config_1_dict:dict,config_2_dict:dict):

    with get_sync_db() as db:
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

        dataset = EvaluationDataset()
        dataset.test_cases = test_cases

        config1 = PipelineConfig.model_validate(config_1_dict)
        config2 = PipelineConfig.model_validate(config_2_dict)
        eval_model = get_llm(config1)

        metrics = [
            FaithfulnessMetric(threshold=0.7, model=eval_model),
            AnswerRelevancyMetric(threshold=0.7, model=eval_model),
            ContextualPrecisionMetric(threshold=0.7, model=eval_model),
            ContextualRecallMetric(threshold=0.7, model=eval_model)
        ]

        results = evaluate(test_cases=dataset.test_cases,metrics=metrics)

        scores = []
        for test_case_result in results.test_results:
            m_data = test_case_result.metrics_data

            pipeline_score = DeepEvalScores(
                faithfulness=m_data[0].score,
                answer_relevance=m_data[1].score,
                context_precision=m_data[2].score,
                context_recall=m_data[3].score
            )
            scores.append(pipeline_score)

        stmt = select(ComparisonModel).where(ComparisonModel.id == comparison_id)
        result = db.execute(stmt)
        comparison_id_row = result.scalar_one_or_none()
        if comparison_id_row:
           comparison_id_row.evaluation_scores = {
                    "pipeline_a": scores[0].model_dump(),
                    "pipeline_b": scores[1].model_dump()
                }
           comparison_id_row.status = "completed"


@shared_task(queue="evaluation")
def evaluate_single_pipeline(pipeline_id:str,dataset_id:str):
    try:
        with get_sync_db() as db:
            stmt = select(PipelineModel).where(PipelineModel.id == pipeline_id)
            result = db.execute(stmt)

            pipeline_row = result.scalar_one_or_none()

            pipeline_config = PipelineConfig(
                id=pipeline_row.id, name=pipeline_row.name, created_at=pipeline_row.created_at, status=pipeline_row.status, **pipeline_row.config
                )

            stmt = select(DatasetModel).options(joinedload(DatasetModel.items)).where(DatasetModel.id == dataset_id)
            result = db.execute(stmt)

            dataset_row = result.scalar_one_or_none()

            dataset = asyncio.run(build_benchmark_dataset(golden_set=dataset_row.items,config=pipeline_config))

        eval_model = get_llm(pipeline_config)

        metrics = [
            FaithfulnessMetric(threshold=0.7, model=eval_model),
            AnswerRelevancyMetric(threshold=0.7, model=eval_model),
            ContextualPrecisionMetric(threshold=0.7, model=eval_model),
            ContextualRecallMetric(threshold=0.7, model=eval_model)
        ]

        result = evaluate(test_cases=dataset.test_cases,metrics=metrics)

        total_faithfulness = 0.0
        total_relevance = 0.0
        total_precision = 0.0
        total_recall = 0.0
        num_cases = len(result.test_results)

        for test_case in result.test_results:

            total_faithfulness += test_case.metrics_data[0].score
            total_relevance += test_case.metrics_data[1].score
            total_precision += test_case.metrics_data[2].score
            total_recall += test_case.metrics_data[3].score

        mean_scores = DeepEvalScores(
            faithfulness=round(total_faithfulness / num_cases, 2) if num_cases > 0 else 0,
            answer_relevance=round(total_relevance / num_cases, 2) if num_cases > 0 else 0,
            context_precision=round(total_precision / num_cases, 2) if num_cases > 0 else 0,
            context_recall=round(total_recall / num_cases, 2) if num_cases > 0 else 0
        )
        return  PipelineScores(
            pipeline_id=pipeline_id,
            scores=mean_scores,
            status="success"
        ).model_dump(mode="json")
    except Exception as e:
        return  PipelineScores(
            pipeline_id=pipeline_id,
            scores=None,
            status="failed",
            error=str(e)
        ).model_dump(mode="json")

@shared_task(queue="evaluation")
def aggregate_benchmark_results(results:list[dict],benchmark_id:str):
    successes = [r for r in results if r["status"] == "success"]
    failures = [r for r in results if r["status"] == "failed"]

    with get_sync_db() as db:
        stmt = select(BenchmarkModel).where(BenchmarkModel.id == benchmark_id)
        result = db.execute(stmt)

        benchmark_row = result.scalar_one_or_none()

        benchmark_row.results = results

        if failures:
            benchmark_row.status = "completed_with_errors"
            benchmark_row.error_log = f"Failed evaluation runs: {len(failures)} item(s)."
        else:
            benchmark_row.status = "completed"

        response = BenchmarkResultResponse(
            id=benchmark_id,
            dataset_id=benchmark_row.dataset_id,
            status=benchmark_row.status,
            created_at=benchmark_row.created_at,
            results=[PipelineScores.model_validate(r) for r in successes],
            error=benchmark_row.error_log,
        )

    return response.model_dump(mode="json")