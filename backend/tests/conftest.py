import os
import tempfile

# Must be set BEFORE the app is imported, so tests never touch the real database.
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-hs256"
