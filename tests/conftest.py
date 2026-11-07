import os
import tempfile

# Must be set before the app imports the database module.
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
os.environ["ADMIN_EMAIL"] = "admin@test.local"
os.environ["ADMIN_PASSWORD"] = "admin-pass-1"
os.environ["LEGACY_WORK_FACTOR"] = "1"  # keep the deliberately slow engine fast under test
