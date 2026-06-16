from models.base import Base
from sqlalchemy.orm import Mapped, mapped_column,relationship
from sqlalchemy import Text,Float,ForeignKey
import uuid
from sqlalchemy.dialects.postgresql import UUID
from models.pipeline_result import PipelineResult

class ChunkTrace(Base):
    __tablename__ = "chunk_traces"
    id:Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    content:Mapped[str] = mapped_column(Text,nullable=False)
    source:Mapped[str] = mapped_column(Text,nullable=False)
    raw_score:Mapped[float] = mapped_column(Float,nullable=False)
    rerank_score:Mapped[float] = mapped_column(Float,nullable=True)
    pipeline_result_id:Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipeline_results.id",ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    pipeline_result:Mapped["PipelineResult"] = relationship(
        "PipelineResult",
        back_populates="chunks"
    )