# test_function_modification.py
from pathlib import Path
import sys
import traceback

# ── bootstrap built‑ins (must come BEFORE any i2c import) ────────────
from i2c.bootstrap import initialize_environment
initialize_environment()

# ── i2c imports (after env) ───────────────────────────────────────────
print("Importing FunctionModifierAgent...")
from i2c.agents.modification_team.function_modifier import FunctionModifierAgent
print("Importing validator...")
from i2c.agents.modification_team.validator import run_validator  # ensure this exists

# ── repo root & retry limit ───────────────────────────────────────────
REPO = Path.cwd()               # assume you run from idea_to_code_factory/
MAX_RETRIES = 2                 # 1 initial + 2 follow‑ups

# ── instantiate agent ────────────────────────────────────────────────
print("Creating FunctionModifierAgent...")
agent = FunctionModifierAgent()

# ── test file to modify ───────────────────────────────────────────────
# Let's create a simple test file if it doesn't exist
TEST_FILE = "i2c_test/test_app/routers/users.py"
TEST_DIR = REPO / "i2c_test/test_app/"

if not (REPO / TEST_FILE).exists():
    print(f"Test file {TEST_FILE} doesn't exist, creating it...")
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    
    TEST_CODE = """from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import EmailStr

from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..database import get_db

router = APIRouter()

@router.post("/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)

@router.get("/", response_model=list[schemas.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_users(db, skip=skip, limit=limit)

@router.get("/{user_id}", response_model=schemas.User)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, user_id=user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.patch("/{user_id}", response_model=schemas.User, status_code=status.HTTP_200_OK)
def patch_user(user_id: int, user: schemas.UserUpdate, db: Session = Depends(get_db)):
    updated = crud.update_user(db, user_id, user)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return updated

@router.delete("/{user_id}", response_model=schemas.User, status_code=status.HTTP_200_OK)
def remove_user(user_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_user(db, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    return deleted"""
    (REPO / TEST_FILE).write_text(TEST_CODE)
    print(f"Created test file: {TEST_FILE}")

# ── initial modification step ────────────────────────────────────────
step = {
    "file": TEST_FILE,
    "function": "create_user",  # Specifically targeting this function
    "what": (
        "Add two validation checks at the very top of create_user: "
        "(1) if user.name is empty, raise HTTPException(400, 'Name cannot be empty'); "
        "(2) validate user.email with EmailStr.validate"
    ),
    "how": (
        "Immediately after the function signature, insert exactly:\n"
        "    if not user.name:\n"
        "        raise HTTPException(400, 'Name cannot be empty')\n"
        "    EmailStr.validate(user.email)\n"
        "Do not alter anything else in the function."
    )
}

# ── modification / validate loop ────────────────────────────────────────
try:
    print("\n=== Starting function modification loop ===")
    for attempt in range(MAX_RETRIES + 1):
        print(f"\nAttempt {attempt+1}/{MAX_RETRIES+1}:")
        try:
            # Execute the function modification
            modified_func = agent.modify_function(step, REPO)
            print(f"Modified function:\n{modified_func}")
            
            # Run validator
            print("Running validator...")
            ok, diag = run_validator(REPO)
            if ok:
                print("✅ Validator passed — done")
                break

            print("❌ Validator failed; requesting follow‑up modification…\n")
            print(f"Validator output:\n{diag}")
            
            # Create follow-up step targeting the same function
            step = {
                "file": TEST_FILE,
                "function": "create_user",
                "what": "Fix validator/linter/test errors",
                "how": (
                    "Apply ONLY the minimal changes needed so that the function passes "
                    "all validators and unit tests below without altering correct logic.\n\n"
                    "Validator output:\n" + diag
                )
            }
            
        except ValueError as e:
            print(f"\n⚠️ Function modification error: {e}")
            if attempt == MAX_RETRIES:
                raise
        except KeyboardInterrupt:
            print("\n⚠️ User interrupted")
            sys.exit(1)
        except Exception as e:
            print(f"\n⚠️ Exception during attempt {attempt+1}: {e}")
            traceback.print_exc()
            if attempt == MAX_RETRIES:
                raise
                
    print("\n=== Function modification process completed ===")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    traceback.print_exc()
    sys.exit(1)