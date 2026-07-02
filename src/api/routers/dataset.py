from fastapi import APIRouter,Depends, HTTPException,status
from src.api.schema import DatasetCreateQuery,DatasetResponse,DatasetListResponse,DatasetItemCreateQuery
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.session import get_db
from src.database.models.benchmark import DatasetItemModel,DatasetModel
from sqlalchemy.orm import joinedload
from sqlalchemy import select
import uuid

router = APIRouter()

@router.post("/datasets",tags=["dataset"],status_code=status.HTTP_201_CREATED,response_model=DatasetResponse)
async def create_dataset(payload:DatasetCreateQuery,db:AsyncSession=Depends(get_db)):
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="dataset must not be empty")
    
    dataset = DatasetModel(
        name=payload.name,
        description=payload.description,
        items= [
            DatasetItemModel(
                question= item.question,
                ground_truth= item.ground_truth
            )
            for item in payload.items
        ]
    )
    db.add(dataset)
    await db.flush()

    stmt = (
        select(DatasetModel)
        .options(joinedload(DatasetModel.items))
        .where(DatasetModel.id == dataset.id)
    )
    result = await db.execute(stmt)
    dataset_row = result.unique().scalar_one_or_none()
    return dataset_row

@router.get("/datasets",tags=["datasets"],response_model=list[DatasetListResponse])
async def get_all_datasets(db:AsyncSession=Depends(get_db)):
    stmt = select(DatasetModel).order_by(DatasetModel.created_at.desc())
    result = await db.execute(stmt)
    dataset_rows = result.scalars().all()
    return dataset_rows

@router.get("/datasets/{dataset_id}",tags=["dataset"],response_model=DatasetResponse)
async def get_dataset_by_id(dataset_id:uuid.UUID,db:AsyncSession=Depends(get_db)):
    stmt = (
        select(DatasetModel)
        .options(joinedload(DatasetModel.items)) 
        .where(DatasetModel.id == dataset_id)
    )
    result = await db.execute(stmt)
    dataset_row = result.unique().scalar_one_or_none()

    if not dataset_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"dataset with {dataset_id} not found")
    
    return dataset_row

@router.delete("/datasets/{dataset_id}",tags=["dataset"],status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset_by_id(dataset_id:uuid.UUID,db:AsyncSession=Depends(get_db)):
    if not dataset_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="dataset id cannot be empty")
    
    stmt = select(DatasetModel).where(DatasetModel.id == dataset_id)
    result = await db.execute(stmt)

    dataset_row = result.scalar_one_or_none()

    if not dataset_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"dataset with id {dataset_id} not found")
    
    await db.delete(dataset_row)

@router.post("/datasets/{dataset_id}/items",tags=["dataset"],status_code=status.HTTP_200_OK,response_model=DatasetResponse)
async def add_items_to_existing_dataset(dataset_id:uuid.UUID,payload:DatasetItemCreateQuery,db:AsyncSession=Depends(get_db)):
    if not dataset_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="dataset id cannot be empty")
    
    if not payload or not len(payload.items)>0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,detail="")

    stmt = select(DatasetModel).where(DatasetModel.id == dataset_id)
    result = await db.execute(stmt)

    dataset_row = result.scalar_one_or_none()

    if not dataset_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"dataset with id {dataset_id} not found")
    
    new_items = [DatasetItemModel(
        dataset_id=dataset_id,
        question=item.question,
        ground_truth=item.ground_truth
    ) for item in payload.items]

    db.add_all(new_items)
    await db.flush()

    db.expire(dataset_row, ["items"])
    
    stmt_reload = (select(DatasetModel)
                   .options(joinedload(DatasetModel.items))
                   .where(DatasetModel.id == dataset_id)
                )
    
    result_reload = await db.execute(stmt_reload)

    dataset_row = result_reload.unique().scalar_one_or_none()
    return dataset_row


@router.delete("/datasets/{dataset_id}/items/{item_id}",tags=["dataset"],status_code=status.HTTP_204_NO_CONTENT)
async def delete_item_in_existing_dataset(dataset_id:uuid.UUID,item_id:uuid.UUID,db:AsyncSession=Depends(get_db)):

    if not dataset_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="dataset id cannot be empty")
    
    stmt = select(DatasetModel).where(DatasetModel.id == dataset_id)
    result = await db.execute(stmt)

    dataset_row = result.scalar_one_or_none()

    if not dataset_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"dataset with id {dataset_id} not found")
    
    stmt = select(DatasetItemModel).where(DatasetItemModel.id == item_id)
    result = await db.execute(stmt)
    item_row = result.scalar_one_or_none()

    if not item_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"item with id {item_id} not found")
    
    await db.delete(item_row)