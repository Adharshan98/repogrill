import os
import tempfile

# Point the app at a throwaway database before any app code is imported
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"

from app.db import init_db  # noqa: E402

init_db()
