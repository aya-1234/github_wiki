"""Validate reviewed Wiki pages and publish only additions after a merge."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
from typing import Callable

from wiki_app import AppError, check_body, check_title, publish

ROOT = Path(__file__).resolve().parents[1]
def added_pages(base: str, head: str, *, pull_request: bool = False, root: Path = ROOT) -> list[Path]:
    if not base or not head:
        raise ValueError('比較対象のコミットが必要です')
    comparison = f'{base}...{head}' if pull_request else f'{base}..{head}'
    process = subprocess.run(
        ['git', 'diff', '--no-renames', '--name-status', comparison, '--', 'wiki-pages/'],
        cwd=root, capture_output=True, text=True, check=True,
    )
    pages = []
    for line in process.stdout.splitlines():
        status, _, name = line.partition('\t')
        if status != 'A':
            raise ValueError(f'既存 Wiki ページの変更・削除はできません: {name}')
        relative = Path(name)
        if relative.parent != Path('wiki-pages') or relative.suffix != '.md':
            raise ValueError(f'Wiki ページは wiki-pages/*.md に配置してください: {name}')
        page = root / relative
        if page.is_symlink() or not page.is_file():
            raise ValueError(f'通常の Markdown ファイルが必要です: {name}')
        check_title(page.stem)
        check_body(page.read_text(encoding='utf-8'))
        pages.append(page)
    return pages


def publish_pages(pages: list[Path], repository: str, publisher: Callable = publish) -> list[dict]:
    results = []
    for page in pages:
        result = publisher(repository, page.stem, page.read_text(encoding='utf-8'))
        results.append(result)
        print(f'公開: {page.name} → {result["pageUrl"]}')
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('validate', 'publish'))
    parser.add_argument('--base', required=True)
    parser.add_argument('--head', required=True)
    parser.add_argument('--pr', action='store_true', help='compare from the PR merge base')
    args = parser.parse_args()
    try:
        pages = added_pages(args.base, args.head, pull_request=args.pr)
        print(f'検証済み新規ページ: {len(pages)} 件')
        if args.action == 'publish' and pages:
            if not os.environ.get('WIKI_PUSH_TOKEN'):
                raise ValueError('Actions secret WIKI_PUSH_TOKEN が必要です')
            repository = os.environ.get('GITHUB_REPOSITORY', '')
            publish_pages(pages, repository)
        return 0
    except (AppError, ValueError, UnicodeError, OSError, subprocess.CalledProcessError) as exc:
        print(f'Wiki 公開エラー: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
