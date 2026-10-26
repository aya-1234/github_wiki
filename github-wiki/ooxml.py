"""Extract editable Markdown from Office Open XML documents without macros."""
from __future__ import annotations

from io import BytesIO
import posixpath
import re
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

MAX_UNCOMPRESSED = 50 * 1024 * 1024
MAX_ENTRIES = 2000
NS = {
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    's': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
    'rel': 'http://schemas.openxmlformats.org/package/2006/relationships',
}


class OfficeError(Exception):
    def __init__(self, code: str, message: str):
        self.code, self.message = code, message
        super().__init__(message)


def _safe_text(value: str) -> str:
    return re.sub(r'([\\`*_{}\[\]()#+.!|>~-])', r'\\\1', value.replace('\r', ' ').replace('\n', ' ')).strip()


def _xml(archive: ZipFile, name: str) -> ET.Element:
    try:
        raw = archive.read(name)
        if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
            raise ValueError('DTD is not allowed')
        return ET.fromstring(raw)
    except (KeyError, ET.ParseError, ValueError) as exc:
        raise OfficeError('INVALID_FILE', 'Office ファイルを読み取れません') from exc


def _archive(data: bytes, expected: str) -> ZipFile:
    try:
        archive = ZipFile(BytesIO(data))
        entries = archive.infolist()
        if len(entries) > MAX_ENTRIES or sum(item.file_size for item in entries) > MAX_UNCOMPRESSED:
            raise OfficeError('FILE_TOO_LARGE', '展開後の Office ファイルが大きすぎます')
        if any(item.flag_bits & 1 for item in entries):
            raise OfficeError('INVALID_FILE', '暗号化された Office ファイルは扱えません')
        if any(item.filename.casefold().endswith('vbaproject.bin') for item in entries):
            raise OfficeError('INVALID_FILE', 'マクロ付き Office ファイルは扱えません')
        if '[Content_Types].xml' not in archive.namelist() or expected not in archive.namelist():
            raise OfficeError('INVALID_FILE', '拡張子に対応する Office ファイルではありません')
        return archive
    except (BadZipFile, ValueError) as exc:
        raise OfficeError('INVALID_FILE', 'Office ファイルを読み取れません') from exc


def _paragraph(element: ET.Element, namespace: str) -> str:
    return ''.join(node.text or '' for node in element.findall(f'.//{namespace}:t', NS))


def _table(rows: list[list[str]]) -> str:
    if not rows:
        return ''
    width = max(map(len, rows))
    if width == 0:
        return ''
    def line(row: list[str]) -> str:
        return '| ' + ' | '.join(_safe_text(row[n]) if n < len(row) else '' for n in range(width)) + ' |'
    return '\n'.join([line(rows[0]), '| ' + ' | '.join(['---'] * width) + ' |', *(line(row) for row in rows[1:])])


def _docx(archive: ZipFile) -> str:
    root = _xml(archive, 'word/document.xml')
    body = root.find('w:body', NS)
    if body is None:
        raise OfficeError('INVALID_FILE', 'Word 文書の本文がありません')
    blocks = []
    for child in body:
        if child.tag == f"{{{NS['w']}}}p":
            value = _safe_text(_paragraph(child, 'w'))
            if not value:
                continue
            style = child.find('w:pPr/w:pStyle', NS)
            style_id = style.get(f"{{{NS['w']}}}val", '') if style is not None else ''
            heading = re.fullmatch(r'Heading([1-6])', style_id, re.I)
            blocks.append('#' * int(heading.group(1)) + ' ' + value if heading else value)
        elif child.tag == f"{{{NS['w']}}}tbl":
            rows = [[_paragraph(cell, 'w') for cell in row.findall('w:tc', NS)] for row in child.findall('w:tr', NS)]
            if rows:
                blocks.append(_table(rows))
    return '\n\n'.join(blocks)


def _column_number(reference: str) -> int:
    letters = re.match(r'[A-Z]+', reference.upper())
    if not letters:
        return 0
    value = 0
    for character in letters.group():
        value = value * 26 + ord(character) - 64
    return value


def _xlsx(archive: ZipFile) -> str:
    workbook = _xml(archive, 'xl/workbook.xml')
    rels = _xml(archive, 'xl/_rels/workbook.xml.rels')
    targets = {rel.get('Id'): rel.get('Target', '') for rel in rels}
    shared = []
    if 'xl/sharedStrings.xml' in archive.namelist():
        strings = _xml(archive, 'xl/sharedStrings.xml')
        shared = [_paragraph(item, 's') for item in strings.findall('s:si', NS)]
    blocks = []
    for sheet in workbook.findall('s:sheets/s:sheet', NS):
        name = sheet.get('name', 'Sheet')
        target = targets.get(sheet.get(f"{{{NS['r']}}}id"))
        if not target:
            raise OfficeError('INVALID_FILE', 'Excel シートを読み取れません')
        path = posixpath.normpath(posixpath.join('xl', target.lstrip('/'))) if not target.startswith('/') else target.lstrip('/')
        if not path.startswith('xl/') or path not in archive.namelist():
            raise OfficeError('INVALID_FILE', 'Excel シートを読み取れません')
        root = _xml(archive, path)
        rows = []
        for row in root.findall('s:sheetData/s:row', NS):
            cells = {}
            for cell in row.findall('s:c', NS):
                col = _column_number(cell.get('r', ''))
                if not 1 <= col <= 100:
                    continue
                kind = cell.get('t')
                if kind == 'inlineStr':
                    value = _paragraph(cell, 's')
                else:
                    node = cell.find('s:v', NS)
                    value = node.text or '' if node is not None else ''
                    if kind == 's':
                        try:
                            value = shared[int(value)]
                        except (ValueError, IndexError):
                            raise OfficeError('INVALID_FILE', 'Excel の共有文字列を読み取れません') from None
                    elif kind == 'b':
                        value = 'TRUE' if value == '1' else 'FALSE'
                cells[col] = value
            if cells and any(value.strip() for value in cells.values()):
                rows.append([cells.get(n, '') for n in range(1, max(cells) + 1)])
        if rows:
            blocks.append('## ' + _safe_text(name) + '\n\n' + _table(rows))
    return '\n\n'.join(blocks)


def _pptx(archive: ZipFile) -> str:
    presentation = _xml(archive, 'ppt/presentation.xml')
    rels = _xml(archive, 'ppt/_rels/presentation.xml.rels')
    targets = {rel.get('Id'): rel.get('Target', '') for rel in rels}
    blocks = []
    for index, slide in enumerate(presentation.findall('p:sldIdLst/p:sldId', NS), 1):
        target = targets.get(slide.get(f"{{{NS['r']}}}id"))
        if not target:
            raise OfficeError('INVALID_FILE', 'PowerPoint スライドを読み取れません')
        path = posixpath.normpath(posixpath.join('ppt', target.lstrip('/'))) if not target.startswith('/') else target.lstrip('/')
        if not path.startswith('ppt/') or path not in archive.namelist():
            raise OfficeError('INVALID_FILE', 'PowerPoint スライドを読み取れません')
        root = _xml(archive, path)
        paragraphs = [_safe_text(_paragraph(p, 'a')) for p in root.findall('.//a:p', NS)]
        paragraphs = [p for p in paragraphs if p]
        if paragraphs:
            blocks.append(f'## スライド {index}\n\n' + '\n\n'.join(paragraphs))
    return '\n\n'.join(blocks)


def extract_office(ext: str, data: bytes) -> str:
    expected = {'.docx': 'word/document.xml', '.xlsx': 'xl/workbook.xml', '.pptx': 'ppt/presentation.xml'}[ext]
    with _archive(data, expected) as archive:
        try:
            return {'.docx': _docx, '.xlsx': _xlsx, '.pptx': _pptx}[ext](archive)
        except (BadZipFile, RuntimeError, OSError) as exc:
            raise OfficeError('INVALID_FILE', 'Office ファイルを読み取れません') from exc
