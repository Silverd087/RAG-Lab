from sqlalchemy import select
from src.database.models.benchmark import DatasetItemModel,DatasetModel
import uuid
class TestCreateDataset:
    async def test_create_dataset_returns_201(self,client):
        payload = {
            "name":"test-dataset",
            "description":"toy dataset for integration tests",
            "items":[
                {
                "question": "What are the specific BLEU scores achieved by the Transformer model on the WMT 2014 English-to-German and English-to-French translation tasks?",
                "ground_truth": "The Transformer model achieves a BLEU score of 28.4 on the WMT 2014 English-to-German translation task, improving over existing best results and ensembles by over 2 BLEU. On the WMT 2014 English-to-French translation task, it establishes a new single-model state-of-the-art BLEU score of 41.0."
                }
            ]
        }
        response = await client.post("/api/v1/datasets",json=payload)

        assert response.status_code == 201
    async def test_create_dataset_returns_id(self,client):
        payload = {
            "name":"test-dataset",
            "description":"toy dataset for integration tests",
            "items":[
                {
                "question": "What are the specific BLEU scores achieved by the Transformer model on the WMT 2014 English-to-German and English-to-French translation tasks?",
                "ground_truth": "The Transformer model achieves a BLEU score of 28.4 on the WMT 2014 English-to-German translation task, improving over existing best results and ensembles by over 2 BLEU. On the WMT 2014 English-to-French translation task, it establishes a new single-model state-of-the-art BLEU score of 41.0."
                }
            ]
        }
        response = await client.post("/api/v1/datasets",json=payload)

        data = response.json()
        assert "id" in data
        assert isinstance(data["id"],str)

    async def test_create_dataset_returns_correct_name(self,client):
        payload = {
            "name":"test-dataset",
            "description":"toy dataset for integration tests",
            "items":[
                {
                "question": "What are the specific BLEU scores achieved by the Transformer model on the WMT 2014 English-to-German and English-to-French translation tasks?",
                "ground_truth": "The Transformer model achieves a BLEU score of 28.4 on the WMT 2014 English-to-German translation task, improving over existing best results and ensembles by over 2 BLEU. On the WMT 2014 English-to-French translation task, it establishes a new single-model state-of-the-art BLEU score of 41.0."
                }
            ]
        }
        response = await client.post("/api/v1/datasets",json=payload)

        data = response.json()
        assert "name" in data
        assert isinstance(data["name"],str)
        assert data["name"] == "test-dataset"


    async def test_create_dataset_stores_items(self,client,db_session):
        payload = {
            "name":"test-dataset",
            "description":"toy dataset for integration tests",
            "items":[
                {
                "question": "What are the specific BLEU scores achieved by the Transformer model on the WMT 2014 English-to-German and English-to-French translation tasks?",
                "ground_truth": "The Transformer model achieves a BLEU score of 28.4 on the WMT 2014 English-to-German translation task, improving over existing best results and ensembles by over 2 BLEU. On the WMT 2014 English-to-French translation task, it establishes a new single-model state-of-the-art BLEU score of 41.0."
                }
            ]
        }
        response = await client.post("/api/v1/datasets",json=payload)
        data = response.json()
        stmt = select(DatasetItemModel).where(DatasetItemModel.dataset_id == data["id"])
        result = await db_session.execute(stmt)
        items = result.scalars().all()
        assert len(items) == 1

    async def test_create_dataset_returns_items(self,client):
        payload = {
            "name":"test-dataset",
            "description":"toy dataset for integration tests",
            "items":[
                {
                "question": "What are the specific BLEU scores achieved by the Transformer model on the WMT 2014 English-to-German and English-to-French translation tasks?",
                "ground_truth": "The Transformer model achieves a BLEU score of 28.4 on the WMT 2014 English-to-German translation task, improving over existing best results and ensembles by over 2 BLEU. On the WMT 2014 English-to-French translation task, it establishes a new single-model state-of-the-art BLEU score of 41.0."
                }
            ]
        }
        response = await client.post("/api/v1/datasets",json=payload)

        data = response.json()
        assert "items" in data
        assert isinstance(data["items"],list)
        assert len(data["items"]) == 1
    async def test_create_dataset_missing_name_returns_422(self,client):
        payload = {
            "description":"toy dataset for integration tests",
            "items":[
                {
                "question": "What are the specific BLEU scores achieved by the Transformer model on the WMT 2014 English-to-German and English-to-French translation tasks?",
                "ground_truth": "The Transformer model achieves a BLEU score of 28.4 on the WMT 2014 English-to-German translation task, improving over existing best results and ensembles by over 2 BLEU. On the WMT 2014 English-to-French translation task, it establishes a new single-model state-of-the-art BLEU score of 41.0."
                }
            ]
        }
        response = await client.post("/api/v1/datasets",json=payload)

        assert response.status_code == 422

    async def test_create_dataset_empty_name_returns_422(self,client):
        payload = {
            "name":"",
            "description":"toy dataset for integration tests",
            "items":[
                {
                "question": "What are the specific BLEU scores achieved by the Transformer model on the WMT 2014 English-to-German and English-to-French translation tasks?",
                "ground_truth": "The Transformer model achieves a BLEU score of 28.4 on the WMT 2014 English-to-German translation task, improving over existing best results and ensembles by over 2 BLEU. On the WMT 2014 English-to-French translation task, it establishes a new single-model state-of-the-art BLEU score of 41.0."
                }
            ]
        }
        response = await client.post("/api/v1/datasets",json=payload)

        assert response.status_code == 422
    
    async def test_create_dataset_empty_items_returns_422(self,client):
        payload = {
            "name":"test-dataset",
            "description":"toy dataset for integration tests",
            "items":[]
        }
        response = await client.post("/api/v1/datasets",json=payload)

        assert response.status_code == 422

    async def test_create_dataset_item_missing_question_returns_422(self,client):
        payload = {
            "name":"test-dataset",
            "description":"toy dataset for integration tests",
            "items":[
                {
                "ground_truth": "The Transformer model achieves a BLEU score of 28.4 on the WMT 2014 English-to-German translation task, improving over existing best results and ensembles by over 2 BLEU. On the WMT 2014 English-to-French translation task, it establishes a new single-model state-of-the-art BLEU score of 41.0."
                }
            ]
        }
        response = await client.post("/api/v1/datasets",json=payload)

        assert response.status_code == 422

    async def test_create_dataset_item_missing_ground_truth_returns_422(self,client):
        payload = {
            "name":"test-dataset",
            "description":"toy dataset for integration tests",
            "items":[
                {
                "question": "What are the specific BLEU scores achieved by the Transformer model on the WMT 2014 English-to-German and English-to-French translation tasks?",
                }
            ]
        }
        response = await client.post("/api/v1/datasets",json=payload)

        response.status_code == 422

class TestGetDataset:
    async def test_get_dataset_returns_200(self,client,dataset):
        response = await client.get(f"/api/v1/datasets/{dataset["id"]}")

        assert response.status_code == 200

    async def test_get_dataset_returns_correct_id(self,client,dataset):
        response = await client.get(f"/api/v1/datasets/{dataset["id"]}")
        data = response.json()
        assert "id" in data
        assert data["id"] == dataset["id"]


    async def test_get_dataset_returns_correct_name(self,client,dataset):
        response = await client.get(f"/api/v1/datasets/{dataset["id"]}")
        data = response.json()
        assert "name" in data
        assert isinstance(data["name"],str)
        assert data["name"] == dataset["name"]

    async def test_get_dataset_returns_items(self,client,dataset):
        response = await client.get(f"/api/v1/datasets/{dataset["id"]}")
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"],list)
        assert data["items"] == dataset["items"]

    
    async def test_get_dataset_items_have_question_and_ground_truth(self,client,dataset):
        response = await client.get(f"/api/v1/datasets/{dataset["id"]}")
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"],list)
        for item in data["items"]:
            assert "question" in item
            assert "ground_truth" in item
            assert isinstance(item["question"],str)
            assert isinstance(item["ground_truth"],str)
    
    async def test_get_nonexistent_dataset_returns_404(self,client):
        dataset_id = str(uuid.uuid4())
        response = await client.get(f"/api/v1/datasets/{dataset_id}")
        assert response.status_code == 404


    async def test_get_dataset_invalid_uuid_returns_422(self,client,dataset):
        dataset_id = uuid.uuid4()
        response = await client.get(f"/api/v1/datasets/{dataset_id}")
        assert response.status_code == 404


class TestListDatasets:
    async def test_list_datasets_returns_200(self,client,datasets):
        response = await client.get(f"/api/v1/datasets")
        assert response.status_code == 200

    async def test_list_datasets_returns_empty_when_none_exist(self,client):
        response = await client.get(f"/api/v1/datasets")
        data = response.json()
        data == []
    async def test_list_datasets_returns_all_datasets(self,client,datasets):
        response = await client.get(f"/api/v1/datasets")
        data = response.json()
        assert len(datasets) == len(data)
                
    async def test_list_datasets_does_not_return_items(self,client,datasets):
        response = await client.get(f"/api/v1/datasets")
        data = response.json()
        assert all("items" not in dataset for dataset in data)


class TestDeleteDataset:
    async def test_delete_dataset_returns_204(self,client,dataset):
        response = await client.delete(f"/api/v1/datasets/{dataset["id"]}")
        assert response.status_code == 204

    async def test_delete_dataset_removes_from_db(self,client,dataset,db_session):
        response = await client.delete(f"/api/v1/datasets/{dataset["id"]}")
        stmt = select(DatasetModel).where(DatasetModel.id == dataset["id"])
        result = await db_session.execute(stmt)
        dataset_row = result.scalar_one_or_none()
        assert dataset_row is None

    async def test_delete_dataset_cascades_to_items(self,client,dataset,db_session):
        response = await client.delete(f"/api/v1/datasets/{dataset["id"]}")
        stmt = select(DatasetItemModel).where(DatasetItemModel.dataset_id == dataset["id"])
        result = await db_session.execute(stmt)
        dataset_item_rows = result.scalars().all()
        assert len(dataset_item_rows) == 0
        assert dataset_item_rows == []

    async def test_delete_nonexistent_dataset_returns_404(self,client,dataset,db_session):
        dataset_id = uuid.uuid4()
        response = await client.delete(f"/api/v1/datasets/{dataset_id}")
        assert response.status_code == 404


class TestAddDatasetItems:
    async def test_add_items_returns_200(self,client,dataset):
        payload = {
            "items":[{
            "question": "How many layers (N) make up the identical blocks in both the encoder and the decoder stacks of the Transformer architecture?",
            "ground_truth": "Both the encoder and the decoder stacks are composed of an orchestration stack of N = 6 identical layers."
        }]}
        response = await client.post(f"/api/v1/datasets/{dataset["id"]}/items",json=payload)
        assert response.status_code == 200

    async def test_add_items_increases_item_count(self,client,dataset):
        payload = {
            "items":[{
            "question": "How many layers (N) make up the identical blocks in both the encoder and the decoder stacks of the Transformer architecture?",
            "ground_truth": "Both the encoder and the decoder stacks are composed of an orchestration stack of N = 6 identical layers."
        }]}
        response = await client.post(f"/api/v1/datasets/{dataset["id"]}/items",json=payload)
        data = response.json()
        assert len(data["items"]) == len(dataset["items"])+1

    async def test_add_items_to_nonexistent_dataset_returns_404(self,client):
        dataset_id = uuid.uuid4()
        payload = {
            "items":[{
            "question": "How many layers (N) make up the identical blocks in both the encoder and the decoder stacks of the Transformer architecture?",
            "ground_truth": "Both the encoder and the decoder stacks are composed of an orchestration stack of N = 6 identical layers."
        }]}
        response = await client.post(f"/api/v1/datasets/{dataset_id}/items",json=payload)
        assert response.status_code == 404

    async def test_add_items_empty_list_returns_422(self,client,dataset):
        response = await client.post(f"/api/v1/datasets/{dataset["id"]}/items",json=[])
        assert response.status_code == 422

        
    async def test_add_items_missing_question_returns_422(self,client,dataset):
        payload = {
            "items":[{
            "ground_truth": "Both the encoder and the decoder stacks are composed of an orchestration stack of N = 6 identical layers."
        }]}
        response = await client.post(f"/api/v1/datasets/{dataset["id"]}/items",json=payload)
        assert response.status_code == 422
    async def test_add_items_missing_ground_truth_returns_422(self,client,dataset):
        payload = {
            "items":[{
            "question": "How many layers (N) make up the identical blocks in both the encoder and the decoder stacks of the Transformer architecture?",
        }]}
        response = await client.post(f"/api/v1/datasets/{dataset["id"]}/items",json=payload)
        assert response.status_code == 422

class TestDeleteDatasetItem:
    async def test_delete_item_returns_204(self,client,dataset):
        response = await client.delete(f"/api/v1/datasets/{dataset["id"]}/items/{dataset["items"][0]["id"]}")
        assert response.status_code == 204

    async def test_delete_item_removes_from_dataset(self,client,dataset,db_session):
        response = await client.delete(f"/api/v1/datasets/{dataset["id"]}/items/{dataset["items"][0]["id"]}")
        stmt = select(DatasetItemModel).where(DatasetItemModel.id == dataset["items"][0]["id"])
        result = await db_session.execute(stmt)
        dataset_item = result.scalar_one_or_none()
        assert dataset_item is None

    async def test_delete_nonexistent_item_returns_404(self,client,dataset):
        item_id = uuid.uuid4()
        response = await client.delete(f"/api/v1/datasets/{dataset["id"]}/items/{item_id}")
        assert response.status_code == 404


    async def test_delete_item_from_nonexistent_dataset_returns_404(self,client):
        dataset_id = uuid.uuid4()
        item_id = uuid.uuid4()
        response = await client.delete(f"/api/v1/datasets/{dataset_id}/items/{item_id}")
        assert response.status_code == 404


