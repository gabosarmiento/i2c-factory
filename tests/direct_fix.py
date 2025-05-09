# direct_fix.py
import sys
from pathlib import Path

# Get the file path
file_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("i2c_test/test_app/users.py")

if not file_path.exists():
    print(f"File not found: {file_path}")
    sys.exit(1)

print(f"Attempting to directly fix syntax in: {file_path}")

# Create a backup
backup_path = file_path.with_suffix(file_path.suffix + ".bak")
file_path.rename(backup_path)
print(f"Original file backed up to: {backup_path}")

# Read the backup file
content = backup_path.read_text(encoding="utf-8")

# Find the specific error and fix it
fixed_content = content.replace(
    "return create_user(db=db, user=user)def read_users_endpoint", 
    "return create_user(db=db, user=user)\n\n@router.get(\"/\", response_model=List[User])\ndef read_users_endpoint"
)

# Write the fixed file
file_path.write_text(fixed_content, encoding="utf-8")
print(f"Fixed file written to: {file_path}")

# Test if the file can now be parsed
try:
    import ast
    ast.parse(fixed_content)
    print("✅ Syntax fix successful!")
except SyntaxError as e:
    print(f"⚠️ File still has syntax errors: {e}")
    print("You might need to manually edit the file or restore from backup.")