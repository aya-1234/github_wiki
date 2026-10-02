from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class Photo:
    source_path: Path
    captured_at: datetime | None
    file_size: int
    hash_value: str | None = None

    @property
    def filename(self) -> str:
        return self.source_path.name

    @property
    def extension(self) -> str:
        return self.source_path.suffix
