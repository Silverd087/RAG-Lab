from langchain_unstructured import UnstructuredLoader
from qdrant_client.http.models import Distance, VectorParams,SparseVectorParams
from src.rag.core import get_client, get_embeddings
from src.rag.models import PipelineConfig,ModeConfig
from src.rag.core import get_vectorstore, get_splitter,get_parent_doc_retriever


def get_pipeline_embedding_dimensions(config:PipelineConfig) -> int:
    """
    Dynamically extracts embedding sizes from any provider model spec at runtime
    by embedding a probe string and measuring the vector length.
    """
    embeddings = get_embeddings(config)
    return len(embeddings.embed_query("dimension probe"))


def ensure_collection(config:PipelineConfig):
    client = get_client()
    if not client.collection_exists(f"collection_{config.id}"):
        dimensions = get_pipeline_embedding_dimensions(config)
        if config.retrieval.mode == ModeConfig.HYBRID:
            client.create_collection(f"collection_{config.id}",vectors_config=VectorParams(size=dimensions,distance=Distance.COSINE),sparse_vectors_config={"langchain-sparse":SparseVectorParams()})
        else:
            client.create_collection(f"collection_{config.id}",vectors_config=VectorParams(size=dimensions,distance=Distance.COSINE))




def run_ingest(file : str, config : PipelineConfig) -> None:    
    ensure_collection(config)
    loader = UnstructuredLoader(file)
    docs = loader.load()

    if not docs:
        raise ValueError(f"No content extrcated from {file}")
    
    if config.chunking.parent_doc:
        retriever = get_parent_doc_retriever(config)
        retriever.add_documents(docs)
    else:
        splitter = get_splitter(config)
        chunks = splitter.split_documents(docs)
        vectorstore = get_vectorstore(config)
        vectorstore.add_documents(chunks) 




