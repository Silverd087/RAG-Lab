from __future__ import annotations
from src.database.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey,DateTime,Index,Text
from sqlalchemy import Enum as SAEnum
import uuid
from sqlalchemy.dialects.postgresql import UUID,JSONB
from datetime import datetime,timezone
import enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.database.models.chunk_trace import PipelineResultModel

class PipelineStatusEnum(str, enum.Enum):
    DRAFT = "draft"
    INGESTING = "ingesting"
    READY = "ready"
    ERROR = "error"

class PipelineModel(Base):
    __tablename__ = "pipeline_config"
    id:Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    name:Mapped[str] = mapped_column(String(255))
    created_at:Mapped[datetime] = mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
    status:Mapped[PipelineStatusEnum] = mapped_column(SAEnum(PipelineStatusEnum),default=PipelineStatusEnum.DRAFT)
    error:Mapped[str|None] = mapped_column(Text,nullable=True)

    config:Mapped[dict] = mapped_column(JSONB,default=dict,nullable=False)
    results: Mapped[list["PipelineResultModel"]] = relationship("PipelineResultModel", back_populates="pipeline")


    __table_args__ = (
        Index("ix_config_gin", "config", postgresql_using="gin"),
    )
