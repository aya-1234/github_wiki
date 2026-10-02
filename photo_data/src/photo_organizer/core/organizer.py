import logging
from collections.abc import Callable
from pathlib import Path

from photo_organizer.config.settings import Settings
from photo_organizer.core.destination import DestinationResolver
from photo_organizer.core.duplicate import DuplicateDetector, generate_unique_path
from photo_organizer.core.file_operator import FileOperator
from photo_organizer.core.metadata import MetadataReader
from photo_organizer.core.scanner import PhotoScanner
from photo_organizer.models.result import ProcessResult

logger = logging.getLogger(__name__)
ProgressCallback = Callable[[int, int, Path, str], None]
CancelCallback = Callable[[], bool]


class Organizer:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._scanner = PhotoScanner(settings.supported_extensions)
        self._metadata = MetadataReader(settings.date_fallback)
        self._resolver = DestinationResolver(settings.create_date_folder)
        self._duplicates = DuplicateDetector()
        self._files = FileOperator()

    def run(
        self,
        source: Path,
        destination: Path,
        mode: str,
        *,
        progress: ProgressCallback | None = None,
        cancelled: CancelCallback | None = None,
    ) -> ProcessResult:
        if mode not in {"copy", "move"}:
            raise ValueError("mode must be 'copy' or 'move'")
        source = source.expanduser().resolve()
        destination = destination.expanduser().resolve()
        if source == destination or source in destination.parents or destination in source.parents:
            raise ValueError("Source and destination directories cannot overlap")
        paths = self._scanner.scan(source)
        destination.mkdir(parents=True, exist_ok=True)
        result = ProcessResult()
        total = len(paths)
        for index, path in enumerate(paths, start=1):
            if cancelled and cancelled():
                result.cancelled = True
                break
            result.processed += 1
            previous_errors = result.errors
            if progress:
                progress(index - 1, total, path, "processing")
            try:
                captured_at = self._metadata.get_capture_datetime(path)
                if captured_at is None:
                    result.skipped += 1
                    logger.warning("Skipping photo without usable capture date: %s", path)
                    continue
                target_dir = self._resolver.resolve(destination, captured_at)
                target_dir.mkdir(parents=True, exist_ok=True)
                duplicate = self._duplicates.find_duplicate(path, target_dir)
                if duplicate is not None:
                    result.skipped += 1
                    logger.info("Skipping duplicate %s (matches %s)", path, duplicate)
                    continue
                target = generate_unique_path(target_dir / path.name)
                if mode == "move":
                    self._files.move(path, target)
                    result.moved += 1
                else:
                    self._files.copy(path, target)
                    result.copied += 1
                logger.info("%s %s -> %s", mode.upper(), path, target)
            except OSError as error:
                result.record_error(path, error)
                logger.exception("Failed to process photo %s", path)
            except Exception as error:
                result.record_error(path, error)
                logger.exception("Unexpected error processing photo %s", path)
            finally:
                if progress:
                    status = "error" if result.errors > previous_errors else "complete"
                    progress(index, total, path, status)
        return result
