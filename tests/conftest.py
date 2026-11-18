import os
import tempfile

# Must be set before the app imports the database module.
# Set TEST_DATABASE_URL to run the suite against Postgres (needs supabase/migrations applied).
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{tempfile.mkdtemp()}/test.db"
os.environ["ADMIN_EMAIL"] = "admin@test.local"
os.environ["ADMIN_PASSWORD"] = "admin-pass-1"
os.environ["LEGACY_WORK_FACTOR"] = "1"  # keep the deliberately slow engine fast under test
os.environ["LEGACY_TARGET_SECONDS"] = "0"  # fixed tiny factor in tests, no time-targeting
