import asyncio
import shutil
import subprocess
from types import SimpleNamespace

import anyio.to_thread
import httpx
import wiki_app

import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse

from wiki_app import (
    AppError, PreviewRequest, PublishRequest, check_body, check_repository,
    check_title, convert, git, local_only, pdf_command, preview_api, publish,
    publish_api,
)


def pdf_bytes(*pages):
    if not pages:
        pages = ('First page',)
    page_ids = [4 + 2 * n for n in range(len(pages))]
    kids = b' '.join(f'{number} 0 R'.encode() for number in page_ids)
    objects = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [' + kids + b'] /Count ' + str(len(pages)).encode() + b' >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    ]
    for n, text in enumerate(pages):
        stream = f'BT /F1 16 Tf 40 100 Td ({text}) Tj ET'.encode()
        objects.extend([
            f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Resources << /Font << /F1 3 0 R >> >> /Contents {5+2*n} 0 R >>'.encode(),
            b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream',
        ])
    out=bytearray(b'%PDF-1.4\n');offsets=[0]
    for n,obj in enumerate(objects,1):
        offsets.append(len(out));out+=f'{n} 0 obj\n'.encode()+obj+b'\nendobj\n'
    start=len(out);out+=f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode()
    for pos in offsets[1:]:out+=f'{pos:010} 00000 n \n'.encode()
    out+=f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode()
    return bytes(out)


def run(*args,cwd=None):
    return subprocess.run(['git',*args],cwd=cwd,check=True,capture_output=True,text=True).stdout.strip()


@pytest.fixture
def wiki_remote(tmp_path):
    remote=tmp_path/'wiki.git';run('init','--bare',str(remote))
    source=tmp_path/'source';run('clone',str(remote),str(source))
    (source/'Home.md').write_text('Welcome')
    run('add','Home.md',cwd=source)
    run('-c','user.name=Test','-c','user.email=test@example.com','commit','-m','Initial',cwd=source)
    run('push','origin','HEAD',cwd=source)
    return remote, source


@pytest.fixture
def asgi_client(monkeypatch):
    # The execution sandbox cannot start worker threads. The ASGI route,
    # middleware, and response stack still run; only worker scheduling is inline.
    async def inline(func, *args, **kwargs):
        return func(*args)
    monkeypatch.setattr(anyio.to_thread, 'run_sync', inline)
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=wiki_app.app),
        base_url='http://127.0.0.1:8000',
    )


def test_markdown_conversion_and_title():
    result=convert('Guide.md',b'\xef\xbb\xbf# Guide\r\n\r\n[ref](assets/a.png)')
    assert result['title']=='Guide'
    assert '\r' not in result['markdown']
    assert result['warnings']
    with pytest.raises(AppError) as exc:convert('bad.md',b'\xff')
    assert exc.value.code=='INVALID_ENCODING'
    with pytest.raises(AppError):check_title('../evil')
    with pytest.raises(AppError):check_title('Home')


def test_relative_references_are_listed_and_rechecked_in_preview():
    body='[Guide][ref]\n\n[ref]: ./guide.md\n\n![logo](img/logo.png)\n\n![root](/images/root.png)\n\n`[example](not-a-link.md)`'
    result=convert('references.md',body.encode())
    assert result['sourceWarnings']==[]
    assert any('相対リンク: ./guide.md' in warning for warning in result['warnings'])
    assert any('相対画像: img/logo.png' in warning for warning in result['warnings'])
    assert any('相対画像: /images/root.png' in warning for warning in result['warnings'])
    assert all('not-a-link.md' not in warning for warning in result['warnings'])
    updated=preview_api(PreviewRequest(markdown='[Guide](https://example.com/guide)\n\n![logo](https://example.com/logo.png)'))
    assert updated['warnings']==[]


def test_pdf_conversion():
    result=convert('sample.pdf',pdf_bytes())
    assert '## PDF 1ページ目' in result['markdown']
    assert 'First page' in result['markdown']
    with pytest.raises(AppError) as exc:convert('image.pdf',pdf_bytes(''))
    assert exc.value.code=='PDF_NO_TEXT'


def test_pdf_page_order_and_limit():
    result = convert('ordered.pdf', pdf_bytes('Alpha', 'Beta'))
    body = result['markdown']
    assert body.index('## PDF 1ページ目') < body.index('Alpha') < body.index('## PDF 2ページ目') < body.index('Beta')
    with pytest.raises(AppError) as exc:
        convert('large.pdf', pdf_bytes(*(['x'] * 101)))
    assert exc.value.code == 'PDF_TOO_MANY_PAGES'
    with pytest.raises(AppError) as exc:
        convert('broken.pdf', b'%PDF-not-a-document')
    assert exc.value.code == 'INVALID_FILE'


@pytest.mark.parametrize(('name', 'data', 'code'), [
    ('bad.txt', b'text', 'UNSUPPORTED_FORMAT'),
    ('bad.md', b'\xff', 'INVALID_ENCODING'),
    ('empty.md', b' \n', 'EMPTY_DOCUMENT'),
    ('nul.md', b'a\x00b', 'EMPTY_DOCUMENT'),
    ('fake.pdf', b'not a PDF', 'INVALID_FILE'),
    ('../escape.md', b'hello', 'INVALID_FILE'),
])
def test_conversion_rejects_invalid_input(name, data, code):
    with pytest.raises(AppError) as exc:
        convert(name, data)
    assert exc.value.code == code


def test_upload_and_body_limits():
    with pytest.raises(AppError) as exc:
        convert('large.md', b'a' * (20 * 1024 * 1024 + 1))
    assert exc.value.code == 'FILE_TOO_LARGE' and exc.value.status == 413
    with pytest.raises(AppError) as exc:
        check_body('a' * (2 * 1024 * 1024 + 1))
    assert exc.value.code == 'CONTENT_TOO_LARGE' and exc.value.status == 413


@pytest.mark.parametrize('value', [
    'owner', 'owner/repo/extra', 'bad_owner/repo', '-owner/repo',
    'owner/../repo', 'owner/.hidden', 'owner/repo.',
])
def test_rejects_invalid_repository(value):
    with pytest.raises(AppError) as exc:
        check_repository(value)
    assert exc.value.code == 'INVALID_REPOSITORY'


@pytest.mark.parametrize('value', [
    '', ' ', ' Home', '_Sidebar', '_Footer', 'name/', 'a:b', 'name.',
    'name\nnext', 'a' * 101,
])
def test_rejects_invalid_title(value):
    with pytest.raises(AppError) as exc:
        check_title(value)
    assert exc.value.code == 'INVALID_TITLE'


def test_title_unicode_normalization():
    assert check_title('e\u0301') == 'é'


def test_encrypted_pdf(tmp_path):
    if not shutil.which('mutool'):
        pytest.skip('mutool is required to generate an encrypted PDF fixture')
    original=tmp_path/'plain.pdf';secret=tmp_path/'secret.pdf'
    original.write_bytes(pdf_bytes())
    subprocess.run(['mutool','clean','-E','aes-128','-O','owner','-U','user',str(original),str(secret)],check=True,capture_output=True)
    with pytest.raises(AppError) as exc:convert('secret.pdf',secret.read_bytes())
    assert exc.value.code=='PDF_ENCRYPTED'


def test_git_publish_add_only(wiki_remote):
    remote, source = wiki_remote
    result=publish('owner/repo','操作手順','# Hello',test_remote=str(remote))
    assert len(result['commitSha'])==40
    assert result['pageUrl'].endswith('/wiki/%E6%93%8D%E4%BD%9C%E6%89%8B%E9%A0%86')
    run('pull','--ff-only',cwd=source)
    assert (source/'操作手順.md').read_text()=='# Hello'
    with pytest.raises(AppError) as exc:publish('owner/repo','操作手順','overwrite',test_remote=str(remote))
    assert exc.value.code=='PAGE_EXISTS'
    assert (source/'Home.md').read_text()=='Welcome'


def test_git_rejects_case_and_unicode_collisions(wiki_remote):
    remote, source = wiki_remote
    (source/'Guide.markdown').write_text('original')
    (source/'é.md').write_text('accented')
    run('add','Guide.markdown','é.md',cwd=source)
    run('-c','user.name=Test','-c','user.email=test@example.com','commit','-m','Existing pages',cwd=source)
    run('push','origin','HEAD',cwd=source)
    for page in ('guide', 'e\u0301'):
        with pytest.raises(AppError) as exc:
            publish('owner/repo',page,'replacement',test_remote=str(remote))
        assert exc.value.code == 'PAGE_EXISTS'
    assert (source/'Guide.markdown').read_text() == 'original'
    assert (source/'é.md').read_text() == 'accented'


@pytest.mark.parametrize(('stderr', 'code', 'status'), [
    ('Authentication failed', 'GIT_AUTH_FAILED', 401),
    ('Permission denied', 'WIKI_WRITE_DENIED', 403),
    ('Repository not found', 'WIKI_UNAVAILABLE', 404),
    ('non-fast-forward', 'REMOTE_CHANGED', 409),
    ('unexpected remote error', 'GIT_REMOTE_ERROR', 502),
])
def test_git_failure_classification(monkeypatch, stderr, code, status):
    monkeypatch.setattr(wiki_app.subprocess, 'run', lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout='', stderr=stderr))
    with pytest.raises(AppError) as exc:
        git(['clone', 'unused'])
    assert (exc.value.code, exc.value.status) == (code, status)
    assert stderr not in exc.value.message


def test_git_timeout(monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 120)
    monkeypatch.setattr(wiki_app.subprocess, 'run', timeout)
    with pytest.raises(AppError) as exc:
        git(['clone', 'unused'])
    assert (exc.value.code, exc.value.status) == ('GIT_TIMEOUT', 504)


@pytest.mark.parametrize(('failure', 'code', 'status'), [
    (FileNotFoundError(), 'PDF_TOOL_MISSING', 500),
    (subprocess.TimeoutExpired(['pdfinfo'], 30), 'INVALID_FILE', 400),
])
def test_pdf_tool_failures(monkeypatch, failure, code, status):
    def fail(*args, **kwargs):
        raise failure
    monkeypatch.setattr(wiki_app.subprocess, 'run', fail)
    with pytest.raises(AppError) as exc:
        pdf_command(['pdfinfo', 'unused'])
    assert (exc.value.code, exc.value.status) == (code, status)


def test_preview_and_publish_validation(monkeypatch):
    monkeypatch.setenv('ALLOW_DIRECT_WIKI_PUBLISH', '1')
    result=preview_api(PreviewRequest(markdown='<script>alert(1)</script>\n\n[bad](javascript:alert(1))'))
    assert '<script>' not in result['html']
    assert 'href="javascript:' not in result['html']
    with pytest.raises(AppError) as exc:
        publish_api(PublishRequest(repository='x/y',title='Home',markdown='abc'))
    assert exc.value.code=='INVALID_TITLE'


def test_preview_rejects_oversized_markdown():
    with pytest.raises(AppError) as exc:
        preview_api(PreviewRequest(markdown='x' * (2 * 1024 * 1024 + 1)))
    assert (exc.value.code, exc.value.status) == ('CONTENT_TOO_LARGE', 413)


def test_git_detects_remote_change(tmp_path):
    remote=tmp_path/'wiki.git';run('init','--bare',str(remote))
    first=tmp_path/'first';run('clone',str(remote),str(first))
    (first/'Home.md').write_text('Home')
    run('add','Home.md',cwd=first)
    run('-c','user.name=Test','-c','user.email=test@example.com','commit','-m','Initial',cwd=first)
    run('push','origin','HEAD',cwd=first)
    stale=tmp_path/'stale';run('clone',str(remote),str(stale))
    (first/'new.md').write_text('new');run('add','new.md',cwd=first)
    run('-c','user.name=Test','-c','user.email=test@example.com','commit','-m','Next',cwd=first)
    run('push','origin','HEAD',cwd=first)
    (stale/'other.md').write_text('other');run('add','other.md',cwd=stale)
    run('-c','user.name=Test','-c','user.email=test@example.com','commit','-m','Stale',cwd=stale)
    branch=run('symbolic-ref','--short','HEAD',cwd=stale)
    with pytest.raises(AppError) as exc:git(['push','origin',f'HEAD:{branch}'],stale)
    assert exc.value.code=='REMOTE_CHANGED'


@pytest.mark.parametrize(('host', 'origin', 'status'), [
    ('127.0.0.1:8000', 'http://127.0.0.1:8000', 200),
    ('localhost:8000', 'http://localhost:8000', 200),
    ('127.0.0.1:8000', 'https://evil.example', 403),
    ('evil.example:8000', 'http://127.0.0.1:8000', 403),
])
def test_origin_guard(host, origin, status):
    async def exercise():
        scope={'type':'http','method':'POST','path':'/api/publish','headers':[(b'host',host.encode()),(b'origin',origin.encode())]}
        async def next_handler(_request):
            return JSONResponse({'ok':True})
        return await local_only(Request(scope),next_handler)

    assert asyncio.run(exercise()).status_code == status


def test_http_conversion_preview_and_errors(asgi_client):
    async def exercise():
        async with asgi_client as client:
            page = await client.get('/')
            assert page.status_code == 200 and 'GitHub Wiki に追加' in page.text
            converted = await client.post('/api/convert', files={'file': ('guide.md', b'# Guide', 'text/markdown')})
            assert converted.status_code == 200 and converted.json()['markdown'] == '# Guide'
            preview = await client.post('/api/preview', json={'markdown': '<script>bad()</script>\n\n# Safe'})
            assert preview.status_code == 200
            assert '<script>' not in preview.json()['html']
            bad = await client.post('/api/convert', files={'file': ('bad.txt', b'bad', 'text/plain')})
            assert bad.status_code == 422 and bad.json()['code'] == 'UNSUPPORTED_FORMAT'
            large = await client.post('/api/convert', files={'file': ('large.md', b'a' * (20 * 1024 * 1024 + 1), 'text/markdown')})
            assert large.status_code == 413 and large.json()['code'] == 'FILE_TOO_LARGE'
            denied = await client.post('/api/preview', json={'markdown': 'ok'}, headers={'origin': 'https://evil.example'})
            assert denied.status_code == 403 and denied.json()['code'] == 'INVALID_ORIGIN'
    asyncio.run(exercise())


def test_http_publish_and_duplicate(asgi_client, wiki_remote, monkeypatch):
    monkeypatch.setenv('ALLOW_DIRECT_WIKI_PUBLISH', '1')
    remote, source = wiki_remote
    original_publish = wiki_app.publish
    monkeypatch.setattr(wiki_app, 'publish', lambda repository, title, markdown: original_publish(repository, title, markdown, test_remote=str(remote)))

    async def exercise():
        async with asgi_client as client:
            payload = {'repository': 'owner/repo', 'title': 'New', 'markdown': '# New'}
            first = await client.post('/api/publish', json=payload)
            assert first.status_code == 201
            assert first.json()['pageUrl'].endswith('/wiki/New')
            assert len(first.json()['commitSha']) == 40
            second = await client.post('/api/publish', json=payload)
            assert second.status_code == 409 and second.json()['code'] == 'PAGE_EXISTS'
            invalid = await client.post('/api/publish', json={**payload, 'title': 'Home'})
            assert invalid.status_code == 400 and invalid.json()['code'] == 'INVALID_TITLE'
    asyncio.run(exercise())
    run('pull','--ff-only',cwd=source)
    assert (source/'New.md').read_text() == '# New'


@pytest.mark.parametrize(('code', 'status'), [
    ('GIT_AUTH_FAILED', 401),
    ('WIKI_WRITE_DENIED', 403),
    ('WIKI_UNAVAILABLE', 404),
    ('REMOTE_CHANGED', 409),
    ('GIT_TIMEOUT', 504),
])
def test_http_publish_errors_are_sanitized(asgi_client, monkeypatch, code, status):
    monkeypatch.setenv('ALLOW_DIRECT_WIKI_PUBLISH', '1')
    def fail(*args, **kwargs):
        raise AppError(code, '公開できません', status)
    monkeypatch.setattr(wiki_app, 'publish', fail)

    async def exercise():
        async with asgi_client as client:
            response = await client.post('/api/publish', json={'repository':'owner/repo','title':'New','markdown':'text'})
            assert response.status_code == status
            assert response.json() == {'code': code, 'message': '公開できません'}
    asyncio.run(exercise())


def test_http_stage_for_pr_and_direct_publish_disabled(asgi_client, tmp_path, monkeypatch):
    monkeypatch.delenv('ALLOW_DIRECT_WIKI_PUBLISH', raising=False)
    original_stage = wiki_app.stage_page
    monkeypatch.setattr(wiki_app, 'stage_page', lambda title, markdown: original_stage(title, markdown, root=tmp_path))

    async def exercise():
        async with asgi_client as client:
            staged = await client.post('/api/stage', json={'title': 'New', 'markdown': '# New'})
            assert staged.status_code == 201 and staged.json()['path'] == 'wiki-pages/New.md'
            duplicate = await client.post('/api/stage', json={'title': 'New', 'markdown': '# Changed'})
            assert duplicate.status_code == 409 and duplicate.json()['code'] == 'PAGE_EXISTS'
            direct = await client.post('/api/publish', json={'repository': 'owner/repo', 'title': 'Direct', 'markdown': '# Direct'})
            assert direct.status_code == 403 and direct.json()['code'] == 'DIRECT_PUBLISH_DISABLED'
    asyncio.run(exercise())
    assert (tmp_path / 'wiki-pages' / 'New.md').read_text() == '# New'


def test_failed_push_cleans_temporary_clone(wiki_remote, tmp_path, monkeypatch):
    remote, source = wiki_remote
    original_temp = wiki_app.tempfile.TemporaryDirectory
    original_git = wiki_app.git
    scratch = tmp_path / 'scratch'
    scratch.mkdir()

    def temporary_directory(*args, **kwargs):
        return original_temp(*args, **kwargs, dir=scratch)

    def fail_on_push(args, cwd=None):
        if args[0] == 'push':
            raise AppError('GIT_REMOTE_ERROR', '公開できません', 502)
        return original_git(args, cwd)

    monkeypatch.setattr(wiki_app.tempfile, 'TemporaryDirectory', temporary_directory)
    monkeypatch.setattr(wiki_app, 'git', fail_on_push)
    with pytest.raises(AppError) as exc:
        publish('owner/repo','Draft','text',test_remote=str(remote))
    assert exc.value.code == 'GIT_REMOTE_ERROR'
    assert list(scratch.iterdir()) == []
    run('pull','--ff-only',cwd=source)
    assert not (source/'Draft.md').exists()
