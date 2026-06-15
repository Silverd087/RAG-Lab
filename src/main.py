from src.rag.models import PipelinePresets
from src.rag.pipeline import run_pipeline
from src.rag.ingest import ingest
from src.rag.models import RetrievalConfig
import asyncio
async def main():
    file_path="sample_document.pdf"
    config = PipelinePresets.rag_fusion(name="test")
    print(config)
    ingest(file=file_path,config=config)
    pipeline_result, answer = await run_pipeline(config=config,query="what is attention")
    print(answer)
    print(pipeline_result)
    
if __name__ == "__main__":
    asyncio.run(main())
