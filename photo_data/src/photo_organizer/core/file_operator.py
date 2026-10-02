import hashlib
import os
from pathlib import Path


class FileOperator:
    def copy(self, source: Path, destination: Path) -> None:
        if not source.is_file():
            raise FileNotFoundError(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        created = False
        try:
            with source.open("rb") as reader, destination.open("xb") as writer:
                created = True
                while chunk := reader.read(1024 * 1024):
                    digest.update(chunk)
                    writer.write(chunk)
                writer.flush()
            if destination.stat().st_size != source.stat().st_size or _hash(destination) != digest.hexdigest():
                raise OSError(f"Copy verification failed: {destination}")
            stat = source.stat()

            os.utime(
                destination,
                ns=(stat.st_atime_ns, stat.st_mtime_ns),
            )
        except Exception:
            if created:
                destination.unlink(missing_ok=True)
            raise

    def move(self, source: Path, destination: Path) -> None:
        self.copy(source, destination)
        try:
            if _hash(source) != _hash(destination):
                raise OSError(f"Source changed during move; keeping original: {source}")
            source.unlink()
        except OSError:
            destination.unlink(missing_ok=True)
            raise


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()
