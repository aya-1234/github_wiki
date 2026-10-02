import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values


@dataclass(slots=True)
class Settings:
    source_path: Path | None = None
    destination_path: Path | None = None
    default_mode: str = "copy"
    move_warning: bool = True
    create_date_folder: bool = True
    duplicate_algorithm: str = "sha256"
    supported_extensions: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".heic", ".heif", ".RW2",".NRW",".NEF",".CR3",".CR2",)
    date_fallback: str = "file_mtime"
    env_path: Path = field(default_factory=lambda: Path(".env"))

    def __post_init__(self) -> None:
        self.default_mode = self.default_mode.lower()
        self.duplicate_algorithm = self.duplicate_algorithm.lower()
        self.date_fallback = self.date_fallback.lower()
        self.supported_extensions = tuple(
            extension.lower() if extension.startswith(".") else f".{extension.lower()}"
            for extension in self.supported_extensions
        )
        if self.default_mode not in {"copy", "move"}:
            raise ValueError("DEFAULT_MODE must be 'copy' or 'move'")
        if self.duplicate_algorithm != "sha256":
            raise ValueError("Only SHA-256 duplicate detection is supported")
        if self.date_fallback not in {"file_mtime", "skip"}:
            raise ValueError("DATE_FALLBACK must be 'file_mtime' or 'skip'")

    @classmethod
    def load(cls, path: Path = Path(".env")) -> Settings:
        raw_values = dotenv_values(path)
        values: dict[str, str] = {key: value for key, value in raw_values.items() if value is not None}
        values.update({key: value for key, value in os.environ.items() if key in values or key in {
            "SOURCE_PATH", "DESTINATION_PATH", "DEFAULT_MODE", "MOVE_WARNING",
            "CREATE_DATE_FOLDER", "DUPLICATE_ALGORITHM", "SUPPORTED_EXTENSIONS", "DATE_FALLBACK",
        }})
        source = values.get("SOURCE_PATH", "").strip()
        destination = values.get("DESTINATION_PATH", "").strip()
        extensions = values.get("SUPPORTED_EXTENSIONS", ".jpg,.jpeg,.png,.heic,.heif")
        return cls(
            source_path=Path(source).expanduser() if source else None,
            destination_path=Path(destination).expanduser() if destination else None,
            default_mode=values.get("DEFAULT_MODE", "copy"),
            move_warning=_as_bool(values.get("MOVE_WARNING", "true")),
            create_date_folder=_as_bool(values.get("CREATE_DATE_FOLDER", "true")),
            duplicate_algorithm=values.get("DUPLICATE_ALGORITHM", "sha256"),
            supported_extensions=tuple(part.strip() for part in extensions.split(",") if part.strip()),
            date_fallback=values.get("DATE_FALLBACK", "file_mtime"),
            env_path=path,
        )

    def save(self) -> None:
        entries = {
            "SOURCE_PATH": str(self.source_path or ""),
            "DESTINATION_PATH": str(self.destination_path or ""),
            "DEFAULT_MODE": self.default_mode,
            "MOVE_WARNING": str(self.move_warning).lower(),
            "CREATE_DATE_FOLDER": str(self.create_date_folder).lower(),
            "DUPLICATE_ALGORITHM": self.duplicate_algorithm,
            "SUPPORTED_EXTENSIONS": ",".join(self.supported_extensions),
            "DATE_FALLBACK": self.date_fallback,
        }
        content = "".join(f"{key}={_quote_env(value)}\n" for key, value in entries.items())
        self.env_path.write_text(content, encoding="utf-8")


def _as_bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _quote_env(value: str) -> str:
    if any(char in value for char in " #\"'"):
        return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'
    return value
