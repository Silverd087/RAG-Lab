from src.database.models.benchmark import BenchmarkModel
from src.api.routers.benchmark import _to_benchmark_response
from src.api.schema import BenchmarkResultResponse
import uuid
from datetime import datetime,timezone
class TestToBenchmarkResponse:
    async def test_returns_with_populated_results(self):
        dataset_id = uuid.uuid4()
        results = [
            {
                "pipeline_id":uuid.uuid4(),
                "status":"complete",
                "scores":{
                    "faithfulness": 0.85,
                    "answer_relevance": 0.92,
                    "context_precision": 0.78,
                    "context_recall": 0.88
                }
            },
            {   "pipeline_id":uuid.uuid4(),
                "status":"complete",
                "scores":{
                    "faithfulness": 0.90,
                    "answer_relevance": 0.95,
                    "context_precision": 0.82,
                    "context_recall": 0.91
                }
            }
        ]
        benchmark_row = BenchmarkModel(
            id=str(uuid.uuid4()),
            dataset_id=str(dataset_id),
            status="completed",
            results=results,
            error_log=None,
            created_at=datetime.now(timezone.utc)
        )        
        benchmark_response = _to_benchmark_response(benchmark_row)
        BenchmarkResultResponse.model_validate(benchmark_response)

    async def test_returns_with_no_populated_results(self):
        dataset_id = uuid.uuid4()
        benchmark_row = BenchmarkModel(
            id=str(uuid.uuid4()),
            dataset_id=str(dataset_id),
            status="completed",
            error_log=None,
            created_at=datetime.now(timezone.utc)
        )        
        benchmark_response = _to_benchmark_response(benchmark_row)
        BenchmarkResultResponse.model_validate(benchmark_response)