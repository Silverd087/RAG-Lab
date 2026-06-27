import uuid
from sqlalchemy import select
from src.database.models.pipeline_result import PipelineResultModel
from src.rag.models import ChunkTrace
class TestQueryPipeline:
    async def test_query_returns_200(self,client,ready_pipeline):
        response = await client.post(f"/api/v1/pipelines/{ready_pipeline["id"]}/query",json={"query":"what is attention"})
        assert response.status_code == 200

    async def test_query_returns_answer(self,client,ready_pipeline):
        response = await client.post(f"/api/v1/pipelines/{ready_pipeline["id"]}/query",json={"query":"what is attention"})
        data = response.json()
        assert "answer" in data
        assert isinstance(data["answer"],str)

    async def test_query_returns_chunks(self,client,ready_pipeline):
        response = await client.post(f"/api/v1/pipelines/{ready_pipeline["id"]}/query",json={"query":"what is attention"})
        data = response.json()
        assert "chunks" in data
        assert isinstance(data["chunks"],list)

    async def test_query_returns_latency(self,client,ready_pipeline):
        response = await client.post(f"/api/v1/pipelines/{ready_pipeline["id"]}/query",json={"query":"what is attention"})
        data = response.json()
        assert "latency" in data
        assert isinstance(data["latency"],dict)
    
    async def test_query_returns_pipeline_id(self,client,ready_pipeline):
        response = await client.post(f"/api/v1/pipelines/{ready_pipeline["id"]}/query",json={"query":"what is attention"})
        data = response.json()
        assert "pipeline_id" in data
        assert isinstance(data["pipeline_id"],str)
        assert data["pipeline_id"] == ready_pipeline["id"]

    async def test_query_empty_string_returns_422(self,client,ready_pipeline):
        response = await client.post(f"/api/v1/pipelines/{ready_pipeline["id"]}/query",json={"query":""})
        assert response.status_code == 422

    async def test_query_whitespace_only_returns_422(self,client,ready_pipeline):
        response = await client.post(f"/api/v1/pipelines/{ready_pipeline["id"]}/query",json={"query":"   "})
        assert response.status_code == 422

    async def test_query_pipeline_not_ready_returns_400(self,client,pipeline):
        response = await client.post(f"/api/v1/pipelines/{pipeline["id"]}/query",json={"query":"what is attention"})
        response.status_code == 400

    async def test_query_nonexistent_pipeline_returns_404(self,client):
        id = uuid.uuid4()
        response = await client.post(f"/api/v1/pipelines/{id}/query",json={"query":"what is attention"})
        response.status_code == 400

    async def test_query_stores_result_in_db(self,client,db_session,ready_pipeline):
        response = await client.post(f"/api/v1/pipelines/{ready_pipeline["id"]}/query",json={"query":"what is attention"})
        assert response.status_code == 200
        data = response.json()
        stmt = select(PipelineResultModel).where(PipelineResultModel.pipeline_id == ready_pipeline["id"])
        result = await db_session.execute(stmt)
        pipeline_row = result.scalar_one_or_none()
        assert pipeline_row is not None


    async def test_query_result_has_correct_pipeline_id(self,client,ready_pipeline):
        response = await client.post(f"/api/v1/pipelines/{ready_pipeline["id"]}/query",json={"query":"what is attention"})
        data = response.json()
        assert "pipeline_id" in data
        assert data["pipeline_id"] == ready_pipeline["id"]

    async def test_query_chunks_have_required_fields(self,client,ready_pipeline):
        response = await client.post(f"/api/v1/pipelines/{ready_pipeline["id"]}/query",json={"query":"what is attention"})
        data = response.json()
        assert "chunks" in data
        assert isinstance(data["chunks"],list)
        for chunk in data["chunks"]:
            assert ChunkTrace.model_validate(chunk)