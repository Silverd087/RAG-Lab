import asyncio
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker, AsyncSession
from src.database.models.base import Base
import pytest
from src.main import app  
from src.database.session import get_db
from httpx import AsyncClient
from config import settings
from src.rag.models import PipelinePresets
from unittest.mock import MagicMock, AsyncMock
from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from langchain_community.chat_models.fake import FakeMessagesListChatModel

@pytest.fixture(scope="session")
def get_event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(url=f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}/{settings.postgres_test_db}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    engine.dispose()

@pytest.fixture
async def db_session(test_engine):
    async_session = async_sessionmaker(bind=test_engine,class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def client(db_session:AsyncSession):
    async def _override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = _override_get_db
    
    async with AsyncClient(app=app,base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()

@pytest.fixture
def fake_docs()->list[Document]:
    return [
        Document(
            page_content="Attention is a mechanism that relates positions.",
            metadata={"source": "test.pdf", "page": 0, "score": 0.95}
        ),
        Document(
            page_content="Self-attention computes representations of sequences.",
            metadata={"source": "test.pdf", "page": 1, "score": 0.88}
        ),
        Document(
            page_content="Multi-head attention runs attention in parallel.",
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

