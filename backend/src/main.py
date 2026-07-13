from fastapi import FastAPI,Request,Response,status
from contextlib import asynccontextmanager
from src.api.routers import pipeline, documents, query, compare,dataset,benchmark
from src.database.session import init_db,get_db
from src.storage.minio_client import init_minio_bucket,get_minio_client
import redis.asyncio as aioredis
from qdrant_client import AsyncQdrantClient
from config import settings
import time
from sqlalchemy import text
from src.celery_app import celery_app
from datetime import datetime

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    init_minio_bucket()

    app.state.redis_client = aioredis.from_url(url=settings.redis_url)
    app.state.qdrant_client = AsyncQdrantClient(url=settings.qdrant_url,timeout=2)

    yield

    app.state.redis_client.close()
    app.state.qdrant_client.close()

app = FastAPI(title="RAG Lab", lifespan=lifespan)

PREFIX = "/api/v1"

app.include_router(pipeline.router, prefix=PREFIX)
app.include_router(documents.router, prefix=PREFIX)
app.include_router(query.router, prefix=PREFIX)
app.include_router(compare.router, prefix=PREFIX)
app.include_router(dataset.router, prefix=PREFIX)
app.include_router(benchmark.router, prefix=PREFIX)

@app.get("/health")
async def health(request:Request,response:Response):
    start_time = time.time()
    
    checks = {
        "postgres":"unhealthy",
        "qdrant":"unhealthy",
        "rabbitmq":"unhealthy",
        "redis":"unhealthy",
        "minio":"unhealthy"
    }

    try:
        async for db in get_db():
            await db.execute(text("SELECT 1"))
            checks["postgres"] = "healthy"
            break
    except:
        checks["postgres"] = "unhealthy"

    try:
        minio_client = get_minio_client()
        minio_client.bucket_exists(settings.minio_bucket_name)
        checks["minio"] = "healthy"
    except:
        checks["minio"] = "unhealthy"
 
    try:
        with celery_app.connection_for_write() as connection:
            connection.connect()
            checks["rabbitmq"] = "healthy"
    except:
            checks["rabbitmq"] = "unhealthy"

    try:
        client = app.state.redis_client
        if await client.ping():
            checks["redis"] = "healthy"
        else:
            checks["redis"] = "unhealthy"
    except:
         checks["redis"] = "unhealthy"
 

    try:
        client = app.state.qdrant_client
        if await client.info():
            checks["qdrant"] = "healthy"
        else:
            checks["qdrant"] = "unhealthy"
    except:
        checks["qdrant"] = "healthy"

    all_healthy = all(status == "healthy" for status in checks.values())

    if not all_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
            "status": "healthy" if all_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "latency_seconds": round(time.time() - start_time, 4),
            "checks": checks
        }



def main():
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
    
if __name__ == "__main__":
    main()