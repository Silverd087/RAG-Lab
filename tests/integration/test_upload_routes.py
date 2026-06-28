import uuid
import pytest
from unittest.mock import MagicMock, AsyncMock


pytestmark = pytest.mark.asyncio

class TestUploadDocument:
    async def test_upload_pdf_returns_202(self,client,pipeline):
            response = await client.post(f"/api/v1/pipelines/{pipeline["id"]}/upload",
                                         files={"file": ("test.pdf", b"%PDF-1.4", "application/pdf")})
            assert response.status_code == 202


    async def test_upload_pdf_sets_status_to_ingesting(slef,client,pipeline):
            response = await client.post(f"/api/v1/pipelines/{pipeline["id"]}/upload",
                                         files={"file": ("test.pdf", b"%PDF-1.4", "application/pdf")})

            data = response.json()
            assert data["status"] == "ingesting"

    async def test_upload_enqueues_celery_task(self,client,pipeline,mock_celery_task):
        response = await client.post(f"/api/v1/pipelines/{pipeline["id"]}/upload",
                                    files={"file": ("test.pdf", b"%PDF-1.4", "application/pdf")})
        
        mock_celery_task["documents"].assert_called_once()

    async def test_upload_non_pdf_returns_400(self,client,pipeline):
        response = await client.post(f"/api/v1/pipelines/{pipeline["id"]}/upload",
                                    files={"file": ("test.txt", b"hello world", "text/plain")})
        assert response.status_code == 400

    async def test_upload_to_nonexistent_pipeline_returns_404(self,client):
        id = uuid.uuid4()
        response = await client.post(f"/api/v1/pipelines/{id}/upload",
                                    files={"file": ("test.pdf", b"%PDF-1.4", "application/pdf")})
        
        assert response.status_code == 404

    async def test_upload_empty_file_returns_400(self,client,pipeline):
        response = await client.post(f"/api/v1/pipelines/{pipeline["id"]}/upload",
                                    files={"file": ("test.pdf", b"", "application/pdf")})
        assert response.status_code == 400

    async def test_upload_returns_job_id(self,client,pipeline):
        response = await client.post(f"/api/v1/pipelines/{pipeline["id"]}/upload",
                                    files={"file": ("test.pdf", b"%PDF-1.4", "application/pdf")})
        data = response.json()

        assert "job_id" in data
        assert isinstance(data["job_id"],str)
     