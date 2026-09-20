import uuid
from abc import ABC, abstractmethod
from pathlib import Path


class FileStorage(ABC):
    @abstractmethod
    def save(self, content: bytes, original_filename: str) -> str:
        """Persists content, returns a stored-path identifier."""


class LocalFileStorage(FileStorage):
    """Writes to STORAGE_DIR on the local filesystem.

    ponytail: local disk instead of an S3-compatible client for this first
    build -- no object storage credentials were available. The interface is
    the seam: a real S3/GCS-backed implementation drops in behind `save`
    without touching any caller. Upgrade trigger: deploying beyond a single
    instance/disk, or needing signed URLs for direct client upload.
    """

    def __init__(self, base_dir: str):
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, content: bytes, original_filename: str) -> str:
        suffix = Path(original_filename).suffix
        stored_name = f"{uuid.uuid4().hex}{suffix}"
        path = self._base_dir / stored_name
        path.write_bytes(content)
        return str(path)


def get_file_storage() -> FileStorage:
    from app.config import get_settings

    return LocalFileStorage(get_settings().storage_dir)
