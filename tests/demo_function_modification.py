# demo_function_modification.py
from pathlib import Path
import sys
import traceback
import time

# ── bootstrap built‑ins (must come BEFORE any i2c import) ────────────
from i2c.bootstrap import initialize_environment
initialize_environment()

# ── i2c imports (after env) ───────────────────────────────────────────
print("Importing SafeFunctionModifierAgent...")
from i2c.agents.modification_team.safe_function_modifier import SafeFunctionModifierAgent
print("Importing validator...")
from i2c.agents.modification_team.validator import run_validator

# ── repo root & retry limit ───────────────────────────────────────────
REPO = Path.cwd()  # assume you run from idea_to_code_factory/

# ── instantiate agent ────────────────────────────────────────────────
print("Creating SafeFunctionModifierAgent...")
agent = SafeFunctionModifierAgent()

# ── test file to modify ───────────────────────────────────────────────
TEST_FILE = "i2c_test/test_app/users.py"
TEST_DIR = REPO / "i2c_test/test_app"

if not (REPO / TEST_FILE).exists():
    print(f"Test file {TEST_FILE} doesn't exist, creating it...")
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    
    TEST_CODE = """from fastapi import APIRouter, HTTPException, Depends, status
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

def delete_user(db: Session, user_id: int):
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    
    db.delete(db_user)
    db.commit()
    return db_user

# API Endpoints
@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user_endpoint(user: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    return create_user(db=db, user=user)

@router.get("/", response_model=List[User])
def read_users_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = get_users(db, skip=skip, limit=limit)
    return users

@router.get("/{user_id}", response_model=User)
def read_user_endpoint(user_id: int, db: Session = Depends(get_db)):
    db_user = get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user"""
    
    (REPO / TEST_FILE).write_text(TEST_CODE)
    print(f"Created test file: {TEST_FILE}")

print("\n=== Function Modification Demo ===")

# First, list available functions in the file
try:
    functions = agent.list_functions(REPO / TEST_FILE)
    print(f"\nFunctions in {TEST_FILE}:")
    for idx, func_name in enumerate(functions, 1):
        print(f"{idx}. {func_name}")
except Exception as e:
    print(f"Error listing functions: {e}")

print("\n=== Demonstration 1: Modify Function ===")
# Modify create_user_endpoint function
modify_step = {
    "file": TEST_FILE,
    "function": "create_user_endpoint",
    "what": "Add validation for empty name and email format",
    "how": "Add these checks at the beginning of the function:\n"
           "1. Check if user.name is empty, and if so, raise HTTPException(400, 'Name cannot be empty')\n"
           "2. Try to validate user.email with EmailStr.validate and catch any ValidationError to raise HTTPException(400, 'Invalid email format')"
}

try:
    print("\nModifying create_user_endpoint...")
    modified_func = agent.modify_function(modify_step, REPO)
    print(f"\nSuccessfully modified create_user_endpoint function.")
except Exception as e:
    print(f"Error modifying function: {e}")
    traceback.print_exc()

time.sleep(1)  # Pause to see the output

print("\n=== Demonstration 2: Add Function ===")
# Add a new function to validate password strength
add_step = {
    "file": TEST_FILE,
    "function": "validate_password",
    "action": "add",
    "position": "end",
    "what": "Create a function to check password strength",
    "how": "Create a function that takes a password string and returns True if it's valid, False otherwise.\n"
           "A valid password must:\n"
           "1. Be at least 8 characters long\n"
           "2. Contain at least one uppercase letter\n"
           "3. Contain at least one digit\n"
           "4. Contain at least one special character (!@#$%^&*)"
}

try:
    print("\nAdding validate_password function...")
    new_func = agent.modify_function(add_step, REPO)
    print(f"\nSuccessfully added validate_password function:\n{new_func}")
except Exception as e:
    print(f"Error adding function: {e}")
    traceback.print_exc()

time.sleep(1)  # Pause to see the output

print("\n=== Demonstration 3: Update Function to Use New Validation ===")
# Modify create_user_endpoint to use the new validation function
update_step = {
    "file": TEST_FILE,
    "function": "create_user_endpoint",
    "what": "Add password validation",
    "how": "Use the validate_password function to check the user's password.\n"
           "If the password is invalid, raise HTTPException(400, 'Password does not meet security requirements')"
}

try:
    print("\nUpdating create_user_endpoint with password validation...")
    updated_func = agent.modify_function(update_step, REPO)
    print(f"\nSuccessfully updated create_user_endpoint to use password validation.")
except Exception as e:
    print(f"Error updating function: {e}")
    traceback.print_exc()

time.sleep(1)  # Pause to see the output

print("\n=== Demonstration 4: Delete Function ===")
# Delete an unused function
delete_step = {
    "file": TEST_FILE,
    "function": "delete_user",  # Let's pretend this is unused
    "action": "delete"
}

try:
    print("\nDeleting delete_user function...")
    result = agent.modify_function(delete_step, REPO)
    print(f"\nFunction deletion result: {result}")
except Exception as e:
    print(f"Error deleting function: {e}")
    traceback.print_exc()

# Final list of functions to verify everything worked
try:
    functions = agent.list_functions(REPO / TEST_FILE)
    print(f"\nUpdated functions in {TEST_FILE}:")
    for idx, func_name in enumerate(functions, 1):
        print(f"{idx}. {func_name}")
except Exception as e:
    print(f"Error listing functions: {e}")

print("\n=== Function Modification Demo Complete ===")