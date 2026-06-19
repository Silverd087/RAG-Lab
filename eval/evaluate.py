from src.rag.models import PipelineConfig,PipelinePresets
from src.rag.pipeline import run_pipeline
import json
import asyncio
from deepeval.test_case import LLMTestCase
from deepeval.dataset import EvaluationDataset
from deepeval import evaluate
from deepeval.metrics import FaithfulnessMetric, AnswerRelevancyMetric, ContextualPrecisionMetric, ContextualRecallMetric
from src.rag.core import get_llm
from src.rag.ingest import run_ingest
async def build_eval_test_cases(golden_set:list,config:PipelineConfig)->EvaluationDataset:
    file_path="sample_document.pdf"
    run_ingest(file=file_path,config=config)
    test_cases = []
    for item in golden_set:
        result,answer = await run_pipeline(config=config,query=item["question"])

        test_case = LLMTestCase(input=item["question"],
                        expected_output=item["ground_truth"],
                        actual_output=answer,
                        context=[c.content for c in result.chunks])
        
        test_cases.append(test_case)

    return EvaluationDataset(test_cases)


async def run_experiment():
    with open("eval/golden_set.json") as f:
        golden_set = json.load(f)

    config = PipelinePresets.baseline("eval-baseline")
    test_cases = await build_eval_test_cases(golden_set,config)
    eval_model = get_llm(config)

    metrics = [
        FaithfulnessMetric(threshold=0.7, model=eval_model),
        AnswerRelevancyMetric(threshold=0.7, model=eval_model),
        ContextualPrecisionMetric(threshold=0.7, model=eval_model),
        ContextualRecallMetric(threshold=0.7, model=eval_model)
    ]

    result = evaluate(test_cases=test_cases,metrics=metrics)
    print(result)

asyncio.run(run_experiment())