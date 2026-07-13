import pytest
from src.rag.ingest import ensure_collection, run_ingest, merge_elements_by_page


class TestEnsureCollection:
    def test_creates_dense_collection_when_missing(self, mock_get_client, base_config):
        mock_get_client.collection_exists.return_value = False
        ensure_collection(base_config)
        mock_get_client.create_collection.assert_called_once()
        args, kwargs = mock_get_client.create_collection.call_args
        assert args[0] == f"collection_{base_config.id}"
        assert "sparse_vectors_config" not in kwargs

    def test_creates_hybrid_collection_with_sparse_config(self, mock_get_client, hyde_hybrid_config):
        mock_get_client.collection_exists.return_value = False
        ensure_collection(hyde_hybrid_config)
        mock_get_client.create_collection.assert_called_once()
        args, kwargs = mock_get_client.create_collection.call_args
        assert args[0] == f"collection_{hyde_hybrid_config.id}"
        assert "langchain-sparse" in kwargs["sparse_vectors_config"]

    def test_skips_creation_when_collection_exists(self, mock_get_client, base_config):
        ensure_collection(base_config)
        mock_get_client.create_collection.assert_not_called()

    def test_checks_existence_with_config_scoped_name(self, mock_get_client, base_config):
        ensure_collection(base_config)
        mock_get_client.collection_exists.assert_called_once_with(f"collection_{base_config.id}")


class TestRunIngest:
    def test_raises_when_no_docs_extracted(self, mock_document_loader, base_config):
        mock_document_loader.load.return_value = []
        with pytest.raises(ValueError):
            run_ingest("empty.pdf", base_config)

    def test_default_flow_splits_then_indexes_chunks(self, mock_document_loader, mock_get_splitter, mock_get_vectorstore, base_config, fake_docs):
        mock_get_splitter.split_documents.return_value = fake_docs
        run_ingest("doc.pdf", base_config)
        merged_docs = merge_elements_by_page(fake_docs, "doc.pdf")
        mock_get_splitter.split_documents.assert_called_once_with(merged_docs)
        mock_get_vectorstore.add_documents.assert_called_once_with(fake_docs)

    def test_default_flow_does_not_use_parent_retriever(self, mock_get_parent_doc_retriever, base_config):
        run_ingest("doc.pdf", base_config)
        mock_get_parent_doc_retriever.add_documents.assert_not_called()

    def test_parent_doc_flow_uses_parent_retriever(self, mock_get_parent_doc_retriever, mock_get_vectorstore, parent_rerank_config, fake_docs):
        run_ingest("doc.pdf", parent_rerank_config)
        merged_docs = merge_elements_by_page(fake_docs, "doc.pdf")
        mock_get_parent_doc_retriever.add_documents.assert_called_once_with(merged_docs)
        mock_get_vectorstore.add_documents.assert_not_called()

    def test_ensures_collection_before_indexing(self, mock_get_client, base_config):
        run_ingest("doc.pdf", base_config)
        mock_get_client.collection_exists.assert_called_once_with(f"collection_{base_config.id}")
