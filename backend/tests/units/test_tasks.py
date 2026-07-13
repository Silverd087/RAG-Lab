import os
import uuid
import pytest
from contextlib import contextmanager
from unittest.mock import MagicMock, AsyncMock
from src.api.task import (
    update_pipeline_status,
    build_benchmark_dataset,
    ingest_task,
    run_deep_eval,
    evaluate_single_pipeline,
    aggregate_benchmark_results,
)


@pytest.fixture
def mock_db(mocker):
    db = MagicMock()

    @contextmanager
    def fake_get_sync_db():
        yield db

    mocker.patch("src.api.task.get_sync_db", fake_get_sync_db)
    return db


@pytest.fixture
def mock_metrics(mocker):
    for metric in [
        "FaithfulnessMetric",
        "AnswerRelevancyMetric",
        "ContextualPrecisionMetric",
        "ContextualRecallMetric",
    ]:
        mocker.patch(f"src.api.task.{metric}", return_value=MagicMock())
    mocker.patch("src.api.task.get_llm", return_value=MagicMock())


def make_eval_results(scores_per_case: list[list[float]]):
    """Build a fake deepeval result: one test_result per case, 4 metric scores each"""
    results = MagicMock()
    test_results = []
    for scores in scores_per_case:
        test_result = MagicMock()
        test_result.metrics_data = [MagicMock(score=s) for s in scores]
        test_results.append(test_result)
    results.test_results = test_results
    return results


class TestUpdatePipelineStatus:
    def test_sets_status(self):
        db = MagicMock()
        pipeline = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = pipeline
        update_pipeline_status(db, "pipeline-id", status="ready")
        assert pipeline.status == "ready"

    def test_sets_error_when_given(self):
        db = MagicMock()
        pipeline = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = pipeline
        update_pipeline_status(db, "pipeline-id", status="error", error="boom")
        assert pipeline.status == "error"
        assert pipeline.error == "boom"

    def test_raises_when_pipeline_not_found(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(ValueError):
            update_pipeline_status(db, "missing-id", status="ready")


class TestBuildBenchmarkDataset:
    async def test_builds_one_test_case_per_golden_item(self, mocker, base_config, fake_docs):
        result = MagicMock()
        result.chunks = [MagicMock(content=doc.page_content) for doc in fake_docs]
        mocker.patch("src.api.task.run_pipeline", AsyncMock(return_value=(result, "the answer")))

        golden_set = [
            {"question": "q1", "ground_truth": "gt1"},
            {"question": "q2", "ground_truth": "gt2"},
        ]
        dataset = await build_benchmark_dataset(golden_set, base_config)
        assert len(dataset.test_cases) == 2

    async def test_test_case_maps_pipeline_output(self, mocker, base_config, fake_docs):
        result = MagicMock()
        result.chunks = [MagicMock(content=doc.page_content) for doc in fake_docs]
        mocker.patch("src.api.task.run_pipeline", AsyncMock(return_value=(result, "the answer")))

        golden_set = [{"question": "q1", "ground_truth": "gt1"}]
        dataset = await build_benchmark_dataset(golden_set, base_config)
        test_case = dataset.test_cases[0]
        assert test_case.input == "q1"
        assert test_case.expected_output == "gt1"
        assert test_case.actual_output == "the answer"
        assert test_case.retrieval_context == [doc.page_content for doc in fake_docs]


class TestIngestTask:
    @pytest.fixture
    def minio_response(self, mock_minio_client):
        """Configure the conftest minio mock to return a readable object"""
        response = MagicMock()
        response.read.return_value = b"pdf bytes"
        mock_minio_client.get_object.return_value = response
        return response

    @pytest.fixture
    def mock_update_status(self, mocker):
        return mocker.patch("src.api.task.update_pipeline_status")

    @pytest.fixture
    def mock_run_ingest(self, mocker):
        return mocker.patch("src.api.task.run_ingest")

    def test_marks_pipeline_ingesting_then_ready(self, mock_db, minio_response, mock_update_status, mock_run_ingest, base_config):
        ingest_task(base_config.model_dump(mode="json"), "pipelines/x/file.pdf")
        statuses = [c.kwargs.get("status") for c in mock_update_status.call_args_list]
        assert statuses == ["ingesting", "ready"]

    def test_runs_ingest_on_downloaded_file(self, mock_db, minio_response, mock_update_status, mock_run_ingest, base_config):
        ingest_task(base_config.model_dump(mode="json"), "pipelines/x/file.pdf")
        mock_run_ingest.assert_called_once()
        tmp_path, config = mock_run_ingest.call_args.args
        assert tmp_path.endswith(".pdf")
        assert str(config.id) == str(base_config.id)

    def test_cleans_up_temp_file_and_connection(self, mock_db, minio_response, mock_update_status, mock_run_ingest, base_config):
        ingest_task(base_config.model_dump(mode="json"), "pipelines/x/file.pdf")
        tmp_path = mock_run_ingest.call_args.args[0]
        assert not os.path.exists(tmp_path)
        minio_response.close.assert_called_once()
        minio_response.release_conn.assert_called_once()

    def test_marks_pipeline_error_on_failure(self, mock_db, minio_response, mock_update_status, mock_run_ingest, base_config):
        mock_run_ingest.side_effect = RuntimeError("boom")
        ingest_task(base_config.model_dump(mode="json"), "pipelines/x/file.pdf")
        last_call = mock_update_status.call_args_list[-1]
        assert last_call.kwargs["status"] == "error"
        assert last_call.kwargs["error"] == "boom"

    def test_fetches_object_from_configured_bucket(self, mock_db, mock_minio_client, minio_response, mock_update_status, mock_run_ingest, base_config):
        from config import settings

        ingest_task(base_config.model_dump(mode="json"), "pipelines/x/file.pdf")
        mock_minio_client.get_object.assert_called_once_with(
            bucket_name=settings.minio_bucket_name,
            object_name="pipelines/x/file.pdf",
        )


class TestRunDeepEval:
    @pytest.fixture
    def pipeline_result_rows(self, fake_docs):
        rows = []
        for answer in ["answer a", "answer b"]:
            row = MagicMock()
            row.query = "what is attention"
            row.answer = answer
            row.chunks = [MagicMock(content=doc.page_content) for doc in fake_docs]
            rows.append(row)
        return rows

    @pytest.fixture
    def comparison_row(self):
        row = MagicMock()
        row.evaluation_scores = None
        row.status = "pending"
        return row

    @pytest.fixture
    def deep_eval_db(self, mock_db, pipeline_result_rows, comparison_row):
        result_1 = MagicMock()
        result_1.unique.return_value.scalar_one_or_none.return_value = pipeline_result_rows[0]
        result_2 = MagicMock()
        result_2.unique.return_value.scalar_one_or_none.return_value = pipeline_result_rows[1]
        result_3 = MagicMock()
        result_3.scalar_one_or_none.return_value = comparison_row
        mock_db.execute.side_effect = [result_1, result_2, result_3]
        return mock_db

    def test_stores_scores_and_completes_comparison(self, mocker, deep_eval_db, comparison_row, mock_metrics, base_config, hyde_config):
        mocker.patch(
            "src.api.task.evaluate",
            return_value=make_eval_results([[0.9, 0.8], [0.5, 0.4]]),
        )
        run_deep_eval(
            comparison_id="comparison-id",
            result_id1="result-1",
            result_id2="result-2",
            config_1_dict=base_config.model_dump(mode="json"),
            config_2_dict=hyde_config.model_dump(mode="json"),
        )
        assert comparison_row.status == "completed"
        assert comparison_row.evaluation_scores["pipeline_a"] == {
            "faithfulness": 0.9,
            "answer_relevance": 0.8,
            "context_precision": None,
            "context_recall": None,
        }
        assert comparison_row.evaluation_scores["pipeline_b"] == {
            "faithfulness": 0.5,
            "answer_relevance": 0.4,
            "context_precision": None,
            "context_recall": None,
        }

    def test_evaluates_one_test_case_per_pipeline_result(self, mocker, deep_eval_db, mock_metrics, base_config, hyde_config):
        mock_evaluate = mocker.patch(
            "src.api.task.evaluate",
            return_value=make_eval_results([[0.9, 0.8, 0.7, 0.6], [0.5, 0.4, 0.3, 0.2]]),
        )
        run_deep_eval(
            comparison_id="comparison-id",
            result_id1="result-1",
            result_id2="result-2",
            config_1_dict=base_config.model_dump(mode="json"),
            config_2_dict=hyde_config.model_dump(mode="json"),
        )
        test_cases = mock_evaluate.call_args.kwargs["test_cases"]
        assert len(test_cases) == 2
        assert test_cases[0].actual_output == "answer a"
        assert test_cases[1].actual_output == "answer b"


class TestEvaluateSinglePipeline:
    @pytest.fixture
    def pipeline_row(self, base_config):
        row = MagicMock()
        row.id = base_config.id
        row.name = base_config.name
        row.created_at = base_config.created_at
        row.status = "ready"
        row.config = base_config.model_dump(exclude={"id", "status", "created_at", "name"})
        return row

    @pytest.fixture
    def dataset_row(self):
        row = MagicMock()
        row.items = [{"question": "q1", "ground_truth": "gt1"}]
        return row

    @pytest.fixture
    def single_eval_db(self, mock_db, pipeline_row, dataset_row):
        result_1 = MagicMock()
        result_1.scalar_one_or_none.return_value = pipeline_row
        result_2 = MagicMock()
        result_2.scalar_one_or_none.return_value = dataset_row
        mock_db.execute.side_effect = [result_1, result_2]
        return mock_db

    @pytest.fixture
    def mock_build_dataset(self, mocker):
        return mocker.patch("src.api.task.build_benchmark_dataset", AsyncMock(return_value=MagicMock()))

    def test_returns_mean_scores_on_success(self, mocker, single_eval_db, mock_build_dataset, mock_metrics, base_config):
        mocker.patch(
            "src.api.task.evaluate",
            return_value=make_eval_results([[1.0, 1.0, 1.0, 1.0], [0.5, 0.7, 0.9, 0.3]]),
        )
        result = evaluate_single_pipeline(str(base_config.id), "dataset-id")
        assert result["status"] == "success"
        assert result["pipeline_id"] == str(base_config.id)
        assert result["scores"] == {
            "faithfulness": 0.75,
            "answer_relevance": 0.85,
            "context_precision": 0.95,
            "context_recall": 0.65,
        }
        assert result["error"] is None

    def test_returns_failed_status_on_exception(self, mock_db, mock_metrics, base_config):
        mock_db.execute.side_effect = RuntimeError("db down")
        result = evaluate_single_pipeline(str(base_config.id), "dataset-id")
        assert result["status"] == "failed"
        assert result["scores"] is None
        assert "db down" in result["error"]


class TestAggregateBenchmarkResults:
    @pytest.fixture
    def benchmark_row(self):
        from datetime import datetime, timezone

        row = MagicMock()
        row.dataset_id = uuid.uuid4()
        row.created_at = datetime.now(timezone.utc)
        row.status = "running"
        row.error_log = None
        return row

    @pytest.fixture
    def scores(self):
        return {
            "faithfulness": 0.9,
            "answer_relevance": 0.8,
            "context_precision": 0.7,
            "context_recall": 0.6,
        }

    def test_completes_when_all_succeed(self, mock_db, benchmark_row, scores):
        mock_db.execute.return_value.scalar_one_or_none.return_value = benchmark_row
        results = [
            {"pipeline_id": str(uuid.uuid4()), "status": "success", "scores": scores, "error": None},
            {"pipeline_id": str(uuid.uuid4()), "status": "success", "scores": scores, "error": None},
        ]
        benchmark_id = str(uuid.uuid4())
        response = aggregate_benchmark_results(results, benchmark_id)
        assert benchmark_row.status == "completed"
        assert benchmark_row.error_log is None
        assert response["status"] == "completed"
        assert len(response["results"]) == 2

    def test_completes_with_errors_when_some_fail(self, mock_db, benchmark_row, scores):
        mock_db.execute.return_value.scalar_one_or_none.return_value = benchmark_row
        results = [
            {"pipeline_id": str(uuid.uuid4()), "status": "success", "scores": scores, "error": None},
            {"pipeline_id": str(uuid.uuid4()), "status": "failed", "scores": None, "error": "boom"},
        ]
        response = aggregate_benchmark_results(results, str(uuid.uuid4()))
        assert benchmark_row.status == "completed_with_errors"
        assert "1 item(s)" in benchmark_row.error_log
        assert len(response["results"]) == 1

    def test_stores_all_results_on_row(self, mock_db, benchmark_row, scores):
        mock_db.execute.return_value.scalar_one_or_none.return_value = benchmark_row
        results = [
            {"pipeline_id": str(uuid.uuid4()), "status": "success", "scores": scores, "error": None},
        ]
        aggregate_benchmark_results(results, str(uuid.uuid4()))
        assert benchmark_row.results == results
