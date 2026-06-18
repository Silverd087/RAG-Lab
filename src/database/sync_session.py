from sqlalchemy import create_engine,sessionmaker
from config import settings
from database.models.base import Base

url = f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}/{settings.postgres_db}"
engine = create_engine(url, echo=True)
SyncSession = sessionmaker(bind=engine,expire_on_commit=False)

async def get_sync_db():
    session = SyncSession()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise

    
