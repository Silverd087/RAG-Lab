from src.database.models.base import Base
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import UUID,String,DateTime,ForeignKey,Text
from sqlalchemy.orm import Mapped, mapped_column,relationship
import uuid
from datetime import datetime,timezone


class DatasetModel(Base):
    __tablename__ = "datasets"

    id:Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name:Mapped[str] = mapped_column(String(255), nullable=False)
    description:Mapped[str] = mapped_column(String, nullable=True)
    created_at:Mapped[datetime] = mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

    items = relationship("DatasetItemModel", back_populates="dataset", cascade="all, delete-orphan")
    benchmarks = relationship("BenchmarkModel", back_populates="dataset")

class DatasetItemModel(Base):
    __tablename__ = "dataset_items"

    id:Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = mapped_column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    
    question = mapped_column(Text, nullable=False)
    ground_truth = mapped_column(Text, nullable=True)

    dataset = relationship("DatasetModel", back_populates="items")

class BenchmarkModel(Base):
    __tablename__ = "benchmarks"
    
    id:Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id:Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False)
    status:Mapped[str] = mapped_column(String, default="pending")
    created_at:Mapped[datetime] = mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

    results:Mapped[list|None] = mapped_column(JSONB, nullable=True)
    error_log:Mapped[str|None] = mapped_column(Text, nullable=True)
    dataset = relationship("DatasetModel", back_populates="benchmarks")