from src.database.models.base import Base
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column,relationship
import uuid
from datetime import datetime,timezone
from sqlalchemy import UUID,String,DateTime,ForeignKey

class ComparisonModel(Base):
    __tablename__ = "comparisons"
    
    id:Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query:Mapped[str] = mapped_column(String, nullable=False)
    status:Mapped[str] = mapped_column(String, default="pending") 
    
    result_1_id:Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pipeline_results.id", ondelete="CASCADE"), nullable=False)
    result_2_id:Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pipeline_results.id", ondelete="CASCADE"), nullable=False)
    
    evaluation_scores:Mapped[dict] = mapped_column(JSONB, nullable=True)
    created_at:Mapped[datetime] = mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

    result_1 = relationship("PipelineResultModel", foreign_keys=[result_1_id])
    result_2 = relationship("PipelineResultModel", foreign_keys=[result_2_id])