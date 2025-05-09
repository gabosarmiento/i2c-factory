from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import crud, schemas
from database import get_db

router = APIRouter(prefix="/items", tags=["items"])

@router.post("/", response_model=schemas.Item)
def create_item(item: schemas.ItemCreate, user_id: int, db: Session = Depends(get_db)):
    # ensure user exists
    if not crud.get_user(db, user_id=user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return crud.create_item(db=db, item=item, user_id=user_id)

@router.get("/", response_model=list[schemas.Item])
def read_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_items(db, skip=skip, limit=limit)

@router.get("/{item_id}", response_model=schemas.Item)
def read_item(item_id: int, db: Session = Depends(get_db)):
    db_item = crud.get_item(db, item_id=item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    return db_item

@router.patch("/{item_id}", response_model=schemas.Item)
def patch_item(item_id: int, item: schemas.ItemUpdate, db: Session = Depends(get_db)):
    updated = crud.update_item(db, item_id, item)
    if not updated:
        raise HTTPException(status_code=404, detail="Item not found")
    return updated

@router.delete("/{item_id}", response_model=schemas.Item)
def remove_item(item_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_item(db, item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return deleted
