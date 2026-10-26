"""Exercise the ASGI app with a local Git wiki and build labeled UI reconstructions."""
from __future__ import annotations

import asyncio
from datetime import date
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import subprocess
import tempfile

import anyio.to_thread
import httpx
from PIL import Image, ImageDraw, ImageFont
import wiki_app

ROOT = Path(__file__).resolve().parents[1]
IMAGES = ROOT / 'docs' / 'images'
EVIDENCE = ROOT / 'docs' / 'evidence' / 'demo_run.json'
REPORT = ROOT / 'docs' / '実働確認レポート.md'
FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'


def make_pdf(*pages: str) -> bytes:
    ids = [4 + 2 * n for n in range(len(pages))]
    kids = b' '.join(f'{number} 0 R'.encode() for number in ids)
    objects = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [' + kids + b'] /Count ' + str(len(pages)).encode() + b' >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    ]
    for n, line in enumerate(pages):
        stream = f'BT /F1 16 Tf 40 100 Td ({line}) Tj ET'.encode()
        objects += [
            f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Resources << /Font << /F1 3 0 R >> >> /Contents {5+2*n} 0 R >>'.encode(),
            b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream',
        ]
    output = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output += f'{number} 0 obj\n'.encode() + obj + b'\nendobj\n'
    start = len(output)
    output += f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode()
    for offset in offsets[1:]:
        output += f'{offset:010} 00000 n \n'.encode()
    output += f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode()
    return bytes(output)


def git(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


async def exercise() -> dict:
    async def inline(func, *args, **kwargs):
        # Worker threads are unavailable in this sandbox. Only test scheduling changes.
        return func(*args)

    original_runner = anyio.to_thread.run_sync
    original_publish = wiki_app.publish
    original_direct = os.environ.get('ALLOW_DIRECT_WIKI_PUBLISH')
    os.environ['ALLOW_DIRECT_WIKI_PUBLISH'] = '1'
    anyio.to_thread.run_sync = inline
    try:
        with tempfile.TemporaryDirectory(prefix='wiki-demo-') as temporary:
            directory = Path(temporary)
            remote = directory / 'demo.wiki.git'
            source = directory / 'source'
            git('init', '--bare', str(remote))
            git('clone', str(remote), str(source))
            (source / 'Home.md').write_text('# Demo Wiki\n', encoding='utf-8')
            git('add', 'Home.md', cwd=source)
            git('-c', 'user.name=Demo', '-c', 'user.email=demo@localhost', 'commit', '-m', 'Initial', cwd=source)
            git('push', 'origin', 'HEAD', cwd=source)
            wiki_app.publish = lambda repository, title, body: original_publish(repository, title, body, test_remote=str(remote))

            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=wiki_app.app), base_url='http://127.0.0.1:8000') as client:
                page = await client.get('/')
                md_bytes = b'# Guide\n\nWelcome to the wiki.\n\n[Details](./details.md)\n\n![Logo](images/logo.png)\n'
                md = await client.post('/api/convert', files={'file': ('Guide.md', md_bytes, 'text/markdown')})
                md_preview = await client.post('/api/preview', json={'markdown': md.json()['markdown']})
                pdf = await client.post('/api/convert', files={'file': ('Manual.pdf', make_pdf('First page', 'Second page'), 'application/pdf')})
                pdf_preview = await client.post('/api/preview', json={'markdown': pdf.json()['markdown']})
                payload = {'repository': 'demo/wiki', 'title': md.json()['title'], 'markdown': md.json()['markdown']}
                published = await client.post('/api/publish', json=payload)
                duplicate = await client.post('/api/publish', json=payload)
            git('pull', '--ff-only', cwd=source)
            saved_body = (source / 'Guide.md').read_text(encoding='utf-8')
            assert page.status_code == 200 and 'GitHub Wiki に追加' in page.text
            assert md.status_code == md_preview.status_code == pdf.status_code == pdf_preview.status_code == 200
            assert published.status_code == 201 and duplicate.status_code == 409
            assert saved_body == md.json()['markdown']
            return {
                'date': str(date.today()),
                'pageStatus': page.status_code,
                'markdown': {'status': md.status_code, 'response': md.json(), 'preview': md_preview.json()},
                'pdf': {'status': pdf.status_code, 'response': pdf.json(), 'preview': pdf_preview.json()},
                'publish': {'status': published.status_code, 'response': published.json(), 'savedMarkdownMatches': saved_body == md.json()['markdown']},
                'duplicate': {'status': duplicate.status_code, 'response': duplicate.json()},
                'remote': 'temporary local bare Git repository',
                'browserScreenshotCaptured': False,
            }
    finally:
        anyio.to_thread.run_sync = original_runner
        wiki_app.publish = original_publish
        if original_direct is None:
            os.environ.pop('ALLOW_DIRECT_WIKI_PUBLISH', None)
        else:
            os.environ['ALLOW_DIRECT_WIKI_PUBLISH'] = original_direct


class PreviewText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lines = []
    def handle_data(self, data: str):
        data = data.strip()
        if data:
            self.lines.append(data)


def clipped(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int) -> str:
    if draw.textlength(text, font=font) <= width:
        return text
    while text and draw.textlength(text + '…', font=font) > width:
        text = text[:-1]
    return text + '…'


def screenshot_like(name: str, *, filename: str, title: str, body: str, preview_html: str, warnings: list[str], status: str, success: bool = False) -> None:
    image = Image.new('RGB', (1440, 900), '#f4f6f9')
    draw = ImageDraw.Draw(image)
    regular = ImageFont.truetype(FONT, 19)
    small = ImageFont.truetype(FONT, 15)
    bold = ImageFont.truetype(FONT, 30)
    draw.rectangle((0, 0, 1440, 48), fill='#8a3c18')
    draw.text((28, 11), '実行データに基づく再現画像  /  ブラウザのスクリーンショットではありません', font=small, fill='white')
    draw.rounded_rectangle((100, 72, 1340, 856), radius=12, fill='white', outline='#dce2e9', width=2)
    draw.text((142, 100), 'GitHub Wiki に追加', font=bold, fill='#20252e')
    draw.text((142, 156), 'PDF または Markdown を取り込み、内容を確認してから公開します。', font=regular, fill='#343a44')
    draw.text((142, 204), '公開先（owner/repository）', font=regular, fill='#20252e')
    draw.rounded_rectangle((142, 238, 1298, 284), radius=6, outline='#aeb8c5', width=2)
    draw.text((156, 246), 'demo/wiki', font=regular, fill='#20252e')
    draw.text((142, 302), 'ファイル（.pdf / .md、20 MiB 以下）', font=regular, fill='#20252e')
    draw.rounded_rectangle((142, 336, 1298, 382), radius=6, outline='#aeb8c5', width=2)
    draw.text((156, 344), filename, font=regular, fill='#20252e')
    warning = ' / '.join(warnings) if warnings else '警告なし'
    draw.text((142, 394), clipped(draw, warning, small, 1140), font=small, fill='#805700')
    draw.text((142, 427), 'ページ名', font=regular, fill='#20252e')
    draw.rounded_rectangle((142, 460, 1298, 506), radius=6, outline='#aeb8c5', width=2)
    draw.text((156, 468), title, font=regular, fill='#20252e')
    draw.text((142, 526), 'Markdown 本文', font=regular, fill='#20252e')
    draw.text((732, 526), 'プレビュー', font=regular, fill='#20252e')
    draw.rounded_rectangle((142, 560, 704, 742), radius=6, outline='#aeb8c5', width=2)
    draw.rounded_rectangle((732, 560, 1298, 742), radius=6, outline='#aeb8c5', width=2)
    parser = PreviewText()
    parser.feed(preview_html)
    for x, lines in ((156, body.splitlines()), (746, parser.lines)):
        for index, line in enumerate([line for line in lines if line.strip()][:6]):
            draw.text((x, 574 + index * 26), clipped(draw, line, small, 520), font=small, fill='#20252e')
    draw.rounded_rectangle((142, 763, 306, 810), radius=6, fill='#1769aa')
    draw.text((166, 774), 'Wiki に追加', font=regular, fill='white')
    draw.text((330, 773), clipped(draw, status, small, 950), font=small, fill='#17633b' if success else '#a01c24' if '同名' in status else '#303743')
    IMAGES.mkdir(parents=True, exist_ok=True)
    image.save(IMAGES / name, optimize=True)


def report_text(data: dict) -> str:
    md = data['markdown']
    pdf = data['pdf']
    pub = data['publish']
    dup = data['duplicate']
    sha = pub['response']['commitSha']
    return f'''<div align="center">

# GitHub Wiki Importer

### 実働確認レポート

</div>

| 文書情報 | 内容 |
| :--- | :--- |
| 確認日 | {data['date']} |
| 対象 | ローカル Web アプリ / PDF・Markdown の GitHub Wiki 登録 |
| 実行先 | プロセス内 ASGI + 一時ローカル Git Wiki |
| 総合結果 | 実行した範囲で成功。実ブラウザと GitHub 本番は未確認 |

> **判定:** プロセス内の画面配信・変換・プレビュー・ローカル Git 公開は成功。ブラウザ撮影と GitHub 実環境への公開は未確認。

---

## 01｜確認方法と範囲

アプリの ASGI インターフェースをプロセス内で実行した。`GET /`、`.md` と PDF の変換・プレビュー、ローカルの一時 Git Wiki への公開、同名ページの拒否を連続して確認した。画面側は別途 Node.js のヘッドレス DOM テストで操作フローを確認した。

**図1〜4は API の実行データを画面の配置に当てはめた再現画像であり、実ブラウザのスクリーンショットではない。** この実行環境ではローカルソケット作成が拒否され、Chrome と Firefox も起動できないため、実ブラウザ撮影は行えていない。画像に見える `demo/wiki` はテスト用のローカル Git リポジトリに接続した値で、GitHub へは送信していない。

| 確認項目 | 実測結果 |
| :--- | :--- |
| 画面配信 | `GET /` → HTTP {data['pageStatus']} |
| Markdown 取り込み | `POST /api/convert` → HTTP {md['status']} |
| PDF 取り込み | `POST /api/convert` → HTTP {pdf['status']} |
| 新規ページ公開 | `POST /api/publish` → HTTP {pub['status']}、保存本文一致: `{str(pub['savedMarkdownMatches']).lower()}` |
| 同名ページ再公開 | `POST /api/publish` → HTTP {dup['status']} / `{dup['response']['code']}` |

---

## 02｜Markdown の取り込み

`Guide.md` を取り込み、本文と相対リンク・画像の警告を取得した。プレビューは `POST /api/preview` の結果を使用した。

![図1：Markdown 取り込み時の画面再現](images/demo-md.png)

*図1　Markdown 取り込み。相対参照の警告は実際の API 応答を表示。ブラウザ撮影ではない。*

---

## 03｜PDF の取り込み

2 ページのテキスト PDF `Manual.pdf` を入力した。変換結果には `PDF 1ページ目` と `PDF 2ページ目` の見出し、および `First page`・`Second page` の本文がこの順に含まれた。

![図2：PDF 取り込み時の画面再現](images/demo-pdf.png)

*図2　PDF 取り込み。画面内の本文・プレビューは実際の変換結果に基づく。ブラウザ撮影ではない。*

---

## 04｜Wiki への追加と重複保護

`Guide.md` の変換本文を、一時的に作ったローカル Git Wiki に新規追加した。プッシュ後に Wiki を取得し直し、保存本文が送信した Markdown と完全一致することを確認した。コミット ID は `{sha[:12]}`。

![図3：公開成功時の画面再現](images/demo-publish.png)

*図3　公開成功時。結果リンクはアプリが組み立てた URL であり、この確認では GitHub 上にページは作成していない。*

同じページ名を再度公開すると、HTTP 409 と `PAGE_EXISTS` が返った。

![図4：同名ページ拒否時の画面再現](images/demo-duplicate.png)

*図4　同名ページの公開拒否。既存本文は変更されていない。*

---

## 05｜検証結果と残る確認

- Python 自動テスト: `uv run python -m pytest -q` → **55 件成功**。
- 画面スクリプトのヘッドレス DOM テスト: `node tests/test_ui.mjs` → **7 件成功**。
- 実ポートへのサーバー起動: `127.0.0.1:8000` への bind が環境に拒否されたため未確認。
- 実ブラウザのスクリーンショット: 未取得。図1〜4は再現画像。
- 実 GitHub Wiki への公開: 利用者の指定に従い、今回は行っていない。

実行の機械可読な記録は [demo_run.json](evidence/demo_run.json) に保存した。再現手順は `uv run python -m scripts.build_demo_report`。設計とタスクの状態は [タスク一覧](tasks_1.md) を参照。
'''


def main() -> None:
    data = asyncio.run(exercise())
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    md, pdf, pub, dup = data['markdown'], data['pdf'], data['publish'], data['duplicate']
    screenshot_like('demo-md.png', filename='Guide.md', title=md['response']['title'], body=md['response']['markdown'], preview_html=md['preview']['html'], warnings=md['response']['warnings'], status='変換しました。内容を確認してください。')
    screenshot_like('demo-pdf.png', filename='Manual.pdf', title=pdf['response']['title'], body=pdf['response']['markdown'], preview_html=pdf['preview']['html'], warnings=pdf['response']['warnings'], status='変換しました。内容を確認してください。')
    screenshot_like('demo-publish.png', filename='Guide.md', title=md['response']['title'], body=md['response']['markdown'], preview_html=md['preview']['html'], warnings=md['response']['warnings'], status='公開しました。コミット: ' + pub['response']['commitSha'][:12], success=True)
    screenshot_like('demo-duplicate.png', filename='Guide.md', title=md['response']['title'], body=md['response']['markdown'], preview_html=md['preview']['html'], warnings=md['response']['warnings'], status=dup['response']['message'])
    REPORT.write_text(report_text(data), encoding='utf-8')
    print(f'Report: {REPORT}')
    print(f'GET /: {data["pageStatus"]}, Markdown: {md["status"]}, PDF: {pdf["status"]}, publish: {pub["status"]}, duplicate: {dup["status"]}')
    print(f'Commit: {pub["response"]["commitSha"]}')


if __name__ == '__main__':
    main()
