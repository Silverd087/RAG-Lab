from contextlib import contextmanager
from sqlalchemy import create_engine
from config import settings
from sqlalchemy.orm import sessionmaker

url = f"postgresql+psycopg2://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}/{settings.postgres_db}"
engine = create_engine(url, echo=True)
SyncSession = sessionmaker(bind=engine,expire_on_commit=False)

@contextmanager
def get_sync_db():
    session = SyncSession()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

