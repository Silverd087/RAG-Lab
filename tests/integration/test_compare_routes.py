from src.rag.models import PipelineResult
import uuid
from sqlalchemy import select
from src.database.models.pipeline_result import PipelineResultModel
class TestComparePipelines:
    async def test_compare_returns_200(self,client,two_ready_pipelines):
        pipeline_1 = two_ready_pipelines[0]
        pipeline_2 = two_ready_pipelines[1]
        payload = {
            "pipeline_id1": pipeline_1["id"],
            "pipeline_id2":pipeline_2["id"],
            "query":"what is attention"
        }
        response = await client.post("/api/v1/compare",json=payload)

        assert response.status_code == 200

    async def test_compare_returns_both_pipeline_results(self,client,two_ready_pipelines):
        pipeline_1 = two_ready_pipelines[0]
        pipeline_2 = two_ready_pipelines[1]
        payload = {
            "pipeline_id1": pipeline_1["id"],
            "pipeline_id2":pipeline_2["id"],
            "query":"what is attention"
        }
        response = await client.post("/api/v1/compare",json=payload)
        
        data = response.json()


        assert "result1" in data
        assert "result2" in data

        assert PipelineResult.model_validate(data["result1"])
        assert PipelineResult.model_validate(data["result2"])

    async def test_compare_returns_answer_for_each_pipeline(self,client,two_ready_pipelines):
        pipeline_1 = two_ready_pipelines[0]
        pipeline_2 = two_ready_pipelines[1]
        payload = {
            "pipeline_id1": pipeline_1["id"],
            "pipeline_id2":pipeline_2["id"],
            "query":"what is attention"
        }
        response = await client.post("/api/v1/compare",json=payload)
        
        data = response.json()
        
        assert data["result1"]["answer"] is not None
        assert data["result2"]["answer"] is not None
        assert isinstance(data["result1"]["answer"],str)
        assert isinstance(data["result2"]["answer"],str)

    async def test_compare_returns_chunks_for_each_pipeline(self,client,two_ready_pipelines):
        pipeline_1 = two_ready_pipelines[0]
        pipeline_2 = two_ready_pipelines[1]
        payload = {
            "pipeline_id1": pipeline_1["id"],
            "pipeline_id2":pipeline_2["id"],
            "query":"what is attention"
        }
        response = await client.post("/api/v1/compare",json=payload)
        
        data = response.json()
                
        assert data["result1"]["chunks"] is not None
        assert data["result2"]["chunks"] is not None
        assert isinstance(data["result1"]["chunks"],list)
        assert isinstance(data["result2"]["chunks"],list)

    async def test_compare_returns_latency_for_each_pipeline(self,client,two_ready_pipelines):
        pipeline_1 = two_ready_pipelines[0]
        pipeline_2 = two_ready_pipelines[1]
        payload = {
            "pipeline_id1": pipeline_1["id"],
            "pipeline_id2":pipeline_2["id"],
            "query":"what is attention"
        }
        response = await client.post("/api/v1/compare",json=payload)
        
        data = response.json()

        assert data["result1"]["latency"] is not None
        assert data["result2"]["latency"] is not None
        assert isinstance(data["result1"]["latency"],dict)
        assert isinstance(data["result2"]["latency"],dict)

    async def test_compare_nonexistent_pipeline_1_returns_404(self,client,two_ready_pipelines):
        pipeline_1 = str(uuid.uuid4())
        pipeline_2 = two_ready_pipelines[1]
        payload = {
            "pipeline_id1": pipeline_1,
            "pipeline_id2":pipeline_2["id"],
            "query":"what is attention"
        }
        response = await client.post("/api/v1/compare",json=payload)
        
        assert response.status_code == 404

    async def test_compare_nonexistent_pipeline_2_returns_404(self,client,two_ready_pipelines):
        pipeline_1 = two_ready_pipelines[0]
        pipeline_2 = str(uuid.uuid4())
        payload = {
            "pipeline_id1": pipeline_1["id"],
            "pipeline_id2":pipeline_2,
            "query":"what is attention"
        }
        response = await client.post("/api/v1/compare",json=payload)
        
        assert response.status_code == 404

    async def test_compare_pipeline_1_not_ready_returns_400(self,client,two_ready_pipelines):

        pipeline_1 = two_ready_pipelines[0]
        pipeline_2 = two_ready_pipelines[1]

        response = await client.patch(f"/api/v1/pipelines/{pipeline_1["id"]}",json={"status":"draft"})

        payload = {
            "pipeline_id1": pipeline_1["id"],
            "pipeline_id2":pipeline_2["id"],
            "query":"what is attention"
        }
        response = await client.post("/api/v1/compare",json=payload)

        response.status_code == 400
    
    async def test_compare_pipeline_2_not_ready_returns_400(self,client,two_ready_pipelines):


        pipeline_1 = two_ready_pipelines[0]
        pipeline_2 = two_ready_pipelines[1]

        response = await client.patch(f"/api/v1/pipelines/{pipeline_2["id"]}",json={"status":"draft"})

        payload = {
            "pipeline_id1": pipeline_1["id"],
            "pipeline_id2":pipeline_2["id"],
            "query":"what is attention"
        }
        response = await client.post("/api/v1/compare",json=payload)

        response.status_code == 400

    async def test_compare_same_pipeline_twice_returns_200(self,client,ready_pipeline):
        payload = {
            "pipeline_id1": ready_pipeline["id"],
            "pipeline_id2":ready_pipeline["id"],
            "query":"what is attention"
        }
        response = await client.post("/api/v1/compare",json=payload)

        response.status_code == 422
    
    async def test_compare_empty_query_returns_422(self,client,two_ready_pipelines):
        pipeline_1 = two_ready_pipelines[0]
        pipeline_2 = two_ready_pipelines[1]

        payload = {
            "pipeline_id1": pipeline_1["id"],
            "pipeline_id2":pipeline_2["id"],
            "query":""
        }

        response = await client.post("/api/v1/compare",json=payload)

        response.status_code == 422

    async def test_compare_stores_both_results_in_db(self,client,two_ready_pipelines,db_session):
        pipeline_1 = two_ready_pipelines[0]
        pipeline_2 = two_ready_pipelines[1]

        payload = {
            "pipeline_id1": pipeline_1["id"],
            "pipeline_id2":pipeline_2["id"],
            "query":"what is attention"
        }

        response = await client.post("/api/v1/compare",json=payload)
        data = response.json()

        stmt = select(PipelineResultModel).where(PipelineResultModel.id == data["result1"]["id"])
        query_result = await db_session.execute(stmt)
        result_1 = query_result.scalar_one_or_none()

        stmt = select(PipelineResultModel).where(PipelineResultModel.id == data["result2"]["id"])
        query_result = await db_session.execute(stmt)
        result_2 = query_result.scalar_one_or_none()
    
        assert result_1 is not None
        assert result_2 is not None

