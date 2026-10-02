from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class ProcessResult:
    processed: int = 0
    copied: int = 0
    moved: int = 0
    skipped: int = 0
    errors: int = 0
    error_messages: list[str] = field(default_factory=list)
    cancelled: bool = False

    def record_error(self, path: Path, error: Exception) -> None:
        self.errors += 1
        self.error_messages.append(f"{path}: {error}")
