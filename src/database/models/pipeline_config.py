from models.base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey,DateTime,Index
from sqlalchemy import Enum as SAEnum
import uuid
from sqlalchemy.dialects.postgresql import UUID,JSONB
from datetime import datetime,timezone
import enum

class PipelineStatusEnum(str, enum.Enum):
    DRAFT = "draft"
    INGESTING = "ingesting"
    READY = "ready"
    ERROR = "error"

class PipelineConfig(Base):
    __tablename__ = "pipeline_config"
    id:Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    name:Mapped[str] = mapped_column(String(50))
    created_at:Mapped[datetime] = mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
    status_id:Mapped[str] = mapped_column(String(50),ForeignKey("pipeline_status.id"),default="draft")
    status:Mapped[PipelineStatusEnum] = mapped_column(SAEnum(PipelineStatusEnum),default=PipelineStatusEnum.DRAFT)

    pipeline_config:Mapped[dict] = mapped_column(JSONB,default=dict,nullable=False)

    __table_args__ = (
        Index("ix_pipeline_config_gin", "pipeline_config", postgresql_using="gin"),
    )
