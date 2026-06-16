from src.rag.models import PipelineConfig,PipelinePresets
from src.rag.pipeline import run_pipeline
import json
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from ragas import evaluate
from datasets import Dataset
import asyncio
async def build_eval_dataset(golden_set:list,config:PipelineConfig):
    questions,ground_truths,answers,contexts = [],[],[],[]
    for item in golden_set:
        result,answer = await run_pipeline(config=config,query=item["question"])
        questions.append(item["question"])
        answers.append(answer)
        ground_truths.append(item["ground_truth"])
        contexts.append([c.content for c in result.chunks])

    return {
        "questions":questions,
        "ground_truths":ground_truths,
        "answers":answers,
        "contexts":contexts
    }


async def run_experiment():
    with open("eval/golden_set.json") as f:
        golden_set = json.load(f)

    config = PipelinePresets.baseline("eval-baseline")
    data = await build_eval_dataset(golden_set,config)
    dataset = Dataset.from_dict(data)

    scores = evaluate(
        dataset=dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall]
    )

    return scores

asyncio.run(run_experiment)