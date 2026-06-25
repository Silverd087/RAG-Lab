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

