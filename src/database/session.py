from sqlalchemy import create_engine
from config import settings
from sqlalchemy.orm import Session,sessionmaker


url = f"postgresql+psycopg2://{settings.postgres_user}:{settings.postgres_password}@localhost/RagLab"
engine = create_engine(url, echo=True)
sessionlocal = sessionmaker(bind=engine)

def get_db():
    try:
        db = sessionlocal()
        yield db
    finally:
        db.close()
    
