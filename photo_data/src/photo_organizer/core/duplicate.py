import hashlib
from pathlib import Path


class DuplicateDetector:
    def calculate_hash(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
        return digest.hexdigest()

    def is_duplicate(self, source: Path, destination: Path) -> bool:
        if not destination.is_file() or source.stat().st_size != destination.stat().st_size:
            return False
        return self.calculate_hash(source) == self.calculate_hash(destination)

    def find_duplicate(self, source: Path, directory: Path) -> Path | None:
        source_size = source.stat().st_size
        source_hash: str | None = None
        for candidate in sorted(directory.iterdir(), key=lambda item: item.name.casefold()):
            if candidate.resolve() == source.resolve():
                continue
            if not candidate.is_file() or candidate.stat().st_size != source_size:
                continue
            if source_hash is None:
                source_hash = self.calculate_hash(source)
            if self.calculate_hash(candidate) == source_hash:
                return candidate
        return None


def generate_unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    index = 1
    while True:
        candidate = path.with_name(f"{path.stem}_{index:03d}{path.suffix}")
        if not candidate.exists():
            return candidate
        index += 1
