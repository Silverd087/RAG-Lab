from sqlalchemy import select
from src.database.models.benchmark import BenchmarkModel
import uuid

class TestRunBenchmark:
    async def test_run_benchmark_returns_202(self,client,dataset,two_ready_pipelines):
        payload = {
            "pipeline_ids":[p["id"] for p in two_ready_pipelines],
            "dataset_id":dataset["id"]
        }
        response = await client.post("/api/v1/benchmarks",json=payload)
        assert response.status_code == 202

    async def test_run_benchmark_returns_benchmark_id(self,client,dataset,two_ready_pipelines):
        payload = {
            "pipeline_ids":[p["id"] for p in two_ready_pipelines],
            "dataset_id":dataset["id"]
        }
        response = await client.post("/api/v1/benchmarks",json=payload)
        data = response.json()
        assert "benchmark_id" in data
        assert isinstance(data["benchmark_id"],str)

    
    async def test_run_benchmark_returns_pending_status(self,client,dataset,two_ready_pipelines):
        payload = {
            "pipeline_ids":[p["id"] for p in two_ready_pipelines],
            "dataset_id":dataset["id"]
        }
        response = await client.post("/api/v1/benchmarks",json=payload)
        data = response.json()
        assert "status" in data
        assert data["status"] == "pending"    
    async def test_run_benchmark_stores_benchmark_in_db(self,client,dataset,two_ready_pipelines,db_session):
        payload = {
            "pipeline_ids":[p["id"] for p in two_ready_pipelines],
            "dataset_id":dataset["id"]
        }
        response = await client.post("/api/v1/benchmarks",json=payload)
        data = response.json()

        stmt = select(BenchmarkModel).where(BenchmarkModel.id == data["benchmark_id"])
        result = await db_session.execute(stmt)

        benchmark_row = result.scalar_one_or_none()

        assert benchmark_row is not None

    async def test_run_benchmark_pipeline_not_found_returns_404(self,client,dataset):
        id = str(uuid.uuid4())
        payload = {
            "pipeline_ids":[id],
            "dataset_id":dataset["id"]
        }
        response = await client.post("/api/v1/benchmarks",json=payload)
        assert response.status_code == 404

    async def test_run_benchmark_partial_pipelines_not_found_returns_404(self,client,dataset,ready_pipeline):
        id = str(uuid.uuid4())
        payload = {
            "pipeline_ids":[id,ready_pipeline["id"]],
            "dataset_id":dataset["id"]
        }
        response = await client.post("/api/v1/benchmarks",json=payload)
        assert response.status_code == 404


    async def test_run_benchmark_pipeline_not_ready_returns_400(self,client,dataset,two_ready_pipelines):
        pipeline_1 = two_ready_pipelines[0]
        response = await client.patch(f"/api/v1/pipelines/{pipeline_1["id"]}",json={"status":"draft"})
        payload = {
            "pipeline_ids":[p["id"] for p in two_ready_pipelines],
            "dataset_id":dataset["id"]
        }
        response = await client.post("/api/v1/benchmarks",json=payload)
        assert response.status_code == 400

    async def test_run_benchmark_dataset_not_found_returns_404(self,client,two_ready_pipelines):
        dataset_id = str(uuid.uuid4())
        payload = {
            "pipeline_ids":[p["id"] for p in two_ready_pipelines],
            "dataset_id":dataset_id
        }
        response = await client.post("/api/v1/benchmarks",json=payload)

        assert response.status_code == 404

    async def test_run_benchmark_empty_pipeline_ids_returns_422(self,client,dataset,two_ready_pipelines):
        payload = {
            "pipeline_ids":[],
            "dataset_id":dataset["id"]
        }
        response = await client.post("/api/v1/benchmarks",json=payload)

        assert response.status_code == 422

    async def test_run_benchmark_missing_dataset_id_returns_422(self,client,two_ready_pipelines):
        payload = {
            "pipeline_ids":[p["id"] for p in two_ready_pipelines],
            "dataset_id":""
        }
        response = await client.post("/api/v1/benchmarks",json=payload)

        assert response.status_code == 422
    
    async def test_run_benchmark_enqueues_celery_chord(self,client,dataset,two_ready_pipelines,mock_celery_chord):
        payload = {
            "pipeline_ids":[p["id"] for p in two_ready_pipelines],
            "dataset_id":dataset["id"]
        }
        response = await client.post("/api/v1/benchmarks",json=payload)

        mock_celery_chord.assert_called_once()
        mock_celery_chord.return_value.assert_called_once()


    async def test_run_benchmark_multiple_pipelines_enqueues_task_per_pipeline(self,client,dataset,two_ready_pipelines,mock_celery_chord):
        p1 , p2 = two_ready_pipelines
        payload = {
            "pipeline_ids":[p["id"] for p in two_ready_pipelines],
            "dataset_id":dataset["id"]
        }
        response = await client.post("/api/v1/benchmarks",json=payload)

        chord_call_args = mock_celery_chord.call_args
        header = chord_call_args.kwargs["header"]

        assert len(header) == 2

        pipeline_ids_in_tasks = [task.pipeline_id for task in header]
        pipeline_ids_in_tasks = list(map(lambda x: str(x),pipeline_ids_in_tasks))
        assert str(p1["id"]) in pipeline_ids_in_tasks
        assert str(p2["id"]) in pipeline_ids_in_tasks