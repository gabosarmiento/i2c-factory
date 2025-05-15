from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr, ValidationError
from typing import List, Optional
from datetime import datetime

# Database session dependency
from .database import get_db
from sqlalchemy.orm import Session

# Router setup
router = APIRouter(prefix="/users", tags=["users"])

# Models
class UserBase(BaseModel):
    name: str
    email: EmailStr
    
class UserCreate(UserBase):
    password: str
    
class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        orm_mode = True

# User repository functions
def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user: UserCreate):
    # In a real app, hash the password first
    db_user = User(
        name=user.name,
        email=user.email,
        hashed_password=user.password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(User).offset(skip).limit(limit).all()

def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

def update_user(db: Session, user_id: int, user: UserBase):
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    
    for key, value in user.dict().items():
        setattr(db_user, key, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user


# API Endpoints
@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user_endpoint(user: UserCreate, db: Session = Depends(get_db)):
    if not user.name:
        raise HTTPException(status_code=400, detail='Name cannot be empty')
    try:
        EmailStr.validate(user.email)
    except ValidationError:
        raise HTTPException(status_code=400, detail='Invalid email format')
    if not validate_password(user.password):
        raise HTTPException(status_code=400, detail='Password does not meet security requirements')
    db_user = get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    return create_user(db=db, user=user)@router.get("/", response_model=List[User])
def read_users_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = get_users(db, skip=skip, limit=limit)
    return users

@router.get("/{user_id}", response_model=User)
def read_user_endpoint(user_id: int, db: Session = Depends(get_db)):
    db_user = get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

def validate_password(password: str) -> bool:
    """
    Validate password strength.

    A valid password must be at least 8 characters long, contain at least one uppercase letter,
    one digit, and one special character (!@#$%^&*).

    Args:
        password (str): The password to validate.

    Returns:
        bool: True if the password is valid, False otherwise.
    """
    if len(password) < 8:
        return False
    has_uppercase = any(char.isupper() for char in password)
    has_digit = any(char.isdigit() for char in password)
    has_special_char = any(char in '!@#$%^&*' for char in password)
    return has_uppercase and has_digit and has_special_char