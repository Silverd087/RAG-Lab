from models.base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey,DateTime,Index
import uuid
from sqlalchemy.dialects.postgresql import UUID,JSONB
from datetime import datetime,timezone

class PipelineStatus(Base):
    """
        id = draft 
        id = ingesting 
        id = ready
        id = error
    """
    __tablename__ = "pipeline_status"
    id:Mapped[str] = mapped_column(String(50),primary_key=True)

class PipelineConfig(Base):
    __tablename__ = "pipeline_config"
    id:Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    name:Mapped[str] = mapped_column(String(50))
    created_at:Mapped[datetime] = mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
    status_id:Mapped[str] = mapped_column(String(50),ForeignKey("pipeline_status.id"),default="draft")
    status:Mapped["PipelineStatus"] = relationship("PipelineStatus")

    pipeline_config:Mapped[dict] = mapped_column(JSONB,default=dict,nullable=False)

    __table_args__ = (
        # A GIN (Generalized Inverted Index) allows PostgreSQL to index inside your JSON payload.
        # This makes running raw SQL queries directly against your nested JSON keys incredibly fast.
        Index("ix_pipeline_config_payload_gin", "config_payload", postgresql_using="gin"),
    )
