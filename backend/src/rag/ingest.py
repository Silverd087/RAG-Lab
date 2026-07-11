from langchain_unstructured import UnstructuredLoader
from langchain_core.documents import Document
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




def merge_elements_by_page(docs:list[Document],source:str)->list[Document]:
    """
    UnstructuredLoader returns one document per element (title, paragraph, ...),
    so chunk_size is never reached. Merge elements back into one document per page
    before splitting.
    """
    pages:dict = {}
    for doc in docs:
        pages.setdefault(doc.metadata.get("page_number"),[]).append(doc.page_content)
    return [
        Document(page_content="\n\n".join(contents),metadata={"source":source,"page":page})
        for page,contents in pages.items()
    ]


def run_ingest(file : str, config : PipelineConfig, source_name : str | None = None) -> None:
    ensure_collection(config)
    loader = UnstructuredLoader(file)
    docs = loader.load()

    if not docs:
        raise ValueError(f"No content extrcated from {file}")

    docs = merge_elements_by_page(docs,source_name or file)

    if config.chunking.parent_doc:
        retriever = get_parent_doc_retriever(config)
        retriever.add_documents(docs)
    else:
        splitter = get_splitter(config)
        chunks = splitter.split_documents(docs)
        vectorstore = get_vectorstore(config)
        vectorstore.add_documents(chunks) 




