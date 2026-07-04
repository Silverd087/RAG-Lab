from langchain_classic.docstore.document import Document
from src.rag.models import PipelineConfig
from src.rag.core import get_llm,get_prompt
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

def format_docs(docs:list[Document])->str:
    return "\n\n".join(doc.page_content for doc in docs)

async def generate(query:str,docs:list[Document],config:PipelineConfig)->tuple[str,]:
    trace ={}
    llm = get_llm(config)
    prompt = get_prompt(config)
    context= format_docs(docs)
    chain = (
         prompt
        | llm
        | StrOutputParser()
    )
    
    answer = await chain.ainvoke({"question":query,"context":context})

    trace["context_sent_to_llm"] = context
    return answer,trace