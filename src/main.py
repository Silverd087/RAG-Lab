from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.api.routers import pipeline, documents, query, compare
from src.database.session import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="RAG Lab", lifespan=lifespan)

PREFIX = "/api/v1"

app.include_router(pipeline.router, prefix=PREFIX)
app.include_router(documents.router, prefix=PREFIX)
app.include_router(query.router, prefix=PREFIX)
app.include_router(compare.router, prefix=PREFIX)


def main():
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    
if __name__ == "__main__":
    main()