"""Convert one supported document into a reviewable wiki-pages Markdown file."""
from __future__ import annotations

import argparse
from pathlib import Path

from wiki_app import AppError, convert, stage_page

ROOT = Path(__file__).resolve().parents[1]


def stage(source: Path, title: str, root: Path = ROOT) -> Path:
    result = convert(source.name, source.read_bytes())
    saved = stage_page(title, result['markdown'], root=root)
    path = root / saved['path']
    for warning in result['warnings']:
        print(f'警告: {warning}')
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--title', required=True)
    args = parser.parse_args()
    try:
        print(stage(args.source, args.title))
    except (AppError, OSError) as exc:
        parser.exit(1, f'{exc}\n')


if __name__ == '__main__':
    main()
