from sqlalchemy.ext.asyncio import create_async_engine,AsyncSession,async_sessionmaker
from config import settings


url = f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}/{settings.postgres_db}"
engine = create_async_engine(url, echo=True)
async_session = async_sessionmaker(bind=engine,expire_on_commit=False)

async def get_db():
    async with async_session() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise

    
