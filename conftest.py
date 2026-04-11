import sys
from pathlib import Path

# Add src/backend to path for imports
backend_path = Path(__file__).parent / "src" / "backend"
sys.path.insert(0, str(backend_path))
