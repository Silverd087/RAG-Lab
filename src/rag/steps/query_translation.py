
from src.rag.models import PipelineConfig
from langchain_core.prompts import ChatPromptTemplate
from src.rag.core import get_llm
from langchain_core.output_parsers import StrOutputParser
import re

MULTI_QUERY_PROMPT = ChatPromptTemplate.from_template(
    "You are an AI language model assistant. Generate {n} different versions "
    "of the following question to retrieve relevant documents from a vector database. "
    "Return each version on a new line with no numbering or extra formatting.\n\n"
    "Original question: {question}"
)

STEP_BACK_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are an expert at rephrasing questions into broader, "
               "more generic questions that are easier to answer. "
               "Given a specific question, step back and ask a more general version."),
    ("user", "{question}")
])

HYDE_PROMPT = ChatPromptTemplate.from_template(
    "Write a short hypothetical document that would directly answer this question. "
    "Be concise and factual in style.\n\nQuestion: {question}"
)



async def translate_query(query:str,config:PipelineConfig)-> tuple[str | list,dict]:
    """
    Returns (search_query, trace)
    search_query: the query to actually use for retrieval
    trace: what happened during translation
    """
    trace = {"original_query": query}

    if config.query_translation.hyde:
        search_query = await _hyde(query,config)
        trace["hypothetical_doc"] = search_query
        return clean_hyde_text(search_query),trace
    
    if config.query_translation.multi_query:
        variants = await _generate_variants(query,config)
        trace["query_variants"] = variants
        return [query]+variants, trace
    
    if config.query_translation.step_back:
        search_query = await _step_back(query,config)
        trace["step_back_query"] = search_query
        return search_query,trace

    return query,trace

async def _hyde(query:str,config:PipelineConfig)->str:
    llm = get_llm(config)
    chain = (
        HYDE_PROMPT
        | llm
        | StrOutputParser()
    )
    return await chain.ainvoke({"question":query})


async def _generate_variants(query:str,config:PipelineConfig,n:int = 4)->str:
    llm = get_llm(config)
    chain = (
        MULTI_QUERY_PROMPT
        | llm
        | StrOutputParser()
        | (lambda x:x.strip().split("\n"))
    )
    return await chain.ainvoke({"question":query,"n":n})


async def _step_back(query:str,config:PipelineConfig)->str:
    llm = get_llm(config)
    chain = (
        STEP_BACK_PROMPT
        | llm
        | StrOutputParser()
    )
    return await chain.ainvoke({"question":query})


def clean_hyde_text(text: str) -> str:
    """Removes harsh markdown syntax and flattens newlines to prevent Gemini 500 errors."""
    # 1. Remove Markdown header and bold symbols
    text = re.sub(r'[#\*`_-]', '', text)
    # 2. Normalize multiple spaces and collapse newlines into simple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()