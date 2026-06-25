from src.rag.models import PipelinePresets,PipelineConfig,ChunkingConfig,ChunkingStrategy,RetrievalConfig,ModeConfig
import pytest
import asyncio
import uuid

pytestmark = pytest.mark.asyncio

class TestCreatePipeline:
    async def test_create_pipeline_returns_201(self,client):
        pipeline_config = PipelinePresets.baseline("test-baseline")
        payload = pipeline_config.model_dump(mode="json")
        response = await client.post(f"/api/v1/pipelines",json=payload)
        assert response.status_code == 201

    async def test_create_pipeline_returns_id(self,client):
        pipeline_config = PipelinePresets.baseline("test-baseline")
        payload = pipeline_config.model_dump(mode="json")
        response = await client.post(f"/api/v1/pipelines",json=payload)
        data = response.json()
        assert "id" in data

    async def test_create_pipeline_returns_default_status_draft(self,client):
        pipeline_config = PipelinePresets.baseline("test-baseline")
        payload = pipeline_config.model_dump(mode="json")
        response = await client.post(f"/api/v1/pipelines",json=payload)
        data = response.json()
        assert "status" in data
        assert data["status"] == "draft"
    
    async def test_create_pipeline_stores_correct_name(self,client):
        pipeline_config = PipelinePresets.baseline("test-baseline")
        payload = pipeline_config.model_dump(mode="json")
        response = await client.post(f"/api/v1/pipelines",json=payload)
        data = response.json()
        assert "name" in data
        assert data["name"] == "test-baseline"

    async def test_create_pipeline_stores_default_config(self,client):
        pipeline_config = PipelinePresets.baseline("test-baseline")
        payload = pipeline_config.model_dump(mode="json")
        response = await client.post(f"/api/v1/pipelines",json=payload)
        data = response.json()

        ignored_fields = {
            "id":True,
            "created_at":True
        }
        assert PipelineConfig(**(data)).model_dump(exclude=ignored_fields) == PipelinePresets.baseline("test-baseline").model_dump(exclude=ignored_fields)

    async def test_create_pipeline_empty_name_returns_422(self,client):
        pipeline_config = PipelinePresets.baseline("test-baseline")
        pipeline_config.name = ""
        payload = pipeline_config.model_dump(mode="json")
        response = await client.post(f"/api/v1/pipelines",json=payload)
        assert response.status_code == 422

    async def test_create_pipeline_missing_name_returns_422(self,client):
        pipeline_config = PipelinePresets.baseline("test-baseline")
        payload = pipeline_config.model_dump(mode="json")
        del payload["name"]
        response = await client.post(f"/api/v1/pipelines",json=payload)
        assert response.status_code == 422

    async def test_create_pipeline_with_custom_chunking_config(self,client):
        pipeline_config = PipelineConfig(
            name="custom-chunking",
            chunking=ChunkingConfig(
                strategy=ChunkingStrategy.SEMANTIC,
                chunk_size=600,
                overlap=60,
                parent_doc=True,
                parent_chunk_size=2500,
                parent_overlap=250
                )
            )
        payload = pipeline_config.model_dump(mode="json")
        response = await client.post(f"/api/v1/pipelines",json=payload)
        data = response.json()
        assert response.status_code == 201
        assert data["chunking"] == payload["chunking"]

    async def test_create_pipeline_with_custom_retrieval_config(self,client):
        pipeline_config = PipelineConfig(
            name="custom-retrieval",
            retrieval=RetrievalConfig(
                mode=ModeConfig.HYBRID,
                top_k= 3
            )
        )
        payload = pipeline_config.model_dump(mode="json")
        response = await client.post(f"/api/v1/pipelines",json=payload)
        data = response.json()
        assert response.status_code == 201
        assert data["retrieval"] == payload["retrieval"]

    async def test_two_pipelines_have_different_ids(self,client):
        pipeline_config_a = PipelinePresets.baseline("a")
        pipeline_config_b = PipelinePresets.baseline("b")

        payload_a = pipeline_config_a.model_dump(mode="json")
        payload_b = pipeline_config_b.model_dump(mode="json")

        response_a = client.post(f"/api/v1/pipelines",json=payload_a)
        response_b = client.post(f"/api/v1/pipelines",json=payload_b)

        result_a,result_b = await asyncio.gather(response_a,response_b)

        data_a = result_a.json()
        data_b = result_b.json()

        assert result_a.status_code == 201
        assert result_b.status_code == 201

        assert "id" in data_a
        assert "id" in data_b


        assert data_a["id"] != data_b["id"]

class TestGetPipeline:
    async def test_get_pipeline_returns_200(self,client,pipeline):
        response = await client.get(f"/api/v1/pipelines/{pipeline["id"]}")
        assert response.status_code == 200

    async def test_get_pipeline_returns_correct_id(self,client,pipeline):
        response = await client.get(f"/api/v1/pipelines/{pipeline["id"]}")
        data = response.json()
        assert data["id"] == pipeline["id"]

    async def test_get_pipeline_returns_correct_name(self,client,pipeline):
        response = await client.get(f"/api/v1/pipelines/{pipeline["id"]}")
        data = response.json()
        assert data["name"] == pipeline["name"]
    
    async def test_get_pipeline_returns_config(self,client,pipeline):
        response = await client.get(f"/api/v1/pipelines/{pipeline["id"]}")
        data = response.json()
        config = {k:v for k,v in data.items() if k not in {"id","created_at","name","status"}}
        assert config == pipeline["config"]

    async def test_get_nonexistent_pipeline_returns_404(self,client):
        id = uuid.uuid4()
        response = await client.get(f"/api/v1/pipelines/{id}")
        assert response.status_code == 404

    async def test_get_pipeline_invalid_uuid_returns_422(self,client):
        response = await client.get(f"/api/v1/pipelines/id")
        assert response.status_code == 422

class TestListPipelines:

    async def test_list_pipelines_returns_200(self,client,pipeline):
        response = await client.get("/api/v1/pipelines")
        assert response.status_code == 200

    async def test_list_pipelines_returns_empty_list_when_none_exist(self,client):
        response = await client.get("/api/v1/pipelines")
        data = response.json()
        assert data == []

    async def test_list_pipelines_returns_all_created_pipelines(self,client,pipeline):
        response = await client.get("/api/v1/pipelines")
        data = response.json()
        returned_ids = [item["id"] for item in data]
        assert str(pipeline["id"]) in returned_ids

    async def test_list_pipelines_returns_correct_fields(self,client,pipeline):
        response = await client.get("/api/v1/pipelines")
        assert response.status_code == 200
        
        for pipeline_data in response.json():
            PipelineConfig(**pipeline_data)
    

class TestDeletePipeline:
    async def test_delete_pipeline_returns_204(self,client,pipeline):
        response = await client.delete(f"/api/v1/pipelines/{pipeline["id"]}")
        assert response.status_code == 204

    async def test_delete_pipeline_removes_from_db(self,client,pipeline):
        delete_response = await client.delete(f"/api/v1/pipelines/{pipeline["id"]}")
        assert delete_response.status_code == 204

        get_response = await client.get(f"/api/v1/pipelines/{pipeline["id"]}")
        assert get_response.status_code == 404

    async def test_delete_nonexistent_pipeline_returns_404(self,client):
        random_id = uuid.uuid4()
        response = await client.delete(f"/api/v1/pipelines/{random_id}")
        assert response.status_code == 404

    ##async def test_delete_pipeline_cascades_to_results(self,client):
    ## TO DO

class TestUpdatePipeline:

    async def test_update_pipeline_name_returns_200(self,client,pipeline):
        response = await client.patch(f"/api/v1/pipelines/{pipeline["id"]}",json={"name":"test-patch"})
        data = response.json()
        assert response.status_code == 200
        assert data["name"] == "test-patch"

    async def test_update_pipeline_config_returns_200(self,client,pipeline):
        patch_payload = {
            "name": "test-patch",
            "chunking": {
                "strategy": "semantic",
                "chunk_size": 1000,
                "overlap": 50
            }
        }
        response = await client.patch(f"/api/v1/pipelines/{pipeline["id"]}",json=patch_payload)
        data = response.json()
        assert response.status_code == 200
        assert data["chunking"]["strategy"] == "semantic"
        assert data["chunking"]["chunk_size"] == 1000
        assert data["name"] == "test-patch"

    async def test_update_nonexistent_pipeline_returns_404(self,client):
        fake_id = uuid.uuid4()
        response = await client.patch(f"/api/v1/pipelines/{fake_id}",json={"name":"test-patch"})
        assert response.status_code == 404

    async def test_cannot_update_pipeline_while_ingesting(self,client,pipeline):
        patch_payload = {"status":"ingesting"}
        response = await client.patch(f"/api/v1/pipelines/{pipeline["id"]}",json=patch_payload)

        assert response.status_code == 200

        patch_payload = {
            "name": "test-patch",
            "chunking": {
                "strategy": "semantic",
                "chunk_size": 1000,
                "overlap": 50
            }
        }
        
        response = await client.patch(f"/api/v1/pipelines/{pipeline["id"]}",json=patch_payload)
        assert response.status_code == 409





