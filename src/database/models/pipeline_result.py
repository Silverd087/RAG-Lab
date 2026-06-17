from models.base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Text,ForeignKey
import uuid
from sqlalchemy.dialects.postgresql import UUID,JSONB
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from src.database.models.chunk_trace import ChunkTrace

class PipelineResult(Base):
    __tablename__ = "pipeline_results"
    id:Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    pipeline_id:Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipeline_config.id",ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    query:Mapped[str] = mapped_column(Text,nullable=False)
    translated_query:Mapped[str | None] = mapped_column(Text,nullable=True)
    query_variants:Mapped[list[str] | None] = mapped_column(JSONB,nullable=True)

    answer:Mapped[str] = mapped_column(Text)
    latency: Mapped[dict[str,int]]  = mapped_column(JSONB,default=dict,nullable=False)

    chunks:Mapped[List["ChunkTrace"]] = relationship(
        "ChunkTrace",
        back_populates="pipeline_result",
        cascade="all,delete-orphan"
    )


