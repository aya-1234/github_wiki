from pathlib import Path
import subprocess

import pytest

from scripts.stage_wiki_page import stage
from scripts.wiki_pr import added_pages, publish_pages
from wiki_app import AppError, publish


def git(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def commit(directory: Path, message: str) -> str:
    git('add', '--all', cwd=directory)
    git('-c', 'user.name=Test', '-c', 'user.email=test@localhost', 'commit', '-m', message, cwd=directory)
    return git('rev-parse', 'HEAD', cwd=directory)


def test_stage_pdf_for_review(tmp_path):
    source = Path(__file__).resolve().parents[1] / 'test.pdf'
    staged = stage(source, 'PDF-Import-Test', tmp_path)
    assert 'GitHub Wiki PDF test' in staged.read_text()
    with pytest.raises(AppError) as exc:
        stage(source, 'PDF-Import-Test', tmp_path)
    assert exc.value.code == 'PAGE_EXISTS'


def test_added_page_publishes_to_local_wiki(tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()
    git('init', str(repo))
    (repo / 'README.md').write_text('base')
    base = commit(repo, 'base')
    pages_dir = repo / 'wiki-pages'
    pages_dir.mkdir()
    (pages_dir / 'PDF-Test.md').write_text('## PDF 1ページ目\n\nHello\n')
    head = commit(repo, 'add wiki page')
    pages = added_pages(base, head, root=repo)
    assert pages == [pages_dir / 'PDF-Test.md']
    assert added_pages(base, head, root=repo, pull_request=True) == pages

    remote = tmp_path / 'wiki.git'
    git('init', '--bare', str(remote))
    source = tmp_path / 'source'
    git('clone', str(remote), str(source))
    (source / 'Home.md').write_text('Home')
    commit(source, 'initial wiki')
    git('push', 'origin', 'HEAD', cwd=source)
    results = publish_pages(pages, 'owner/repo', lambda repository, title, body: publish(repository, title, body, test_remote=str(remote)))
    assert len(results) == 1 and results[0]['pageUrl'].endswith('/PDF-Test')
    git('pull', '--ff-only', cwd=source)
    assert (source / 'PDF-Test.md').read_text() == pages[0].read_text()


def test_existing_page_edit_is_rejected(tmp_path):
    git('init', str(tmp_path))
    pages_dir = tmp_path / 'wiki-pages'
    pages_dir.mkdir()
    (pages_dir / 'Existing.md').write_text('original')
    base = commit(tmp_path, 'base')
    (pages_dir / 'Existing.md').write_text('changed')
    head = commit(tmp_path, 'edit')
    with pytest.raises(ValueError, match='変更・削除'):
        added_pages(base, head, root=tmp_path)


def test_nested_page_is_rejected(tmp_path):
    git('init', str(tmp_path))
    (tmp_path / 'README.md').write_text('base')
    base = commit(tmp_path, 'base')
    nested = tmp_path / 'wiki-pages' / 'nested'
    nested.mkdir(parents=True)
    (nested / 'Page.md').write_text('content')
    head = commit(tmp_path, 'nested')
    with pytest.raises(ValueError, match='wiki-pages'):
        added_pages(base, head, root=tmp_path)
