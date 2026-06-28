import asyncio
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker, AsyncSession
from src.database.models.base import Base
import pytest
from src.main import app  
from src.database.session import get_db
from httpx import AsyncClient,ASGITransport
from config import settings
from src.rag.models import PipelinePresets
from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from langchain_community.chat_models.fake import FakeMessagesListChatModel
import pytest_asyncio
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from langchain_core.prompts import ChatPromptTemplate
from unittest.mock import MagicMock,AsyncMock
from src.database.models.pipeline import PipelineModel

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(url=f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}/{settings.postgres_test_db}",poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture(scope="session")
async def session_factory(test_engine):
    return async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

@pytest_asyncio.fixture(autouse=True)
async def clean_db(test_engine):
    yield
    async with test_engine.begin() as conn:
        await conn.execute(text("TRUNCATE chunk_traces, pipeline_results, pipeline_config RESTART IDENTITY CASCADE"))

@pytest_asyncio.fixture
async def db_session(session_factory):
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest.fixture
async def client(db_session:AsyncSession):
    async def _override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = _override_get_db
    
    async with AsyncClient(transport=ASGITransport(app=app),base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()

@pytest.fixture
def fake_docs()->list[Document]:
    return [
        Document(
            page_content="Chunk 1",
            metadata={"source": "test.pdf", "page": 0, "score": 0.95}
        ),
        Document(
            page_content="Chunk 2",
            metadata={"source": "test.pdf", "page": 1, "score": 0.88}
        ),
        Document(
            page_content="Chunk 3",
            metadata={"source": "test.pdf", "page": 2, "score": 0.81}
        ),
    ]

@pytest.fixture
def duplicate_docs(fake_docs)->list[Document]:
    return fake_docs + fake_docs


@pytest.fixture
def base_config():
    return PipelinePresets.baseline("test-baseline")

@pytest.fixture
def hyde_config():
    return PipelinePresets.rag_hyde("test_hyde")

@pytest.fixture
def hyde_hybrid_config():
    return PipelinePresets.hyde_hybrid("test-hyde-hybrid")


@pytest.fixture
def multi_query_config():
    return PipelinePresets.rag_multiquery("test-multi-query")

@pytest.fixture
def step_back_config():
    return PipelinePresets.rag_step_back("test-step-back")

@pytest.fixture
def rag_fusion_config():
    return PipelinePresets.rag_fusion("test-rag-fusion")

@pytest.fixture
def parent_rerank_config():
    return PipelinePresets.parent_rerank("test-parent-rerank")

@pytest.fixture
def cross_encoder_config():
    return PipelinePresets.rag_cross_encoder("test-cross-encoder")

@pytest.fixture
def fusion_config():
    return PipelinePresets.rag_fusion("test-fusion")

@pytest.fixture
def reorder_config():
    return PipelinePresets.rag_reorder("test-reorder")

@pytest.fixture
def mock_llm():
    return FakeMessagesListChatModel(
        responses=[
            AIMessage(content="This is a mock response.")
        ]
    )

@pytest.fixture(autouse=True)
def mock_get_llm(mocker,mock_llm):
    mocker.patch("src.rag.steps.query_translation.get_llm",return_value=mock_llm)
    mocker.patch("src.rag.steps.generation.get_llm",return_value=mock_llm)

@pytest.fixture(autouse=True)
def mock_get_embedding(mocker):
    embeddings = MagicMock()
    embeddings.embed_query.return_value = [0.1] * 768
    mocker.patch("src.rag.core.get_embeddings",return_value=embeddings)
    mocker.patch("src.rag.steps.retrieval.get_embeddings",return_value=embeddings)

@pytest.fixture(autouse=True)
def mock_get_client(mocker):
    client = MagicMock()
    client.collection_exists.return_value = True
    mocker.patch("src.rag.ingest.get_client",return_value=client)

@pytest.fixture(autouse=True)
def mock_get_vectorstore(mocker,fake_docs):
    vectorstore = MagicMock()
    vectorstore.similarity_search_with_score.return_value = [(doc,doc.metadata["score"]) for doc in fake_docs]
    vectorstore.max_marginal_relevance_search_with_score_by_vector.retun_value = [(doc,doc.metadata["score"]) for doc in fake_docs]
    vectorstore.add_documents.return_value = MagicMock(return_value=None)

    mocker.patch("src.rag.ingest.get_vectorstore",return_value=vectorstore)
    mocker.patch("src.rag.steps.retrieval.get_vectorstore",return_value=vectorstore)

@pytest.fixture(autouse=True)
def mock_get_parent_doc_retriever(mocker,fake_docs):
    retriever = MagicMock()
    retriever.add_documents.return_value = MagicMock(return_value=None)
    retriever.ainvoke = AsyncMock()
    retriever.ainvoke.return_value = fake_docs
    mocker.patch("src.rag.ingest.get_parent_doc_retriever", return_value=retriever)
    mocker.patch("src.rag.steps.retrieval.get_parent_doc_retriever", return_value=retriever)


@pytest.fixture(autouse=True)
def mock_get_splitter(mocker):
    splitter = MagicMock()
    splitter.split_documents.return_value = []
    mocker.patch("src.rag.ingest.get_splitter", return_value=splitter)
    mocker.patch("src.rag.core.get_splitter", return_value=splitter)

@pytest.fixture(autouse=True)
def mock_get_prompt(mocker):
    prompt = ChatPromptTemplate.from_template("Context: {context}\nQuestion: {question}")
    mocker.patch("src.rag.steps.generation.get_prompt", return_value=prompt)


@pytest.fixture(autouse=True)
def mock_cross_encoder(mocker):
    cross_encoder = MagicMock()
    cross_encoder.score.return_value = [0.9,0.8,0.7]
    mocker.patch("src.rag.steps.post_retrieval.get_cross_encoder",return_value=cross_encoder)

@pytest_asyncio.fixture
async def pipeline(db_session):
    pipeline_config = PipelinePresets.baseline("test-baseline")
    pipeline_model =  PipelineModel(
        id=pipeline_config.id,
        name=pipeline_config.name,
        config=pipeline_config.model_dump(exclude={"id","status","created_at","name"})
        )
    db_session.add(pipeline_model)
    await db_session.commit()
    return {
        "id": str(pipeline_model.id),
        "name": pipeline_model.name,
        "status": pipeline_model.status,
        "created_at": pipeline_model.created_at.isoformat(),
        "config": pipeline_model.config,
    }

@pytest_asyncio.fixture
async def ready_pipeline(db_session):
    pipeline_config = PipelinePresets.baseline("test-baseline")
    pipeline_model =  PipelineModel(
        id=pipeline_config.id,
        name=pipeline_config.name,
        status="ready",
        config=pipeline_config.model_dump(exclude={"id","status","created_at","name"})
        )
    db_session.add(pipeline_model)
    await db_session.commit()

    return {
        "id": str(pipeline_model.id),
        "name": pipeline_model.name,
        "status": pipeline_model.status,
        "created_at": pipeline_model.created_at.isoformat(),
        "config": pipeline_model.config,
    }

@pytest_asyncio.fixture
async def ready_hyde_pipeline(db_session):
    pipeline_config = PipelinePresets.rag_hyde("test-hyde")
    pipeline_model =  PipelineModel(
        id=pipeline_config.id,
        name=pipeline_config.name,
        status="ready",
        config=pipeline_config.model_dump(exclude={"id","status","created_at","name"})
        )
    db_session.add(pipeline_model)
    await db_session.commit()
    return {
        "id": str(pipeline_model.id),
        "name": pipeline_model.name,
        "status": pipeline_model.status,
        "created_at": pipeline_model.created_at.isoformat(),
        "config": pipeline_model.config,
    }

@pytest_asyncio.fixture
async def ready_multiquery_pipeline(db_session):
    pipeline_config = PipelinePresets.rag_multiquery("test-hyde")
    pipeline_model =  PipelineModel(
        id=pipeline_config.id,
        name=pipeline_config.name,
        status="ready",
        config=pipeline_config.model_dump(exclude={"id","status","created_at","name"})
        )
    db_session.add(pipeline_model)
    await db_session.commit()
    return {
        "id": str(pipeline_model.id),
        "name": pipeline_model.name,
        "status": pipeline_model.status,
        "created_at": pipeline_model.created_at.isoformat(),
        "config": pipeline_model.config,
    }

@pytest_asyncio.fixture
async def two_ready_pipelines(client: AsyncClient) -> tuple[dict, dict]:
    """Two ready pipelines for compare tests"""
    r1 = await client.post("/api/v1/pipelines", json={"name": "pipeline-a"})
    r2 = await client.post("/api/v1/pipelines", json={"name": "pipeline-b"})
    assert r1.status_code == 201
    assert r2.status_code == 201
    
    p1, p2 = r1.json(), r2.json()
    
    await client.patch(f"/api/v1/pipelines/{p1['id']}", json={"status": "ready"})
    await client.patch(f"/api/v1/pipelines/{p2['id']}", json={"status": "ready"})

    return {**p1, "status": "ready"}, {**p2, "status": "ready"}


@pytest.fixture(autouse=True)
def mock_minio_client(mocker):
    minio_client = MagicMock()
    minio_client.put_object = AsyncMock()
    minio_client.put_object.return_value = True

    mocker.patch("src.api.routers.documents.get_minio_client",return_value=minio_client)

    return minio_client

@pytest.fixture(autouse=True)
def mock_celery_task(mocker):
    task_result = MagicMock()
    task_result.id = "mock-celery-job-id-12345"
    mock_ingest_delay = mocker.patch(
        "src.api.routers.documents.ingest_task.delay",
        return_value=task_result
    )
    mock_eval_delay = mocker.patch(
        "src.api.routers.compare.run_deep_eval.delay",
        return_value=task_result
    )
    return {
        "documents":mock_ingest_delay,
        "eval":mock_eval_delay
    } 

@pytest.fixture(autouse=True)
def mock_get_llm(mocker,mock_llm):
    mocker.patch("src.rag.steps.query_translation.get_llm",return_value=mock_llm)
    mocker.patch("src.rag.steps.generation.get_llm",return_value=mock_llm)

@pytest.fixture(autouse=True)
def mock_get_embedding(mocker):
    embeddings = MagicMock()
    embeddings.embed_query.return_value = [0.1] * 768
    mocker.patch("src.rag.core.get_embeddings",return_value=embeddings)
    mocker.patch("src.rag.steps.retrieval.get_embeddings",return_value=embeddings)

@pytest.fixture(autouse=True)
def mock_get_client(mocker):
    client = MagicMock()
    client.collection_exists.return_value = True
    mocker.patch("src.rag.ingest.get_client",return_value=client)

@pytest.fixture(autouse=True)
def mock_get_vectorstore(mocker,fake_docs):
    vectorstore = MagicMock()
    vectorstore.similarity_search_with_score.return_value = [(doc,doc.metadata["score"]) for doc in fake_docs]
    vectorstore.max_marginal_relevance_search_with_score_by_vector.return_value = [(doc,doc.metadata["score"]) for doc in fake_docs]
    vectorstore.add_documents.return_value = MagicMock(return_value=None)

    mocker.patch("src.rag.ingest.get_vectorstore",return_value=vectorstore)
    mocker.patch("src.rag.steps.retrieval.get_vectorstore",return_value=vectorstore)

@pytest.fixture(autouse=True)
def mock_get_parent_doc_retriever(mocker,fake_docs):
    retriever = MagicMock()
    retriever.add_documents.return_value = MagicMock(return_value=None)
    retriever.ainvoke = AsyncMock()
    retriever.ainvoke.return_value = fake_docs
    mocker.patch("src.rag.ingest.get_parent_doc_retriever", return_value=retriever)
    mocker.patch("src.rag.steps.retrieval.get_parent_doc_retriever", return_value=retriever)


@pytest.fixture(autouse=True)
def mock_get_splitter(mocker):
    splitter = MagicMock()
    splitter.split_documents.return_value = []
    mocker.patch("src.rag.ingest.get_splitter", return_value=splitter)
    mocker.patch("src.rag.core.get_splitter", return_value=splitter)

@pytest.fixture(autouse=True)
def mock_get_prompt(mocker):
    prompt = ChatPromptTemplate.from_template("Context: {context}\nQuestion: {question}")
    mocker.patch("src.rag.steps.generation.get_prompt", return_value=prompt)


@pytest.fixture(autouse=True)
def mock_cross_encoder(mocker):
    cross_encoder = MagicMock()
    cross_encoder.score.return_value = [0.9,0.8,0.7]
    mocker.patch("src.rag.steps.post_retrieval.get_cross_encoder",return_value=cross_encoder)

