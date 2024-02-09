import shutil
import tempfile
from typing import ContextManager


class DirUtils:
    @staticmethod
    def temporary_dir() -> ContextManager[str]:
        temp_dir = tempfile.mkdtemp()
        try:
            yield temp_dir
        finally:
            shutil.rmtree(temp_dir)
