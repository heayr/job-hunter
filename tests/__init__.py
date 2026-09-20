import os
import sys

# Guarantee test isolation: prevent test suites from polluting production jobs.db
os.environ["JOB_HUNTER_ENV"] = "test"
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
test_db_path = os.path.join(project_root, "test_jobs.db")
os.environ["JOB_HUNTER_DB_PATH"] = test_db_path

try:
    from tracker.db import init_db, sync_canonical_profiles_to_db, set_db_path
    set_db_path(test_db_path)
    init_db(test_db_path)
    sync_canonical_profiles_to_db()
except Exception as e:
    sys.stderr.write(f"Warning: Failed to initialize test database in tests/__init__.py: {e}\n")
