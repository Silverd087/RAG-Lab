import pytest_asyncio
from src.rag.models import PipelinePresets
from src.database.models.pipeline import PipelineModel
@pytest_asyncio.fixture
async def pipeline(db_session):
    pipeline_config = PipelinePresets.baseline("test-baseline")
    pipeline_model =  PipelineModel(
        id=pipeline_config.id,
        name=pipeline_config.name,
        config=pipeline_config.model_dump(exclude={"id","status","created_at","name"})
        )
    db_session.add(pipeline_model)
    await db_session.commit()
    return {
        "id": str(pipeline_model.id),
        "name": pipeline_model.name,
        "status": pipeline_model.status.value,
        "created_at": pipeline_model.created_at.isoformat(),
        "config": pipeline_model.config,
    }
