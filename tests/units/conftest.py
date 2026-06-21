import pytest
from unittest.mock import MagicMock, AsyncMock

@pytest.fixture(autouse=True)
def mock_get_llm(mocker,mock_llm):
    mocker.patch("rag.steps.query_translation.get_llm",return_value=mock_llm)
    mocker.patch("rag.steps.retrieval.get_llm",return_value=mock_llm)
    mocker.patch("rag.steps.post_retrieval.get_llm",return_value=mock_llm)
    mocker.patch("rag.steps.generation.get_llm",return_value=mock_llm)

@pytest.fixture(autouse=True)
def mock_get_embedding(mocker):
    embeddings = MagicMock()
    embeddings.embed_query.return_value = [0.1] * 768
    mocker.patch("rag.core.get_embeddings",return_value=embeddings)
    mocker.patch("rag.steps.post_retrieval.get_embeddings",return_value=embeddings)

@pytest.fixture(autouse=True)
def mock_get_client(mocker):
    client = MagicMock()
    client.collection_exists.return_value = True
    mocker.patch("rag.ingest.get_client",return_value=client)

@pytest.fixture(autouse=True)
def mock_get_vectorstore(mocker,fake_docs):
    vectorstore = MagicMock()
    vectorstore.similarity_search_with_score.return_value = [(doc,doc.metadata["score"]) for doc in fake_docs]
    vectorstore.max_marginal_relevance_search_with_score_by_vector.retun_value = [(doc,doc.metadata["score"]) for doc in fake_docs]
    vectorstore.add_documents.return_value = MagicMock(return_value=None)

    mocker.patch("rag.ingest.get_vectorstore",return_value=vectorstore)
    mocker.patch("rag.steps.post_retrieval.get_vectorstore",return_value=vectorstore)

@pytest.fixture(autouse=True)
def mock_get_parent_doc_retriever(mocker,fake_docs):
    retriever = MagicMock()
    retriever.add_documents.return_value = MagicMock(return_value=None)
    retriever.ainvoke.return_value = AsyncMock(return_value=fake_docs)
    mocker.patch("rag.ingest.get_parent_doc_retriever", return_value=retriever)
    mocker.patch("rag.steps.retrieval.get_parent_doc_retriever", return_value=retriever)


@pytest.fixture(autouse=True)
def mock_get_splitter(mocker):
    splitter = MagicMock()
    splitter.split_documents.return_value = []
    mocker.patch("rag.ingest.get_splitter", return_value=splitter)
    mocker.patch("rag.core.get_splitter", return_value=splitter)

@pytest.fixture(autouse=True)
def mock_get_prompt(mocker):
    prompt = MagicMock()
    mocker.patch("rag.steps.generation.get_prompt", return_value=prompt)



