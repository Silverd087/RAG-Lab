import pytest_asyncio
from sqlalchemy import text


@pytest_asyncio.fixture(autouse=True)
async def clean_db(test_engine):
    yield
    async with test_engine.begin() as conn:
        await conn.execute(text("TRUNCATE chunk_traces, pipeline_results, pipeline_config, datasets, dataset_items, benchmarks, comparisons RESTART IDENTITY CASCADE"))
