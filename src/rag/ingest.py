from langchain_community.document_loaders import PyPDFLoader
from qdrant_client.http.models import Distance, VectorParams,SparseVectorParams
from rag.core import get_client
from rag.models import PipelineConfig,ModeConfig
from rag.core import get_vectorstore, get_splitter,get_parent_doc_retriever

def ensure_collection(config:PipelineConfig):
    client = get_client()
    if not client.collection_exists(f"collection_{config.id}"):
        if config.retrieval.mode == ModeConfig.HYBRID:
            client.create_collection(f"collection_{config.id}",vectors_config=VectorParams(size=3072,distance=Distance.COSINE),sparse_vectors_config={"langchain-sparse":SparseVectorParams()})

        else:
            client.create_collection(f"collection_{config.id}",vectors_config=VectorParams(size=3072,distance=Distance.COSINE))




def ingest(file : str, config : PipelineConfig) -> None:
    print(f"retrieval mode: {config.retrieval.mode}")
    print(f"collection: collection_{config.id}")
    
    if not file.endswith(".pdf"):
        raise ValueError(f"Expected a pdf file, got {file}")
    ensure_collection(config)
    loader = PyPDFLoader(file)
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




