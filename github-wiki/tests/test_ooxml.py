"""Office conversion with small, valid OOXML packages."""
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from wiki_app import AppError, convert


def package(files: dict[str, str]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, 'w', ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml', '<Types/>')
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def docx() -> bytes:
    return package({'word/document.xml': '''
    <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
      <w:body>
        <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Guide</w:t></w:r></w:p>
        <w:p><w:r><w:t>First</w:t></w:r><w:r><w:t> paragraph</w:t></w:r></w:p>
        <w:tbl><w:tr><w:tc><w:p><w:r><w:t>Name</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>Value</w:t></w:r></w:p></w:tc></w:tr>
        <w:tr><w:tc><w:p><w:r><w:t>A</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>1</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
      </w:body></w:document>'''})


def xlsx() -> bytes:
    return package({
        'xl/workbook.xml': '''<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="売上" r:id="rId1"/></sheets></workbook>''',
        'xl/_rels/workbook.xml.rels': '''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>''',
        'xl/sharedStrings.xml': '''<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si><t>項目</t></si><si><t>単価</t></si></sst>''',
        'xl/worksheets/sheet1.xml': '''<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>Pen</t></is></c><c r="B2"><v>120</v></c></row></sheetData></worksheet>''',
    })


def pptx() -> bytes:
    return package({
        'ppt/presentation.xml': '''<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><p:sldIdLst><p:sldId r:id="rId2"/><p:sldId r:id="rId1"/></p:sldIdLst></p:presentation>''',
        'ppt/_rels/presentation.xml.rels': '''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="slides/slide1.xml"/><Relationship Id="rId2" Target="slides/slide2.xml"/></Relationships>''',
        'ppt/slides/slide1.xml': '''<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:sp><p:txBody><a:p><a:r><a:t>Second slide</a:t></a:r></a:p></p:txBody></p:sp></p:sld>''',
        'ppt/slides/slide2.xml': '''<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:sp><p:txBody><a:p><a:r><a:t>First slide</a:t></a:r></a:p></p:txBody></p:sp></p:sld>''',
    })


def test_word_heading_paragraph_and_table():
    result = convert('Guide.docx', docx())
    assert result['title'] == 'Guide'
    assert '# Guide' in result['markdown']
    assert 'First paragraph' in result['markdown']
    assert '| Name | Value |' in result['markdown']
    assert '| A | 1 |' in result['markdown']
    assert result['sourceWarnings']


def test_excel_sheet_and_cells():
    result = convert('Sales.xlsx', xlsx())
    assert '## 売上' in result['markdown']
    assert '| 項目 | 単価 |' in result['markdown']
    assert '| Pen | 120 |' in result['markdown']


def test_powerpoint_presentation_order():
    result = convert('Slides.pptx', pptx())
    assert result['markdown'].index('First slide') < result['markdown'].index('Second slide')
    assert '## スライド 2' in result['markdown']


@pytest.mark.parametrize('name', ['Broken.docx', 'Broken.xlsx', 'Broken.pptx'])
def test_bad_archive_is_rejected(name):
    with pytest.raises(AppError) as exc:
        convert(name, b'not a zip')
    assert exc.value.code == 'INVALID_FILE'


def test_wrong_office_extension_is_rejected():
    with pytest.raises(AppError) as exc:
        convert('Sales.docx', xlsx())
    assert exc.value.code == 'INVALID_FILE'


def test_empty_office_document_is_rejected():
    data = package({'word/document.xml': '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body/></w:document>'})
    with pytest.raises(AppError) as exc:
        convert('Empty.docx', data)
    assert exc.value.code == 'EMPTY_DOCUMENT'


def test_xml_entity_is_rejected():
    data = package({'word/document.xml': '<!DOCTYPE x [<!ENTITY e "bad">]><x/>'})
    with pytest.raises(AppError) as exc:
        convert('Bad.docx', data)
    assert exc.value.code == 'INVALID_FILE'


def test_macro_package_is_rejected():
    data = package({
        'word/document.xml': '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Hello</w:t></w:r></w:p></w:body></w:document>',
        'word/vbaProject.bin': 'macro',
    })
    with pytest.raises(AppError) as exc:
        convert('Macro.docx', data)
    assert exc.value.code == 'INVALID_FILE'


def test_uncompressed_limit_is_rejected():
    data = package({'word/document.xml': 'x' * (50 * 1024 * 1024 + 1)})
    with pytest.raises(AppError) as exc:
        convert('Huge.docx', data)
    assert exc.value.code == 'FILE_TOO_LARGE'
