from datetime import datetime
from pathlib import Path


class DestinationResolver:
    def __init__(self, create_date_folder: bool = True) -> None:
        self._create_date_folder = create_date_folder

    def resolve(self, destination: Path, captured_at: datetime) -> Path:
        if not self._create_date_folder:
            return destination
        return destination / f"{captured_at.year:04d}" / f"{captured_at.month:02d}" / f"{captured_at.day:02d}"
