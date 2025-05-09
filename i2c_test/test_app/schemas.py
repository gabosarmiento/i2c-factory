from typing import List, Optional

from pydantic import BaseModel, EmailStr

class ItemBase(BaseModel):
    title: str
    description: Optional[str] = None

class ItemCreate(ItemBase):
    pass

class Item(ItemBase):
    id: int
    owner_id: int

    class Config:
        # Pydantic v2 renamed `orm_mode` → `from_attributes`
        from_attributes = True


class UserBase(BaseModel):
    name: str
    email: EmailStr

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    items: List[Item] = []

    class Config:
        from_attributes = True
        
class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None

class ItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
