import sys
from pathlib import Path

# Добавляем корень репозитория (родительскую папку tests) в PYTHONPATH
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

