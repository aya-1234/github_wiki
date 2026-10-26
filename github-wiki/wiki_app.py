"""Local document importer for GitHub Wiki."""
from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading
import unicodedata
from urllib.parse import quote

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from markdown_it import MarkdownIt
from ooxml import OfficeError, extract_office
from pydantic import BaseModel

MAX_UPLOAD = 20 * 1024 * 1024
MAX_BODY = 2 * 1024 * 1024
LOCK = threading.Lock()
ROOT = Path(__file__).parent
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
renderer = MarkdownIt('commonmark', {'html': False, 'linkify': False})


class AppError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        self.code, self.message, self.status = code, message, status
        super().__init__(message)


class PublishRequest(BaseModel):
    repository: str
    title: str
    markdown: str


class PreviewRequest(BaseModel):
    markdown: str


class StageRequest(BaseModel):
    title: str
    markdown: str


def check_repository(value: str) -> tuple[str, str]:
    pieces = value.split('/') if isinstance(value, str) else []
    if len(pieces) != 2 or not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?', pieces[0]) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', pieces[1]) or pieces[1].startswith('.') or pieces[1].endswith('.') or '..' in pieces[1]:
        raise AppError('INVALID_REPOSITORY', 'owner/repository を指定してください')
    return pieces[0], pieces[1]


def check_title(value: str) -> str:
    value = unicodedata.normalize('NFC', value)
    if not 1 <= len(value) <= 100 or value != value.strip() or value in ('.', '..') or value.endswith('.') or value.casefold() in ('home', '_sidebar', '_footer') or any(c in '\\/:*?"<>|' or unicodedata.category(c).startswith('C') for c in value):
        raise AppError('INVALID_TITLE', 'ページ名に使用できない文字または予約名があります')
    return value


def check_body(value: str) -> str:
    value = value.replace('\r\n', '\n').replace('\r', '\n')
    if not value.strip() or '\x00' in value:
        raise AppError('EMPTY_DOCUMENT', '本文が空、または無効です')
    if len(value.encode('utf-8')) > MAX_BODY:
        raise AppError('CONTENT_TOO_LARGE', '本文は 2 MiB 以下にしてください', 413)
    return value


def git(args: list[str], cwd: Path | None = None) -> str:
    env = os.environ.copy()
    env['GIT_TERMINAL_PROMPT'] = '0'
    try:
        p = subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True, env=env, timeout=120)
    except subprocess.TimeoutExpired:
        raise AppError('GIT_TIMEOUT', 'Git 操作が時間切れになりました。Wiki を確認してください', 504) from None
    if p.returncode:
        detail = (p.stderr + p.stdout).lower()
        if 'non-fast-forward' in detail or 'fetch first' in detail:
            raise AppError('REMOTE_CHANGED', 'Wiki が更新されました。再確認してください', 409)
        if 'authentication failed' in detail or 'could not read username' in detail:
            raise AppError('GIT_AUTH_FAILED', 'Git の認証設定を確認してください', 401)
        if 'permission denied' in detail or 'write access' in detail:
            raise AppError('WIKI_WRITE_DENIED', 'Wiki の書き込み権限を確認してください', 403)
        if 'repository not found' in detail:
            raise AppError('WIKI_UNAVAILABLE', 'Wiki の有効化と初期ページを確認してください', 404)
        raise AppError('GIT_REMOTE_ERROR', 'Git 操作に失敗しました。Wiki と接続状態を確認してください', 502)
    return p.stdout.strip()


def publish(repository: str, page_title: str, body: str, *, test_remote: str | None = None) -> dict:
    owner, repo = check_repository(repository)
    page_title, body = check_title(page_title), check_body(body)
    remote = test_remote or f'https://github.com/{owner}/{repo}.wiki.git'
    with LOCK, tempfile.TemporaryDirectory(prefix='wiki-git-') as directory:
        work = Path(directory) / 'wiki'
        git(['clone', '--', remote, str(work)])
        branch = git(['symbolic-ref', '--short', 'HEAD'], work)
        wanted = page_title.casefold()
        for item in work.iterdir():
            if item.is_file() and item.suffix.lower() in ('.md', '.markdown', '.textile', '.rst', '.org') and unicodedata.normalize('NFC', item.stem).casefold() == wanted:
                raise AppError('PAGE_EXISTS', '同名の Wiki ページが既にあります', 409)
        name = page_title + '.md'
        (work / name).write_text(body, encoding='utf-8')
        git(['add', '--', name], work)
        git(['-c', 'user.name=Wiki Importer', '-c', 'user.email=wiki-importer@localhost', 'commit', '-m', f'Add wiki page: {page_title}'], work)
        commit = git(['rev-parse', 'HEAD'], work)
        git(['push', 'origin', f'HEAD:{branch}'], work)
        return {'pageUrl': f'https://github.com/{owner}/{repo}/wiki/{quote(page_title, safe="")}', 'wikiUrl': f'https://github.com/{owner}/{repo}/wiki', 'commitSha': commit}


def stage_page(page_title: str, body: str, *, root: Path = ROOT) -> dict:
    page_title, body = check_title(page_title), check_body(body)
    folder = root / 'wiki-pages'
    if folder.is_symlink():
        raise AppError('INVALID_FILE', '審査用フォルダーを確認してください')
    folder.mkdir(exist_ok=True)
    path = folder / f'{page_title}.md'
    try:
        with path.open('x', encoding='utf-8') as output:
            output.write(body)
    except FileExistsError:
        raise AppError('PAGE_EXISTS', '同名の審査用ページが既にあります', 409) from None
    return {'path': f'wiki-pages/{page_title}.md'}


def pdf_command(args: list[str]) -> bytes:
    try:
        p = subprocess.run(args, capture_output=True, timeout=30)
    except FileNotFoundError:
        raise AppError('PDF_TOOL_MISSING', 'pdfinfo と pdftotext が必要です', 500) from None
    except subprocess.TimeoutExpired:
        raise AppError('INVALID_FILE', 'PDF の処理が時間切れになりました') from None
    if p.returncode:
        if b'incorrect password' in p.stderr.lower():
            raise AppError('PDF_ENCRYPTED', '暗号化 PDF は扱えません', 422)
        raise AppError('INVALID_FILE', 'PDF を読み取れません')
    return p.stdout


def relative_link_warnings(body: str) -> list[str]:
    found = []
    for token in renderer.parse(body):
        for child in token.children or []:
            if child.type not in ('link_open', 'image'):
                continue
            target = child.attrGet('href' if child.type == 'link_open' else 'src') or ''
            if not target or target.startswith(('#', '//')) or re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', target):
                continue
            kind = '相対画像' if child.type == 'image' else '相対リンク'
            message = f'{kind}: {target} — ' + ('画像は自動登録されません' if child.type == 'image' else 'Wiki での参照先を確認してください')
            if message not in found:
                found.append(message)
    if len(found) > 5:
        return found[:5] + [f'ほか {len(found)-5} 件の相対参照があります']
    return found


def convert(name: str, data: bytes) -> dict:
    if not name or Path(name).name != name:
        raise AppError('INVALID_FILE', 'ファイル名を確認してください')
    ext = Path(name).suffix.lower()
    if ext not in ('.md', '.pdf', '.docx', '.xlsx', '.pptx'):
        raise AppError('UNSUPPORTED_FORMAT', '.md / .pdf / .docx / .xlsx / .pptx を選んでください', 422)
    if len(data) > MAX_UPLOAD:
        raise AppError('FILE_TOO_LARGE', 'ファイルは 20 MiB 以下にしてください', 413)
    if ext == '.md':
        try:
            body = data.decode('utf-8-sig')
        except UnicodeDecodeError:
            raise AppError('INVALID_ENCODING', 'Markdown は UTF-8 で保存してください', 422) from None
        body = check_body(body)
    elif ext in ('.docx', '.xlsx', '.pptx'):
        try:
            body = check_body(extract_office(ext, data))
        except OfficeError as exc:
            raise AppError(exc.code, exc.message, 413 if exc.code == 'FILE_TOO_LARGE' else 422) from None
    else:
        if not data.startswith(b'%PDF-'):
            raise AppError('INVALID_FILE', 'PDF を読み取れません')
        with tempfile.TemporaryDirectory(prefix='wiki-pdf-') as directory:
            path = Path(directory) / 'input.pdf'
            path.write_bytes(data)
            info = pdf_command(['pdfinfo', str(path)]).decode('utf-8', 'replace')
            if re.search(r'^Encrypted:\s+yes', info, re.M | re.I):
                raise AppError('PDF_ENCRYPTED', '暗号化 PDF は扱えません', 422)
            match = re.search(r'^Pages:\s+(\d+)', info, re.M)
            if not match:
                raise AppError('INVALID_FILE', 'PDF のページ数を取得できません')
            pages = int(match.group(1))
            if pages > 100:
                raise AppError('PDF_TOO_MANY_PAGES', 'PDF は 100 ページ以下にしてください', 422)
            extracted = pdf_command(['pdftotext', '-enc', 'UTF-8', '-layout', str(path), '-']).decode('utf-8', 'replace').split('\f')[:pages]
            if not any(part.strip() for part in extracted):
                raise AppError('PDF_NO_TEXT', '文字がない PDF です。OCR は対応していません', 422)
            body = check_body('\n\n'.join(f'## PDF {n}ページ目\n\n{part.strip()}' for n, part in enumerate(extracted, 1)) + '\n')
    source_notes = []
    if ext == '.pdf' and len(body) < 100:
        source_notes.append('抽出文字が少ないため、元の PDF と照合してください')
    if ext in ('.docx', '.xlsx', '.pptx'):
        source_notes.append('画像・図形・一部の書式は取り込まれません。元のファイルと照合してください')
    return {'title': Path(name).stem, 'markdown': body, 'warnings': source_notes + relative_link_warnings(body), 'sourceWarnings': source_notes}


@app.exception_handler(AppError)
def app_error(_request: Request, exc: AppError):
    return JSONResponse({'code': exc.code, 'message': exc.message}, status_code=exc.status)


@app.exception_handler(RequestValidationError)
def validation_error(_request: Request, _exc: RequestValidationError):
    return JSONResponse({'code': 'INVALID_REQUEST', 'message': '入力形式を確認してください'}, status_code=400)


@app.middleware('http')
async def local_only(request: Request, call_next):
    host = request.headers.get('host', '').split(':')[0]
    origin = request.headers.get('origin', '')
    if host not in ('127.0.0.1', 'localhost') or (origin and origin not in ('http://127.0.0.1:8000', 'http://localhost:8000')):
        return JSONResponse({'code': 'INVALID_ORIGIN', 'message': 'ローカル画面から操作してください'}, status_code=403)
    return await call_next(request)


@app.get('/')
def index():
    return FileResponse(ROOT / 'static' / 'index.html')


@app.post('/api/convert')
async def convert_api(file: UploadFile = File(...)):
    data = await file.read(MAX_UPLOAD + 1)
    return convert(file.filename or '', data)


@app.post('/api/preview')
def preview_api(payload: PreviewRequest):
    if len(payload.markdown.encode('utf-8')) > MAX_BODY:
        raise AppError('CONTENT_TOO_LARGE', '本文は 2 MiB 以下にしてください', 413)
    return {'html': renderer.render(payload.markdown), 'warnings': relative_link_warnings(payload.markdown)}


@app.post('/api/publish', status_code=201)
def publish_api(payload: PublishRequest):
    if os.environ.get('ALLOW_DIRECT_WIKI_PUBLISH') != '1':
        raise AppError('DIRECT_PUBLISH_DISABLED', 'PR 用ファイルを保存し、審査後に Wiki へ公開してください', 403)
    return publish(payload.repository, payload.title, payload.markdown)


@app.post('/api/stage', status_code=201)
def stage_api(payload: StageRequest):
    return stage_page(payload.title, payload.markdown)
