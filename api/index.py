import sys
import os

# Add backend directory to sys.path so modules like database, core, fetchers, etc. import cleanly
backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from main import app
