import time
import requests
import os
import sys
import uuid
import zipfile

# Base URL of your running FastAPI app
BASE_URL = 'http://127.0.0.1:8000/api/v1'

# Determine the directory that contains your FastAPI app (identified by main.py)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# —— Add any extra directories you want to skip here —— 
EXCLUDE_DIRS = {
    'venv',       # virtualenv folder
    '.venv',      # alternate virtualenv
    'env', 'ENV', # other env folders
    '__pycache__',
    'node_modules',
    '.idea',      # PyCharm/IDE settings
    '.vscode',    # VSCode settings
    # add more names here, e.g. 'migrations', '*.db', etc.
}

def find_app_dir():
    """
    Return the directory that contains the FastAPI app (identified by main.py).
    Priority:
      1) Script’s own folder, if it has main.py
      2) A subfolder named 'test_app' containing main.py
      3) Otherwise fallback to the script’s folder
    """
    # 1) Check script’s folder
    if os.path.isfile(os.path.join(SCRIPT_DIR, 'main.py')):
        return SCRIPT_DIR

    # 2) Check nested 'test_app'
    candidate = os.path.join(SCRIPT_DIR, 'test_app')
    if os.path.isfile(os.path.join(candidate, 'main.py')):
        return candidate

    # 3) Fallback
    return SCRIPT_DIR

# Application directory and exclusions
APP_DIR = find_app_dir()
if not os.path.isdir(APP_DIR):
    print(f"WARNING: App directory '{APP_DIR}' not found. Using script directory.")
    APP_DIR = SCRIPT_DIR

# Directories to exclude from line counts and zipping
EXCLUDE_DIRS = {'venv', '.venv', 'env', 'ENV', '__pycache__', 'node_modules'}


def count_lines(path):
    """
    Count total lines in all .py files under the given directory,
    excluding typical dependency folders.
    """
    total = 0
    for root, dirs, files in os.walk(path):
        # prune excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for fname in files:
            if fname.endswith('.py'):
                try:
                    with open(os.path.join(root, fname), 'r', encoding='utf-8') as f:
                        total += len(f.readlines())
                except Exception as e:
                    print(f"Unable to read {fname}: {e}")
    return total


def zip_app(output='app.zip'):
    """
    Zip only the application .py files, excluding dependency folders.
    """
    zipf = zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED)
    for root, dirs, files in os.walk(APP_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for fname in files:
            if fname.endswith('.py'):
                full = os.path.join(root, fname)
                arc = os.path.relpath(full, SCRIPT_DIR)
                zipf.write(full, arc)
    zipf.close()
    print(f"Zipped application files to {output}")


def cleanup():
    """
    Remove all existing items and users before benchmarking.
    """
    # delete items
    resp = requests.get(f"{BASE_URL}/items/")
    if resp.status_code == 200:
        for item in resp.json():
            requests.delete(f"{BASE_URL}/items/{item.get('id')}")
    # delete users
    resp = requests.get(f"{BASE_URL}/users/")
    if resp.status_code == 200:
        for user in resp.json():
            requests.delete(f"{BASE_URL}/users/{user.get('id')}")


def run_tests():
    """
    Perform a full CRUD cycle and time each step.
    Returns (success_flag, timings_dict).
    """
    cleanup()
    timings = {}
    success = True

    # list users
    t0 = time.time()
    r = requests.get(f"{BASE_URL}/users/")
    timings['list_users'] = time.time() - t0
    success &= (r.status_code == 200 and r.json() == [])

    # create user
    email = f"bench_{uuid.uuid4().hex}@example.com"
    t0 = time.time()
    r = requests.post(f"{BASE_URL}/users/", json={'name':'B','email':email})
    timings['create_user'] = time.time() - t0
    success &= (r.status_code == 200)
    uid = r.json().get('id', None)

    # get user
    t0 = time.time()
    r = requests.get(f"{BASE_URL}/users/{uid}")
    timings['get_user'] = time.time() - t0
    success &= (r.status_code == 200)

    # create item
    t0 = time.time()
    r = requests.post(f"{BASE_URL}/items/", params={'user_id':uid}, json={'title':'X','description':'Y'})
    timings['create_item'] = time.time() - t0
    success &= (r.status_code == 200)
    iid = r.json().get('id', None)

    # get item
    t0 = time.time()
    r = requests.get(f"{BASE_URL}/items/{iid}")
    timings['get_item'] = time.time() - t0
    success &= (r.status_code == 200)

    # list items
    t0 = time.time()
    r = requests.get(f"{BASE_URL}/items/")
    timings['list_items'] = time.time() - t0
    success &= (r.status_code == 200 and len(r.json()) == 1)

    return success, timings


def main():
    print("Starting CRUD benchmark against:", BASE_URL)
    ok, times = run_tests()
    print("\nResults:")
    print(f"  All tests passed: {ok}")
    for step, dt in times.items(): print(f"  {step:12}: {dt*1000:8.2f} ms")

    lines = count_lines(APP_DIR)
    print(f"\nTotal lines of application code: {lines}")

    zip_app()

    if not ok:
        print("\nWARNING: Some tests failed.")

if __name__ == '__main__':
    try:
        import requests
    except ImportError:
        print("Install requests: pip install requests")
        sys.exit(1)
    main()
